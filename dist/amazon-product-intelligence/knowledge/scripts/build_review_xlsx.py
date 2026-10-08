#!/usr/bin/env python3
"""Build the human-review XLSX from sealed handoff records (spec sections 69-79, 102).

Usage: build_review_xlsx.py handoff.jsonl|json review.xlsx
Sheets: Products, Content, Pricing, Attributes, Compatibility, Claims, Warnings, Images, Versions, Audit, Handoff.
Identifiers are written as text (leading zeros preserved). Never edits the source records.
"""
import json
import sys

try:
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
except ImportError:
    sys.exit("openpyxl is required: pip install openpyxl")


def load(path):
    txt = open(path, encoding="utf-8-sig").read()
    if path.endswith(".jsonl"):
        return [json.loads(l) for l in txt.splitlines() if l.strip()]
    d = json.loads(txt)
    return d if isinstance(d, list) else [d]


def j(v):
    return json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    recs = load(sys.argv[1])
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    def sheet(name, header, rows):
        ws = wb.create_sheet(name)
        ws.append(header)
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="1F4E78")
        for r in rows:
            ws.append([("'" + v if False else v) for v in r])
        for i, h in enumerate(header, 1):
            ws.column_dimensions[get_column_letter(i)].width = min(60, max(12, len(h) + 2))
        for row in ws.iter_rows(min_row=2):
            for c in row:
                c.alignment = Alignment(wrap_text=True, vertical="top")
                if isinstance(c.value, str):
                    c.data_type = "s"
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions

    P, C, PR, AT, CO, CL, W, IM, V, AU, H = ([] for _ in range(11))
    for r in recs:
        i = r.get("identifiers") or {}
        pt = r.get("product_type") or {}
        cat = r.get("catalog") or {}
        P.append([r.get("internal_product_id"), r.get("sku"), i.get("ean"), i.get("upc"), i.get("gtin"), i.get("gtin_exempt"),
                  i.get("asin"), cat.get("brand"), cat.get("product_name"), cat.get("model"), pt.get("value"), r.get("marketplace"),
                  cat.get("country_of_origin"), r.get("publish_status")])
        c = r.get("content") or {}
        b = (c.get("bullet_points") or []) + [None] * 5
        C.append([r.get("sku"), r.get("marketplace"), c.get("language"), c.get("title"), c.get("item_highlights"), *b[:5],
                  c.get("description"), c.get("backend_search_terms"), c.get("backend_bytes")])
        p = r.get("pricing") or {}
        PR.append([r.get("sku"), r.get("marketplace"), p.get("currency"), p.get("sale_price"), p.get("standard_price"),
                   p.get("list_price"), p.get("map_price"), p.get("minimum_seller_allowed_price"),
                   p.get("maximum_seller_allowed_price"), p.get("business_price"), p.get("business_price_status"),
                   j(p.get("quantity_tiers")), p.get("pricing_policy_version")])
        for k, v in (cat.get("attributes") or {}).items():
            v = v if isinstance(v, dict) else {"value": v}
            AT.append([r.get("sku"), k, j(v.get("value")), v.get("source"), v.get("confidence"), v.get("required"), v.get("status")])
        comp = r.get("compatibility") or {}
        for m in comp.get("items", [comp] if comp else []):
            CO.append([r.get("sku"), m.get("compatible_brand"), m.get("compatible_model"), m.get("compatible_generation"),
                       m.get("compatible_year"), m.get("compatible_device"), m.get("not_compatible_with"), m.get("source"), m.get("confidence")])
        for cl in r.get("claims") or []:
            CL.append([r.get("sku"), cl.get("claim"), cl.get("source"), cl.get("evidence"), cl.get("claim_type"), cl.get("risk"),
                       cl.get("status"), cl.get("action")])
        for w in r.get("hard_blockers") or []:
            W.append([r.get("sku"), "HARD_BLOCKER", "HIGH", None, w, "Resolve before publishing"])
        for w in r.get("warnings") or []:
            W.append([r.get("sku"), "WARNING", "LOW", None, w, "Review"])
        for e in r.get("evidence") or []:
            if e.get("image"):
                IM.append([r.get("sku"), e.get("image"), e.get("image_type"), e.get("matched_product"), e.get("match_confidence"),
                           j(e.get("extracted")), e.get("required"), e.get("status")])
        v = r.get("versions") or {}
        h = r.get("hashes") or {}
        V.append([r.get("sku"), r.get("marketplace"), r.get("record_version"), v.get("seo_version"), v.get("product_data_version"),
                  v.get("pricing_policy_version") or p.get("pricing_policy_version"), v.get("amazon_policy_version"),
                  h.get("source_hash"), h.get("content_hash"), r.get("generated_at")])
        AU.append([r.get("sku"), j(r.get("audit"))])
        H.append([r.get("handoff_schema_version"), r.get("batch_id"), r.get("internal_product_id"), r.get("sku"), r.get("marketplace"),
                  r.get("record_version"), r.get("operation_intent"), r.get("publish_status"), r.get("identifier_mode"), pt.get("value"),
                  "LOCKED" if pt.get("locked") else pt.get("status"), j(r.get("changed_fields")), j(r.get("unresolved_required_fields")),
                  j(r.get("hard_blockers")), j(r.get("warnings")), h.get("source_hash"), h.get("content_hash"), h.get("pricing_hash"),
                  h.get("record_hash"), r.get("idempotency_key"), r.get("generated_at"), r.get("generated_by_agent_version")])
    sheet("Products", ["Internal Product ID", "SKU", "EAN", "UPC", "GTIN", "GTIN Exempt", "ASIN", "Brand", "Product Name", "Model",
                       "Product Type", "Marketplace", "Country of Origin", "Publish Status"], P)
    sheet("Content", ["SKU", "Marketplace", "Language", "Title", "Item Highlights", "Bullet 1", "Bullet 2", "Bullet 3", "Bullet 4",
                      "Bullet 5", "Description", "Backend Search Terms", "Backend Bytes"], C)
    sheet("Pricing", ["SKU", "Marketplace", "Currency", "Sale Price", "Standard Price", "List Price", "MAP", "Min Seller Allowed Price",
                      "Max Seller Allowed Price", "Business Price", "Business Price Status", "Quantity Tiers", "Pricing Policy Version"], PR)
    sheet("Attributes", ["SKU", "Attribute", "Value", "Source", "Confidence", "Required", "Status"], AT)
    sheet("Compatibility", ["SKU", "Compatible Brand", "Compatible Model", "Generation", "Year", "Device", "Not Compatible With",
                            "Source", "Confidence"], CO)
    sheet("Claims", ["SKU", "Claim", "Source", "Evidence", "Claim Type", "Risk", "Status", "Action"], CL)
    sheet("Warnings", ["SKU", "Issue Type", "Severity", "Field", "Issue", "Recommended Action"], W)
    sheet("Images", ["SKU", "Image", "Image Type", "Matched Product", "Match Confidence", "Evidence Extracted", "Required / Optional", "Status"], IM)
    sheet("Versions", ["SKU", "Marketplace", "Listing Version", "SEO Version", "Product Data Version", "Pricing Policy Version",
                       "Amazon Policy Version", "Source Hash", "Content Hash", "Last Updated"], V)
    sheet("Audit", ["SKU", "Audit (JSON)"], AU)
    sheet("Handoff", ["Handoff Schema Version", "Batch ID", "Internal Product ID", "SKU", "Marketplace", "Record Version",
                      "Operation Intent", "Publish Status", "Identifier Mode", "Product Type", "Product Type Status", "Changed Fields",
                      "Unresolved Required Fields", "Hard Blockers", "Warnings", "Source Hash", "Content Hash", "Pricing Hash",
                      "Record Hash", "Idempotency Key", "Generated At", "Generated By Agent Version"], H)
    wb.save(sys.argv[2])
    print(f"wrote {sys.argv[2]}: {len(recs)} records, 11 sheets")


if __name__ == "__main__":
    main()
