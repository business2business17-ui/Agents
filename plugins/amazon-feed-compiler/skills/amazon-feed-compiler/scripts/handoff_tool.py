#!/usr/bin/env python3
"""Validate and seal Agent 1 -> Agent 2 handoff records (spec sections 80-102).

Usage:
  handoff_tool.py --example                         # print a minimal valid record
  handoff_tool.py seal     IN.json|jsonl  OUT.jsonl [--batch-id B] [--agent-version 2.0.0]
        fills generated_at / batch_id / handoff_schema_version, computes source/content/pricing/record hashes and
        idempotency_key (deterministic: same logical record -> same key)
  handoff_tool.py validate IN.json|jsonl [--json]
        checks identity fields, enums, null semantics, product-type lock, pricing block (policy v3), hash consistency,
        and publish-status rules (hard blockers / unresolved required fields forbid READY_*).
Exit 0 = all records valid, 1 = invalid records.
"""
import argparse
import copy
import hashlib
import json
import sys
from datetime import datetime, timezone

SCHEMA = "1.0.0"
SUPPORTED = {"1.0.0"}
POLICY = "2026-10-08-v3"
STATUSES = {"READY_TO_PUBLISH", "READY_WITH_WARNINGS", "NEEDS_REVIEW", "DATA_REQUIRED", "POLICY_RISK",
            "PRICE_CONFLICT", "BLOCKED"}
READY = {"READY_TO_PUBLISH", "READY_WITH_WARNINGS"}
INTENTS = {"CREATE", "UPDATE", "PARTIAL_UPDATE", "CONTENT_ONLY", "PRICE_ONLY", "OFFER_ONLY", "CLOSE_OFFER", "DELETE"}
ID_MODES = {"GTIN", "GTIN_EXEMPT", "MATCH_EXISTING_ASIN", "UPDATE_EXISTING_ASIN"}
IDENT_STATUS = {"GTIN_VALID", "GTIN_EXEMPT", "GTIN_MISSING", "GTIN_INVALID", "IDENTIFIER_CONFLICT",
                "IDENTIFIER_DUPLICATE", "ASIN_MATCH_FOUND", "NEW_PRODUCT_CANDIDATE"}
BLOCKERS = {"INVALID_GTIN", "IDENTIFIER_CONFLICT", "REQUIRED_ATTRIBUTE_MISSING", "PROHIBITED_CLAIM",
            "PRICE_CONFLICT", "CURRENCY_CONFLICT", "PRODUCT_TYPE_UNRESOLVED"}
REQUIRED = ["handoff_schema_version", "batch_id", "generated_at", "generated_by_agent_version", "internal_product_id",
            "sku", "marketplace", "record_version", "operation_intent", "publish_status", "identifier_mode",
            "identifiers", "product_type", "changed_fields", "unresolved_required_fields", "hard_blockers",
            "warnings", "hashes", "idempotency_key"]
GENERATED = {"generated_at", "hashes", "idempotency_key", "batch_id", "handoff_schema_version"}

EXAMPLE = {
    "handoff_schema_version": SCHEMA, "batch_id": "B20261008", "generated_at": "", "generated_by_agent_version": "2.0.0",
    "internal_product_id": "P-0001", "sku": "SKU-001", "marketplace": "DE", "record_version": "1",
    "operation_intent": "CREATE", "publish_status": "READY_TO_PUBLISH", "identifier_mode": "GTIN",
    "identifiers": {"ean": "4006381333931", "upc": None, "gtin": None, "asin": None, "gtin_exempt": False,
                    "status": "GTIN_VALID"},
    "product_type": {"value": "PHONE_CASE", "status": "LOCKED", "confidence": "HIGH", "locked": True},
    "catalog": {"brand": "ExampleBrand"},
    "content": {"title": "ExampleBrand Slim Case for Pixel 8, Matte Black", "item_highlights": "", "bullet_points": [],
                "description": "", "backend_search_terms": "", "backend_bytes": 0},
    "pricing": {"price_input_type": "sale_price", "sale_price": 24.99, "standard_price": 27.77, "business_price": 24.99,
                "business_price_status": "CALCULATED", "pricing_policy_version": POLICY, "pricing_basis": "STANDARD_PRICE",
                "currency": "EUR", "pricing_calculations": []},
    "compatibility": {}, "claims": [], "evidence": [], "changed_fields": [], "unresolved_required_fields": [],
    "hard_blockers": [], "warnings": [], "versions": {}, "audit": {},
    "hashes": {"source_hash": "", "content_hash": "", "pricing_hash": "", "record_hash": ""},
    "idempotency_key": "",
    "rollback": {"previous_record_version": None, "previous_content_hash": None, "previous_pricing_hash": None},
}


def h(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                                     default=str).encode("utf-8")).hexdigest()


def seal_one(r, batch_id, agent_version, now):
    r = copy.deepcopy(r)
    r["handoff_schema_version"] = SCHEMA
    r["batch_id"] = r.get("batch_id") or batch_id
    r["generated_at"] = r.get("generated_at") or now
    r["generated_by_agent_version"] = r.get("generated_by_agent_version") or agent_version
    if r.get("content"):
        c = r["content"]
        c["backend_bytes"] = len((c.get("backend_search_terms") or "").encode("utf-8"))
    src = {k: r.get(k) for k in ("identifiers", "catalog", "compatibility", "claims", "evidence", "product_type")}
    content = r.get("content")
    pricing = r.get("pricing")
    r["hashes"] = dict(source_hash=h(src), content_hash=h(content), pricing_hash=h(pricing))
    body = {k: v for k, v in r.items() if k not in ("hashes", "idempotency_key", "generated_at", "batch_id")}
    r["hashes"]["record_hash"] = h(body)
    r["idempotency_key"] = h([r.get("internal_product_id"), r.get("marketplace"), r.get("operation_intent"),
                              r["hashes"]["content_hash"], r["hashes"]["pricing_hash"], r.get("changed_fields")])[:32]
    return r


def validate_one(r):
    errs, warns = [], []
    for k in REQUIRED:
        if k not in r:
            errs.append(f"missing field: {k}")
    if errs:
        return errs, warns
    if r["handoff_schema_version"] not in SUPPORTED:
        errs.append(f"unsupported handoff_schema_version {r['handoff_schema_version']} (supported {sorted(SUPPORTED)})")
    for k in ("internal_product_id", "sku", "marketplace", "batch_id", "record_version"):
        if r.get(k) in (None, ""):
            errs.append(f"{k} is empty (null = unavailable; identity fields are mandatory)")
    if r["operation_intent"] not in INTENTS:
        errs.append(f"operation_intent '{r['operation_intent']}' not in {sorted(INTENTS)}")
    if r["operation_intent"] in ("DELETE", "CLOSE_OFFER"):
        warns.append("destructive operation intent: needs explicit user approval downstream")
    if r["publish_status"] not in STATUSES:
        errs.append(f"publish_status '{r['publish_status']}' invalid")
    if r["identifier_mode"] not in ID_MODES:
        errs.append(f"identifier_mode '{r['identifier_mode']}' not in {sorted(ID_MODES)}")
    ident = r["identifiers"]
    if ident.get("status") not in IDENT_STATUS:
        errs.append(f"identifiers.status '{ident.get('status')}' invalid")
    mode = r["identifier_mode"]
    if mode == "GTIN_EXEMPT" and not ident.get("gtin_exempt"):
        errs.append("identifier_mode GTIN_EXEMPT but identifiers.gtin_exempt is not true")
    if mode == "GTIN" and not any(ident.get(k) for k in ("ean", "upc", "gtin")):
        errs.append("identifier_mode GTIN but no EAN/UPC/GTIN present")
    if mode in ("MATCH_EXISTING_ASIN", "UPDATE_EXISTING_ASIN") and not ident.get("asin"):
        errs.append(f"identifier_mode {mode} requires identifiers.asin")
    for k in ("ean", "upc", "gtin"):
        v = ident.get(k)
        if v is not None and not isinstance(v, str):
            errs.append(f"identifiers.{k} must be a string (leading zeros), got {type(v).__name__}")
        if v == "":
            errs.append(f"identifiers.{k} is an empty string; use null for unavailable")
    pt = r["product_type"]
    if not isinstance(pt, dict) or not pt.get("value"):
        errs.append("product_type.value missing")
    elif r["publish_status"] in READY and not pt.get("locked"):
        errs.append("READY record requires product_type.locked = true (Product Type Lock)")
    for k in ("changed_fields", "unresolved_required_fields", "hard_blockers", "warnings"):
        if not isinstance(r[k], list):
            errs.append(f"{k} must be a list")
    bl = r["hard_blockers"] if isinstance(r["hard_blockers"], list) else []
    unknown = [b for b in bl if b not in BLOCKERS]
    if unknown:
        warns.append(f"non-standard hard_blockers: {unknown}")
    if r["publish_status"] in READY and bl:
        errs.append(f"READY status with hard_blockers {bl}")
    if r["publish_status"] in READY and r["unresolved_required_fields"]:
        errs.append(f"READY status with unresolved_required_fields {r['unresolved_required_fields']}")
    if r["publish_status"] == "BLOCKED" and not bl:
        warns.append("BLOCKED without hard_blockers: add the reason")
    if r["operation_intent"] in ("PARTIAL_UPDATE", "CONTENT_ONLY", "PRICE_ONLY", "OFFER_ONLY") and not r["changed_fields"]:
        errs.append(f"{r['operation_intent']} requires non-empty changed_fields")
    p = r.get("pricing") or {}
    if p:
        if p.get("pricing_policy_version") != POLICY:
            errs.append(f"pricing.pricing_policy_version must be {POLICY} (stale or divergent policy)")
        if p.get("price_input_type") != "sale_price":
            warns.append("pricing.price_input_type is not sale_price (PRICE_INPUT_DEFAULT)")
        for k in ("sale_price", "standard_price", "business_price"):
            v = p.get(k)
            if isinstance(v, str):
                errs.append(f"pricing.{k} must be a number, not a formatted string ({v!r})")
        if p.get("sale_price") is not None and p.get("standard_price") is not None and not p["sale_price"] < p["standard_price"]:
            errs.append("sale_price must be < standard_price under policy v3 (PRICE_POLICY_CONFLICT)")
        if p.get("business_price") is not None and p.get("standard_price") is not None and not p["business_price"] <= p["standard_price"]:
            errs.append("business_price must not exceed standard_price")
        if not p.get("currency"):
            errs.append("pricing.currency missing")
        tiers = p.get("quantity_tiers") or []
        if tiers:
            qs = [t.get("quantity") for t in tiers]
            ps = [t.get("price") for t in tiers]
            if any(not isinstance(q, int) for q in qs) or qs != sorted(set(qs)):
                errs.append("pricing.quantity_tiers: quantities must be integers in strictly ascending order")
            if any(not isinstance(x, (int, float)) for x in ps) or any(a <= b for a, b in zip(ps, ps[1:])):
                errs.append("pricing.quantity_tiers: prices must strictly decrease as quantity grows")
            g = p.get("guardrails") or {}
            if g.get("policy_status") != "USER_DECISION":
                errs.append("pricing.guardrails.policy_status must be USER_DECISION for tiers/bounds (not part of policy v3)")
            if g.get("business_min_rule", "").startswith("DEEPEST_TIER"):
                if p.get("business_min_price") != ps[-1]:
                    errs.append("business_min_price must equal the price of the largest-quantity tier (rule DEEPEST_TIER)")
        elif p.get("business_min_price") is not None or p.get("business_max_price") is not None:
            if (p.get("guardrails") or {}).get("policy_status") != "USER_DECISION":
                errs.append("B2B min/max present without guardrails.policy_status USER_DECISION")
    elif r["operation_intent"] in ("PRICE_ONLY", "OFFER_ONLY"):
        errs.append("PRICE_ONLY/OFFER_ONLY without pricing block")
    c = r.get("content") or {}
    if c and c.get("backend_search_terms") is not None:
        if len(c["backend_search_terms"].encode("utf-8")) != c.get("backend_bytes", -1):
            errs.append("content.backend_bytes does not match UTF-8 byte length")
    hs = r["hashes"]
    exp = seal_one(r, r["batch_id"], r["generated_by_agent_version"], r["generated_at"])
    for k in ("source_hash", "content_hash", "pricing_hash", "record_hash"):
        if hs.get(k) != exp["hashes"][k]:
            errs.append(f"hashes.{k} stale or missing: re-run `seal`")
    if r["idempotency_key"] != exp["idempotency_key"]:
        errs.append("idempotency_key stale or missing: re-run `seal`")
    return errs, warns


def load(path):
    txt = open(path, encoding="utf-8-sig").read()
    if path.endswith(".jsonl"):
        return [json.loads(l) for l in txt.splitlines() if l.strip()]
    d = json.loads(txt)
    return d if isinstance(d, list) else [d]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", nargs="?", choices=["seal", "validate"])
    ap.add_argument("inp", nargs="?")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--batch-id", default="BATCH")
    ap.add_argument("--agent-version", default="2.0.0")
    ap.add_argument("--example", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--now")
    a = ap.parse_args()
    if a.example:
        print(json.dumps(seal_one(EXAMPLE, "B20261008", "2.0.0", "2026-10-08T00:00:00Z"), indent=2, ensure_ascii=False))
        return 0
    if not a.cmd or not a.inp:
        ap.error("command and input required")
    recs = load(a.inp)
    if a.cmd == "seal":
        if not a.out:
            ap.error("seal needs OUT.jsonl")
        now = a.now or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with open(a.out, "w", encoding="utf-8") as f:
            for r in recs:
                f.write(json.dumps(seal_one(r, a.batch_id, a.agent_version, now), ensure_ascii=False, sort_keys=True) + "\n")
        print(f"sealed {len(recs)} records -> {a.out}")
        return 0
    bad, res = 0, []
    for i, r in enumerate(recs, 1):
        e, w = validate_one(r)
        bad += bool(e)
        res.append(dict(record=r.get("sku") or i, marketplace=r.get("marketplace"), valid=not e, errors=e, warnings=w))
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        for x in res:
            print(f"[{x['record']}/{x['marketplace']}] {'VALID' if x['valid'] else 'INVALID'}")
            for m in x["errors"]:
                print("   ERROR", m)
            for m in x["warnings"]:
                print("   WARN ", m)
        print(f"{len(recs) - bad}/{len(recs)} valid")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
