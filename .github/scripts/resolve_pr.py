# NOTE: AI slop - generated, unreviewed.
#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import tempfile
import urllib.request

REPO = os.environ.get("GITHUB_REPOSITORY", "")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN", "")
FILE = "development-updates.md"
MERGE_SCRIPT = "/tmp/dev_updates.py"


def api(path):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "auto-merge-dev-updates",
        },
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def run(cmd, check=True, capture=False):
    print("+ " + " ".join(cmd), flush=True)
    res = subprocess.run(cmd, check=check, text=True, capture_output=capture)
    if capture:
        return res.stdout.strip()
    return ""


def git_show(ref_path):
    res = subprocess.run(["git", "show", ref_path], text=True, capture_output=True)
    return res.stdout if res.returncode == 0 else ""


def main(pr_number):
    pr = api(f"/repos/{REPO}/pulls/{pr_number}")
    if pr.get("state") != "open":
        print(f"PR #{pr_number} not open; skipping.")
        return 0

    head_repo = pr["head"]["repo"]["full_name"]
    head_branch = pr["head"]["ref"]
    head_sha = pr["head"]["sha"]
    base_branch = pr["base"]["ref"]
    maintainer_can_modify = pr.get("maintainer_can_modify", False)

    files = api(f"/repos/{REPO}/pulls/{pr_number}/files")
    if not any(f["filename"] == FILE for f in files):
        print(f"PR #{pr_number} does not touch {FILE}; skipping.")
        return 0

    owner = REPO.split("/")[0]
    auth_remote = f"https://x-access-token:{TOKEN}@github.com/{head_repo}.git"

    run(["git", "fetch", "origin", base_branch], check=True)
    # BUGFIX: reset remote each iteration; it may point at a different fork.
    run(["git", "remote", "remove", "prhead"], check=False)
    run(["git", "remote", "add", "prhead", auth_remote], check=True)
    run(["git", "fetch", "prhead", head_branch], check=True)

    head_ref = head_sha
    main_ref = f"origin/{base_branch}"

    merge_base = run(["git", "merge-base", head_ref, main_ref], capture=True)
    print(f"merge-base = {merge_base}")

    base_content = git_show(f"{merge_base}:{FILE}")
    ours_content = git_show(f"{head_ref}:{FILE}")
    theirs_content = git_show(f"{main_ref}:{FILE}")

    with tempfile.TemporaryDirectory() as d:
        bp, op, tp, mp = (os.path.join(d, n) for n in ("base", "ours", "theirs", "merged"))
        open(bp, "w").write(base_content)
        open(op, "w").write(ours_content)
        open(tp, "w").write(theirs_content)

        res = subprocess.run(
            [sys.executable, MERGE_SCRIPT, "merge", bp, op, tp, "--output", mp],
            text=True, capture_output=True,
        )
        print(res.stdout)
        print(res.stderr, file=sys.stderr)
        merged = open(mp).read()

    if res.returncode != 0:
        comment(pr_number,
                ":warning: Auto-merge could not resolve `development-updates.md` "
                "(two changes target the same cell). Look for `<!-- CONFLICT` markers.")
        print(f"PR #{pr_number}: real conflict, left a comment.")
        return 0

    if merged == ours_content:
        print(f"PR #{pr_number}: already up to date; nothing to push.")
        return 0

    if not maintainer_can_modify and head_repo.split("/")[0] != owner:
        comment(pr_number,
                ":information_source: This PR conflicts with `development-updates.md`. "
                "Enable \"Allow edits by maintainers\" and I'll re-run, or run "
                "`python scripts/dev_updates.py format development-updates.md` locally.")
        print(f"PR #{pr_number}: cannot push (maintainer edits disabled).")
        return 0

    run(["git", "checkout", "-B", "_autofix", head_ref])
    open(FILE, "w").write(merged)
    run(["git", "add", FILE])
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode
    if diff == 0:
        print(f"PR #{pr_number}: no net change; skipping push.")
        return 0
    run(["git", "commit", "-m", "Auto-merge main into development-updates.md"])
    run(["git", "push", "prhead", f"_autofix:{head_branch}"])
    comment(pr_number,
            ":white_check_mark: Synced `development-updates.md` with `main` and "
            "re-formatted. Your update is preserved and the PR should be mergeable.")
    print(f"PR #{pr_number}: pushed to {head_repo}:{head_branch}.")
    return 0


def comment(pr_number, body):
    data = json.dumps({"body": body}).encode()
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/issues/{pr_number}/comments",
        data=data,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "auto-merge-dev-updates",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        urllib.request.urlopen(req)
    except Exception as e:
        print(f"(could not post comment: {e})")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: resolve_pr.py <pr_number>", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(main(int(sys.argv[1])))
