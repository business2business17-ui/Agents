"""Запуск: python examples/run_example.py examples/de_private_label_skincare.json"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mia.pipeline import analyze_file  # noqa: E402

path = sys.argv[1] if len(sys.argv) > 1 else "examples/de_private_label_skincare.json"
pkg = analyze_file(path)
d = pkg["decision"]
print(f"Decision: {d['status']}  rule={d['rule_fired']}  confidence={d['confidence']}  score={d['score']}")
for r in d.get("reasons", []):
    print("  -", r)
if d.get("conditional_after_fix"):
    print("  после устранения:", d["conditional_after_fix"])
print()
print(pkg.get("narrative", ""))
if pkg.get("warnings"):
    print("\nПредупреждения:")
    for w in pkg["warnings"]:
        print("  !", w)
out = Path(path).with_suffix(".decision_package.json")
out.write_text(json.dumps(pkg, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
print(f"\nDecision Package: {out}")
