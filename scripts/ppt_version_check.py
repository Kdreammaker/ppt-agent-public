from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "1.0"


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")


def run(command: list[str], *, cwd: Path, timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False, timeout=timeout)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def git_value(repo: Path, command: list[str]) -> str | None:
    result = run(["git", *command], cwd=repo)
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def remote_head(repo: Path, remote: str, branch: str, *, skip_remote: bool) -> tuple[str | None, str | None]:
    if skip_remote:
        return None, "skipped"
    result = run(["git", "ls-remote", "--heads", remote, branch], cwd=repo, timeout=30)
    if result.returncode != 0:
        return None, (result.stderr or result.stdout).strip()[-500:] or "remote check failed"
    line = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
    if not line:
        return None, "remote branch not found"
    return line.split()[0], None


def repo_status(repo: Path, *, label: str, skip_remote: bool) -> dict[str, Any]:
    branch = git_value(repo, ["rev-parse", "--abbrev-ref", "HEAD"]) or "unknown"
    local = git_value(repo, ["rev-parse", "HEAD"])
    remote = git_value(repo, ["config", f"branch.{branch}.remote"]) or "origin"
    merge = git_value(repo, ["config", f"branch.{branch}.merge"]) or f"refs/heads/{branch}"
    remote_branch = merge.rsplit("/", 1)[-1]
    url = git_value(repo, ["remote", "get-url", remote])
    latest, error = remote_head(repo, remote, remote_branch, skip_remote=skip_remote)
    dirty = bool(run(["git", "status", "--porcelain"], cwd=repo).stdout.strip())
    status = "unknown"
    if local and latest:
        status = "up_to_date" if local == latest else "update_available"
    elif error == "skipped":
        status = "local_only"
    else:
        status = "remote_unreachable"
    return {
        "label": label,
        "path": repo.as_posix(),
        "branch": branch,
        "remote": remote,
        "remote_url_configured": bool(url),
        "remote_url_host": url.split("@")[-1].split("/")[0] if url else None,
        "remote_branch": remote_branch,
        "local_head": local,
        "remote_head": latest,
        "status": status,
        "dirty": dirty,
        "error": error,
        "policy_summary": {
            "tokens_printed": False,
            "remote_url_redacted_to_host": True,
            "network_check_performed": not skip_remote,
        },
    }


def private_runtime_from_workspace(workspace: Path | None) -> Path | None:
    if workspace is None:
        return None
    config = read_json(workspace / ".ppt-agent" / "private_connector.json")
    root = config.get("private_package_install_root")
    if not isinstance(root, str) or not root:
        return None
    path = Path(root)
    if not path.is_absolute():
        path = workspace / path
    return path.resolve() if (path / ".git").exists() else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check public/private repo channel freshness without printing secrets.")
    parser.add_argument("--workspace", default=None)
    parser.add_argument("--private-runtime", default=None)
    parser.add_argument("--report", default="outputs/reports/version_check.json")
    parser.add_argument("--skip-remote", action="store_true")
    parser.add_argument("--require-latest", action="store_true")
    args = parser.parse_args(argv)

    workspace = Path(args.workspace).resolve() if args.workspace else None
    private_runtime = Path(args.private_runtime).resolve() if args.private_runtime else private_runtime_from_workspace(workspace)
    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = (BASE_DIR / report_path).resolve()

    repos = [repo_status(BASE_DIR, label="public_control_plane", skip_remote=args.skip_remote)]
    if private_runtime and (private_runtime / ".git").exists():
        repos.append(repo_status(private_runtime, label="private_runtime", skip_remote=args.skip_remote))

    blocking = [
        repo["label"]
        for repo in repos
        if args.require_latest and repo.get("status") not in {"up_to_date", "local_only"}
    ]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "command": "ppt_version_check",
        "generated_at": utc_now(),
        "status": "valid" if not blocking else "blocked",
        "summary": {
            "repos": len(repos),
            "update_available": [repo["label"] for repo in repos if repo.get("status") == "update_available"],
            "remote_unreachable": [repo["label"] for repo in repos if repo.get("status") == "remote_unreachable"],
            "dirty": [repo["label"] for repo in repos if repo.get("dirty")],
            "blocking": blocking,
        },
        "repositories": repos,
    }
    write_json(report_path, payload)
    print(json.dumps({"status": payload["status"], "summary": payload["summary"], "report": report_path.as_posix()}, indent=2))
    return 0 if not blocking else 2


if __name__ == "__main__":
    raise SystemExit(main())
