"""Capture verified upstream releases for review without changing deployed images."""

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen


UPSTREAM = "ChatbotXIO/ChatbotX"
FIRST_RELEASE = "2026-11-18T03:31:03Z"  # Include the initial v1.22.0 candidate.
SERVICES = ("builder", "worker", "realtime", "javascript-executor")
VERSION = re.compile(r"v\d+\.\d+\.\d+", re.ASCII)
DIGEST = re.compile(r"^Digest:\s+(sha256:[0-9a-f]{64})\s*$", re.MULTILINE)


def command(*arguments, directory=None):
    return subprocess.run(arguments, cwd=directory, check=True, text=True,
                          stdout=subprocess.PIPE).stdout.strip()


def official_releases():
    url = f"https://api.github.com/repos/{UPSTREAM}/releases?per_page=100"
    while url:
        request = Request(url, headers={"Accept": "application/vnd.github+json",
                                        "User-Agent": "VINCHI-ChatbotX-release-review"})
        with urlopen(request, timeout=30) as response:
            releases = json.load(response)
            links = response.headers.get("Link", "")
        for release in releases:
            if (not release["draft"] and not release["prerelease"]
                    and release["published_at"] >= FIRST_RELEASE):
                yield release
        next_page = re.search(r'<(https://api\.github\.com/[^>]+)>; rel="next"', links)
        url = next_page.group(1) if next_page else None


def release_candidate(release):
    tag = release["tag_name"]
    if not VERSION.fullmatch(tag):
        raise ValueError(f"Unsupported stable upstream tag format: {tag!r}")
    git_ref = f"refs/tags/{tag}"
    refs = dict(line.split("\t")[::-1] for line in command(
        "git", "ls-remote", f"https://github.com/{UPSTREAM}.git",
        git_ref, f"{git_ref}^{{}}").splitlines())
    commit = refs.get(f"{git_ref}^{{}}", refs.get(git_ref, ""))
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError(f"Couldn't resolve the official commit for {tag}")
    images = {}
    for service in SERVICES:
        image = f"ghcr.io/chatbotxio/chatbotx-{service}:{tag[1:]}"
        manifest = command("docker", "buildx", "imagetools", "inspect", image)
        digest = DIGEST.search(manifest)
        if not digest or not re.search(r"^\s*Platform:\s+linux/amd64\s*$", manifest, re.MULTILINE):
            raise ValueError(f"Unable to verify the linux/amd64 image and digest for {image}")
        images[service] = f"{image}@{digest.group(1)}"
    return {"release": tag, "published_at": release["published_at"],
            "url": f"https://github.com/{UPSTREAM}/releases/tag/{tag}",
            "commit": commit, "images": images}


def propose(release, base_branch, repository):
    release_id = int(release["id"])
    branch = f"upstream/chatbotx-release-{release_id}"
    candidate = release_candidate(release)
    tag = candidate["release"]
    target = Path("upstream-releases") / f"{tag}.json"
    payload = json.dumps(candidate, indent=2) + "\n"
    if target.exists() and target.read_text(encoding="utf-8") == payload:
        return

    remote = command("git", "ls-remote", "origin", f"refs/heads/{branch}")
    if remote:
        command("git", "fetch", "--no-tags", "origin", f"refs/heads/{branch}")
        if command("git", "show", f"FETCH_HEAD:{target.as_posix()}") != payload.strip():
            raise ValueError(f"Existing branch {branch} has different release data. Review it manually.")
    else:
        with tempfile.TemporaryDirectory() as temporary:
            worktree = Path(temporary) / "checkout"
            command("git", "worktree", "add", "--detach", str(worktree), "HEAD")
            try:
                destination = worktree / target
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(payload, encoding="utf-8")
                command("git", "add", "--", str(target), directory=worktree)
                command("git", "-c", "user.name=github-actions[bot]",
                        "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com",
                        "commit", "-m", f"Record official ChatbotX {tag}", directory=worktree)
                command("git", "push", "origin", f"HEAD:refs/heads/{branch}", directory=worktree)
            finally:
                command("git", "worktree", "remove", str(worktree))
    compare = f"https://github.com/{repository}/compare/{quote(base_branch, safe='')}...{quote(branch, safe='')}?expand=1"
    summary = f"- [{tag}]({compare}) · official source commit `{candidate['commit']}`\n"
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as output:
            output.write(summary)
    print(f"{tag}: saved for review at {compare}")


def main():
    dry_run = "--dry-run" in sys.argv or os.getenv("DRY_RUN") == "true"
    releases = sorted(official_releases(), key=lambda release: release["published_at"])
    failures = []
    for release in releases:
        try:
            if dry_run:
                print(json.dumps(release_candidate(release), indent=2))
            else:
                propose(release, os.environ["DEFAULT_BRANCH"], os.environ["GITHUB_REPOSITORY"])
        except (ValueError, subprocess.CalledProcessError) as failure:
            failures.append(release["tag_name"])
            print(f"{release['tag_name']}: {failure}", file=sys.stderr)
    if failures:
        sys.exit(f"Could not verify or save {', '.join(failures)}. These will be checked again.")


if __name__ == "__main__":
    main()
