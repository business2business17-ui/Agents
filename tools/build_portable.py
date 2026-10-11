#!/usr/bin/env python3
"""Build AI-agnostic bundles from the plugin sources (single source of truth: plugins/).

For every plugins/<name>/ writes dist/<name>/:
  system-prompt.md        full self-contained agent prompt (protocol + all references inlined)
                          -> Claude Projects, Gemini Gems, Cursor rules, Codex/AGENTS.md, any API system prompt
  instructions-short.md   protocol only, <= 8000 chars
                          -> Custom GPT "Instructions" field (upload knowledge/ as Knowledge files)
  knowledge/              references, scripts, assets as separate files
and dist/<name>.zip with all of the above.

Usage: build_portable.py [--check]   (--check exits 1 if dist/ is stale; for CI)
"""
import argparse
import re
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHORT_LIMIT = 8000
SHORT_DROP = ("## 2.", "## 5.", "## 6.")


def split_frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, m.group(2).lstrip("\n")


def build_one(plugin: Path):
    name = plugin.name
    skill_dir = next((plugin / "skills").iterdir())
    agent_meta, agent_body = split_frontmatter((plugin / "agents" / f"{name}.md").read_text(encoding="utf-8"))
    skill_meta, skill_body = split_frontmatter((skill_dir / "SKILL.md").read_text(encoding="utf-8"))

    refs = sorted((skill_dir / "references").glob("*.md"))
    parts = [f"# {name}\n\n{agent_meta.get('description', '')}\n", agent_body.strip(), skill_body.strip(),
             "\n---\n# KNOWLEDGE BASE (reference files; read the named file when the protocol points to it)\n"]
    parts.append("Script files (`scripts/*.py`) and `assets/` are separate files; if you cannot execute scripts, "
                 "apply their checks manually as described in `references/qa-preflight.md` and produce the "
                 "workbook columns per `references/xlsx-output.md`.\n")
    for r in refs:
        parts.append(f"\n## FILE: references/{r.name}\n\n{r.read_text(encoding='utf-8').strip()}\n")
    system_prompt = "\n\n".join(parts).replace("\n\n\n\n", "\n\n") + "\n"

    sections = re.split(r"\n(?=## )", skill_body.strip())
    kept = [s for s in sections if not s.startswith(SHORT_DROP)]
    short = ("\n".join(kept).strip() +
             "\n\nKNOWLEDGE: the files `references/*.md` are attached as knowledge; open the one named in each "
             "step when you reach it. Project memory: if you cannot write files, print the updated memory block "
             "at the end of each reply and ask the user to paste it next session.\n")
    if len(short) > SHORT_LIMIT:
        raise SystemExit(f"{name}: instructions-short.md is {len(short)} chars (> {SHORT_LIMIT}); trim SKILL.md")

    out = {}
    out[f"dist/{name}/system-prompt.md"] = system_prompt
    out[f"dist/{name}/instructions-short.md"] = short
    for sub in ("references", "scripts", "assets"):
        for f in sorted((skill_dir / sub).glob("*")):
            if f.is_file() and f.name != "__pycache__":
                out[f"dist/{name}/knowledge/{sub}/{f.name}"] = f.read_bytes()
    return name, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    stale = []
    for plugin in sorted((ROOT / "plugins").iterdir()):
        if not (plugin / "agents").is_dir():
            continue
        name, files = build_one(plugin)
        for rel, data in files.items():
            p = ROOT / rel
            raw = data.encode("utf-8") if isinstance(data, str) else data
            if a.check:
                if not p.exists() or p.read_bytes() != raw:
                    stale.append(rel)
            else:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(raw)
        if not a.check:
            z = ROOT / "dist" / f"{name}.zip"
            with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
                for rel in files:
                    zf.write(ROOT / rel, Path(rel).relative_to("dist"))
            print(f"built dist/{name}/ ({len(files)} files), {z.relative_to(ROOT)}")
    if a.check:
        if stale:
            print("STALE:", *stale, sep="\n  ")
            return 1
        print("dist/ is up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
