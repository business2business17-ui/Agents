#!/usr/bin/env python3
"""Keep all design work (renders, images, A+, carousel, briefs) on the branch AMZ-DESIGN.

The Design agent creates / switches to that branch itself before it writes or commits anything; automatic session
branches (claude/...) are not used for design output.

  design_branch.py ensure [--branch AMZ-DESIGN] [--base main] [--remote origin]
      switch to the branch (local, else tracking the remote one, else create it from <remote>/<base>); uncommitted
      files are carried over; stops if they would be overwritten
  design_branch.py commit -m "message" [--paths creative-studio images ...]
      ensure + stage only the given paths (default: creative-studio images) + commit; nothing staged = no commit
  design_branch.py push
      ensure + git push -u <remote> <branch> (4 attempts, waits 2 / 4 / 8 / 16 s on network errors)
Exit 0 = ok, 1 = git refused (message printed), 2 = not a git repository / usage.
"""
import argparse
import subprocess
import sys
import time


def git(*args, check=False):
    p = subprocess.run(["git", *args], capture_output=True, text=True)
    if check and p.returncode:
        raise RuntimeError((p.stderr or p.stdout).strip())
    return p


def ensure(branch, base, remote):
    if git("rev-parse", "--is-inside-work-tree").returncode:
        print("not a git repository", file=sys.stderr)
        return 2
    if git("branch", "--show-current").stdout.strip() == branch:
        print(f"already on {branch}")
        return 0
    fetched = git("fetch", remote).returncode == 0
    if not fetched:
        print(f"warning: could not fetch {remote}; using local refs", file=sys.stderr)
    local = git("show-ref", "--verify", "--quiet", f"refs/heads/{branch}").returncode == 0
    remote_has = git("show-ref", "--verify", "--quiet", f"refs/remotes/{remote}/{branch}").returncode == 0
    if local:
        cmd, how = ["checkout", branch], "switched to existing"
    elif remote_has:
        cmd, how = ["checkout", "-b", branch, "--track", f"{remote}/{branch}"], "created from remote"
    else:
        start = f"{remote}/{base}" if git("show-ref", "--verify", "--quiet", f"refs/remotes/{remote}/{base}").returncode == 0 else "HEAD"
        cmd, how = ["checkout", "-b", branch, start], f"created from {start}"
    p = git(*cmd)
    if p.returncode:
        print(f"cannot switch to {branch}: {(p.stderr or p.stdout).strip()}\n"
              "commit or stash the conflicting files first", file=sys.stderr)
        return 1
    print(f"{how} {branch}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["ensure", "commit", "push"])
    ap.add_argument("--branch", default="AMZ-DESIGN")
    ap.add_argument("--base", default="main")
    ap.add_argument("--remote", default="origin")
    ap.add_argument("-m", "--message")
    ap.add_argument("--paths", nargs="+", default=["creative-studio", "images"])
    a = ap.parse_args()
    rc = ensure(a.branch, a.base, a.remote)
    if rc or a.cmd == "ensure":
        return rc
    if a.cmd == "commit":
        if not a.message:
            print("commit needs -m MESSAGE", file=sys.stderr)
            return 2
        import os
        paths = [p for p in a.paths if os.path.exists(p)]
        if paths:
            git("add", "--", *paths)
        if git("diff", "--cached", "--quiet").returncode == 0:
            print("nothing to commit")
            return 0
        p = git("commit", "-m", a.message)
        print((p.stdout or p.stderr).strip().splitlines()[0] if (p.stdout or p.stderr).strip() else "committed")
        return 1 if p.returncode else 0
    delay = 2
    for attempt in range(5):
        p = git("push", "-u", a.remote, a.branch)
        if p.returncode == 0:
            print(f"pushed {a.branch}")
            return 0
        if attempt == 4:
            break
        time.sleep(delay)
        delay *= 2
    print((p.stderr or p.stdout).strip(), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
