#!/usr/bin/env python3
"""Create a working folder for one project (brand / product line) with the layout the agents expect.

Usage:  python3 tools/init_project.py DIR [--only amazon|design]

DIR/inbox/                                                            drop your source files here
DIR/amazon-project/PROJECT.md + agent1/ agent2/ agent3/ subfolders   (Product Intelligence, Feed Compiler, Feed Error Agent)
DIR/creative-studio/PROJECT.md + out/                                 (Design agent, if it is installed)
Existing PROJECT.md files are never overwritten. Start `claude` inside DIR, drop your files into the folders and describe the task.
"""
import argparse
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AMAZON_DIRS = ["agent1/normalized", "agent1/evidence", "agent1/competitors", "agent1/seo", "agent1/output/json", "agent1/output/jsonl",
               "agent1/output/xlsx", "agent1/output/issues", "agent1/versions",
               "agent2/templates/raw", "agent2/mappings", "agent2/overrides", "agent2/feeds/generated", "agent2/feeds/validated",
               "agent2/manifests", "agent2/validation", "agent2/provenance", "agent2/mutations", "agent2/processing-reports",
               "agent3/source", "agent3/working", "agent3/corrected", "agent3/reports", "agent3/change-sets", "agent3/diffs"]


def find_template(plugin):
    base = os.path.join(ROOT, "plugins", plugin, "skills", plugin, "assets", "project-memory-template.md")
    return base if os.path.exists(base) else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir")
    ap.add_argument("--only", choices=["amazon", "design"])
    a = ap.parse_args()
    made = []
    os.makedirs(os.path.join(a.dir, "inbox"), exist_ok=True)  # drop source files here (XLSX, images, exports, templates)
    if a.only in (None, "amazon"):
        tpl = find_template("amazon-product-intelligence")
        if tpl:
            base = os.path.join(a.dir, "amazon-project")
            for d in AMAZON_DIRS:
                os.makedirs(os.path.join(base, d), exist_ok=True)
            dst = os.path.join(base, "PROJECT.md")
            if not os.path.exists(dst):
                shutil.copyfile(tpl, dst)
            made.append(base)
        elif a.only == "amazon":
            sys.exit("Amazon agents are not in this folder")
    if a.only in (None, "design"):
        tpl = find_template("amazon-creative-studio")
        if tpl:
            base = os.path.join(a.dir, "creative-studio")
            os.makedirs(os.path.join(base, "out"), exist_ok=True)
            dst = os.path.join(base, "PROJECT.md")
            if not os.path.exists(dst):
                shutil.copyfile(tpl, dst)
            made.append(base)
        elif a.only == "design":
            sys.exit("the Design agent is not in this folder")
    if not made:
        sys.exit("no agents found next to this tool")
    print("ready:", *made, sep="\n  ")
    print(f"next: cd {a.dir} && claude   (put source files into ./inbox or the agent folders)")


if __name__ == "__main__":
    main()
