#!/usr/bin/env python3
"""Copy shared Amazon components (shared/amazon/) into every Amazon skill that uses them.

Single source of truth: shared/amazon/. Plugins must be self-contained (installed one by one), so each skill carries
its own copy. Run after editing shared/; `--check` exits 1 if a copy is stale (CI).
"""
import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SH = ROOT / "shared" / "amazon"
MD = "shared-pricing-and-updates.md"
PLAN = {
    "amazon-product-intelligence": ["pricing_engine.py", "margin_calc.py", "performance_calc.py", "handoff_tool.py",
                                    "marketplaces.py", "marketplaces.json", "google_link.py", "amazon_link.py"],
    "amazon-feed-compiler": ["pricing_engine.py", "handoff_tool.py", "marketplaces.py", "marketplaces.json", "google_link.py", "amazon_link.py", "xlsx_core.py", "xlsm_inspect.py", "xlsm_patch.py",
                             "workbook_guard.py", "validate_cells.py", "parse_processing_report.py", "compare_reports.py"],
    "amazon-feed-error-agent": ["pricing_engine.py", "google_link.py", "amazon_link.py", "marketplaces.py", "marketplaces.json", "xlsx_core.py", "xlsm_inspect.py", "xlsm_patch.py",
                                "workbook_guard.py", "validate_cells.py", "parse_processing_report.py", "compare_reports.py"],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    stale = []
    for name, scripts in PLAN.items():
        skill = ROOT / "plugins" / name / "skills" / name
        pairs = ([(SH / s, skill / "scripts" / s) for s in scripts] + [(SH / MD, skill / "references" / MD),
                 (SH / "project-memory.md", skill / "references" / "project-memory.md"),
                 (SH / "project-memory-template.md", skill / "assets" / "project-memory-template.md")])
        for src, dst in pairs:
            if a.check:
                if not dst.exists() or dst.read_bytes() != src.read_bytes():
                    stale.append(str(dst.relative_to(ROOT)))
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
    if a.check:
        print("STALE:\n  " + "\n  ".join(stale) if stale else "shared copies are up to date")
        return 1 if stale else 0
    print("synced shared components")
    return 0


if __name__ == "__main__":
    sys.exit(main())
