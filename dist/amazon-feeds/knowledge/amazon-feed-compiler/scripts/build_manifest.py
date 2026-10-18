#!/usr/bin/env python3
"""Build Feed_Manifest.json and the submission package checksum for a generated feed (spec sections 35, 86, 109).

Usage:
  build_manifest.py --feed OUT.xlsm --template CLEAN.xlsm --handoff sealed.jsonl --batch-id B1 --marketplace DE
        [--artifacts mapping.json validation.json provenance.jsonl ...] [--part 1] [--execution-mode LOCAL_POWERSHELL]
        [--repo owner/name --branch main --commit SHA] [--agent-version 2.0.0] [--out Feed_Manifest_B1.json]
Records: sha256/size of feed, template and every artifact, operation counts and publish-status counts from the handoff,
template fingerprint (header / validation / structure hashes), execution context, and
submission_package_checksum = sha256 over the sorted (name, sha256) pairs of feed + manifest inputs + artifacts.
Deterministic: same inputs -> same checksum (timestamps are metadata and are excluded from the checksum).
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--feed", required=True)
    ap.add_argument("--template", required=True)
    ap.add_argument("--handoff", required=True)
    ap.add_argument("--batch-id", required=True)
    ap.add_argument("--marketplace", required=True)
    ap.add_argument("--artifacts", nargs="*", default=[])
    ap.add_argument("--part", type=int, default=1)
    ap.add_argument("--execution-mode", default="USER_UPLOAD",
                    choices=["LOCAL_POWERSHELL", "GITHUB_BROWSER", "HYBRID", "USER_UPLOAD"])
    ap.add_argument("--repo")
    ap.add_argument("--branch")
    ap.add_argument("--commit")
    ap.add_argument("--agent-version", default="2.0.0")
    ap.add_argument("--sheet")
    ap.add_argument("--out")
    a = ap.parse_args()

    recs = []
    for line in open(a.handoff, encoding="utf-8-sig"):
        if line.strip():
            recs.append(json.loads(line))
    if not recs:  # plain json
        d = json.load(open(a.handoff, encoding="utf-8-sig"))
        recs = d if isinstance(d, list) else [d]
    recs = [r for r in recs if r.get("marketplace") in (None, a.marketplace)]

    fp = {}
    try:
        tmp = a.out + ".inspect.tmp" if a.out else "inspect.tmp.json"
        cmd = [sys.executable, os.path.join(HERE, "xlsm_inspect.py"), a.template, "--json", tmp] + (["--sheet", a.sheet] if a.sheet else [])
        subprocess.run(cmd, check=True, capture_output=True)
        insp = json.load(open(tmp, encoding="utf-8"))
        os.remove(tmp)
        fp = insp.get("fingerprint", {})
        tpl = dict(template_sheet=insp.get("template_sheet"), macros_present=insp.get("macros_present"), kind=insp.get("kind"))
    except Exception as e:  # noqa: BLE001
        tpl = dict(error=f"template inspection failed: {e}")

    files = {"feed": a.feed, "template": a.template, "handoff": a.handoff}
    for i, p in enumerate(a.artifacts, 1):
        files[f"artifact_{i}:{os.path.basename(p)}"] = p
    hashes = {k: dict(path=p, sha256=sha(p), size=os.path.getsize(p)) for k, p in files.items()}
    pairs = sorted((os.path.basename(v["path"]), v["sha256"]) for v in hashes.values())
    checksum = hashlib.sha256(json.dumps(pairs).encode()).hexdigest()
    manifest = dict(
        feed_filename=os.path.basename(a.feed), marketplace=a.marketplace, batch_id=a.batch_id, part_number=a.part,
        sku_count=len({r.get("sku") for r in recs}), record_count=len(recs),
        operation_counts=dict(Counter(r.get("operation_intent") for r in recs)),
        publish_status_counts=dict(Counter(r.get("publish_status") for r in recs)),
        blocked_count=sum(r.get("publish_status") not in ("READY_TO_PUBLISH", "READY_WITH_WARNINGS") for r in recs),
        handoff_schema_versions=sorted({r.get("handoff_schema_version") for r in recs}),
        template=tpl, template_fingerprint=fp, files=hashes, submission_package_checksum=checksum,
        execution_context=dict(execution_mode=a.execution_mode, working_directory=os.getcwd() if a.execution_mode.startswith("LOCAL") else None,
                               repository=a.repo, branch=a.branch, source_commit_sha=a.commit),
        agent2_version=a.agent_version, pricing_policy_version="2026-10-08-v3",
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    text = json.dumps(manifest, ensure_ascii=False, indent=2)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(text + "\n")
        print(f"wrote {a.out}; submission_package_checksum={checksum}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
