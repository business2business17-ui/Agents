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
REFS = [MD, "amazon-categories.md", "live-research.md", "content-limits.md"]
PLAN = {
    "amazon-product-intelligence": ["pricing_engine.py", "margin_calc.py", "performance_calc.py", "handoff_tool.py",
                                    "marketplaces.py", "marketplaces.json", "google_link.py", "amazon_link.py", "content_limits.json"],
    "amazon-feed-compiler": ["pricing_engine.py", "handoff_tool.py", "marketplaces.py", "marketplaces.json", "google_link.py", "amazon_link.py", "xlsx_core.py", "xlsm_inspect.py", "xlsm_patch.py",
                             "workbook_guard.py", "validate_cells.py", "parse_processing_report.py", "compare_reports.py", "feed_pipeline.py"],
    "amazon-feed-error-agent": ["pricing_engine.py", "google_link.py", "amazon_link.py", "marketplaces.py", "marketplaces.json", "xlsx_core.py", "xlsm_inspect.py", "xlsm_patch.py",
                                "workbook_guard.py", "validate_cells.py", "parse_processing_report.py", "compare_reports.py", "feed_pipeline.py"],
}
# Design agent: link tools, marketplace table, categories and live-research knowledge (no Amazon feed/pricing code).
DESIGN = "amazon-creative-studio"
DESIGN_SCRIPTS = ["google_link.py", "amazon_link.py", "marketplaces.py", "marketplaces.json"]
DESIGN_REFS = ["amazon-categories.md", "live-research.md"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    stale = []
    for name, scripts in PLAN.items():
        skill = ROOT / "plugins" / name / "skills" / name
        pairs = ([(SH / s, skill / "scripts" / s) for s in scripts] + [(SH / m, skill / "references" / m) for m in REFS] + [
                 (SH / "project-memory.md", skill / "references" / "project-memory.md"),
                 (SH / "project-memory-template.md", skill / "assets" / "project-memory-template.md")])
        for src, dst in pairs:
            if a.check:
                if not dst.exists() or dst.read_bytes() != src.read_bytes():
                    stale.append(str(dst.relative_to(ROOT)))
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
    skill = ROOT / "plugins" / DESIGN / "skills" / DESIGN
    for src, dst in ([(SH / f, skill / "scripts" / f) for f in DESIGN_SCRIPTS] +
                     [(SH / f, skill / "references" / f) for f in DESIGN_REFS]):
        if a.check:
            if not dst.exists() or dst.read_bytes() != src.read_bytes():
                stale.append(str(dst.relative_to(ROOT)))
        else:
            shutil.copy2(src, dst)
    if a.check:
        print("STALE:\n  " + "\n  ".join(stale) if stale else "shared copies are up to date")
        return 1 if stale else 0
    print("synced shared components")
    return 0


if __name__ == "__main__":
    sys.exit(main())
