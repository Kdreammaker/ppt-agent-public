from __future__ import annotations

import argparse
import datetime as dt
import importlib.metadata as importlib_metadata
import importlib.util
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "1.0"
MIN_PYTHON = (3, 11)
MODEL_VERSIONS = {
    "cli": "0.1.0",
    "workspace_contract": "0.2.0",
    "composer": "deterministic_intake_composer_v0",
    "renderer": "template_slide_renderer_v0",
    "mcp_adapter": "thin_cli_adapter_v0",
    "gateway_contract": "0.2.0",
    "premium_recommendation": "disabled",
}
CONSENT_MODES = {"workspace_only", "selected_folders", "manual_file_only", "no_local_assets"}
WORKSPACE_DIRS = [
    "intake",
    "specs",
    "decks",
    "html",
    "reports",
    "previews",
    "assets/images",
    "assets/logos",
    "assets/icons",
    "assets/fonts",
    "assets/references",
    "assets/slides",
    "assets/documents",
    "assets/templates",
    "data/intake",
    "data/specs",
    "outputs/decks",
    "outputs/html",
    "outputs/reports",
    ".ppt-agent/runs",
    ".ppt-agent/gateway_requests",
]


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def resolve_workspace(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    return path


def workspace_relative(path: str) -> str:
    return path.replace("\\", "/")


def write_human_guidance(lines: list[str]) -> None:
    print("\n".join(lines), file=sys.stderr)


def init_guidance(workspace: Path, summary: dict[str, Any]) -> list[str]:
    policy = summary.get("policy_summary", {})
    return [
        "",
        "PPT Agent developer preview workspace is ready.",
        f"- Workspace: {workspace.as_posix()}",
        f"- Mode: {policy.get('mode', 'local_only')}",
        f"- Uploads: {'enabled' if policy.get('upload_allowed') else 'disabled'}",
        f"- Telemetry: {'enabled' if policy.get('telemetry_enabled') else 'disabled'}",
        f"- README: {(workspace / 'README.md').as_posix()}",
        "",
        "First-run next steps:",
        f"1. python scripts/ppt_cli_workspace.py healthcheck --workspace {workspace.as_posix()}",
        f"2. python scripts/ppt_workspace_entitlement.py usage --workspace {workspace.as_posix()}",
        "3. Assistant Mode should show the structure blueprint before final PPTX/HTML build.",
        "4. Auto Mode may skip the blueprint checkpoint by policy.",
        "",
        "Current limitation: usage counters are local fixture state. Real cross-PC user/device monitoring requires the future private admin/gateway service.",
        "",
    ]


def healthcheck_guidance(report: dict[str, Any], report_json: Path, report_md: Path) -> list[str]:
    policy = report.get("policy_summary", {})
    versions = report.get("model_versions", {})
    return [
        "",
        "PPT Agent healthcheck complete.",
        f"- Status: {report.get('status')}",
        f"- Workspace: {report.get('workspace_root')}",
        f"- Healthcheck JSON: {report_json.as_posix()}",
        f"- Healthcheck report: {report_md.as_posix()}",
        f"- Mode: {policy.get('mode', 'local_only')}",
        f"- Gateway enabled: {policy.get('gateway_enabled', False)}",
        f"- Uploads: {'enabled' if policy.get('upload_allowed') else 'disabled'}",
        f"- Telemetry: {'enabled' if policy.get('telemetry_enabled') else 'disabled'}",
        f"- CLI version: {versions.get('cli')}",
        f"- Workspace contract: {versions.get('workspace_contract')}",
        f"- Composer: {versions.get('composer')}",
        f"- Renderer: {versions.get('renderer')}",
        f"- MCP adapter: {versions.get('mcp_adapter')}",
        "",
        "Usage and policy:",
        "- Local-only compose/build/validate can run without a workspace code.",
        "- Private beta entitlement usage is local fixture state in this preview.",
        "- Real active user/device counts, activation limits, and daily quota audit require the future private admin/gateway service.",
        "",
        "Assistant/Auto modes:",
        "- Assistant Mode: show the structure blueprint and wait for explicit approve/revise/continue/skip before final file generation.",
        "- Auto Mode: may skip the blueprint checkpoint by default.",
        "- The ASCII blueprint is structure-only; use HTML/PPTX preview or rendered thumbnails for visual approval.",
        "",
    ]


def default_config(workspace: Path, *, gateway_enabled: bool) -> dict[str, Any]:
    mode = "gateway_ai" if gateway_enabled else "local_only"
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": utc_now(),
        "workspace_root": workspace.as_posix(),
        "mode": mode,
        "gateway_enabled": gateway_enabled,
        "telemetry": "disabled",
        "upload_allowed": False,
        "outputs": {
            "specs": "specs/",
            "pptx": "decks/",
            "html": "html/",
            "reports": "reports/",
            "previews": "previews/",
        },
        "commands": {
            "plan": "python scripts/ppt_system.py blueprint intake/example.json --kind intake --approval-mode assistant",
            "compose": "python scripts/ppt_system.py compose-spec intake/example.json --output specs/example.json",
            "build": "python scripts/ppt_system.py build-outputs specs/example.json --validate --report-dir reports --html-output html/example.html",
            "validate": "python scripts/ppt_system.py gate",
        },
    }


def default_consent(
    workspace: Path,
    *,
    consent_mode: str,
    read_local_fonts: bool,
    read_workspace_assets: bool,
    read_local_templates: bool,
    gateway_asset_metadata_visible: bool,
    upload_allowed: bool,
) -> dict[str, Any]:
    if consent_mode not in CONSENT_MODES:
        raise ValueError(f"Unsupported consent mode: {consent_mode}")
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": utc_now(),
        "workspace_root": workspace.as_posix(),
        "consent_mode": consent_mode,
        "workspace_read": True,
        "read_local_fonts": read_local_fonts,
        "read_workspace_assets": read_workspace_assets,
        "selected_asset_folders": [],
        "read_local_templates": read_local_templates,
        "gateway_asset_metadata_visible": gateway_asset_metadata_visible,
        "upload_allowed": upload_allowed,
        "telemetry_enabled": False,
        "learning_collection_enabled": False,
        "notes": "Local-only defaults. Consent must be changed explicitly before reading external folders, uploading files, or enabling telemetry.",
    }


def default_gateway(*, gateway_enabled: bool) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": utc_now(),
        "gateway_enabled": gateway_enabled,
        "endpoint": None,
        "credential_storage": "os_keychain_or_local_ignored_config",
        "metadata_visible": False,
        "file_upload_allowed": False,
        "final_artifact_upload_allowed": False,
        "request_summary_dir": ".ppt-agent/gateway_requests/",
    }


def readme_text(workspace: Path) -> str:
    return f"""# PPT Workspace

This workspace stores local deck intake files, generated specs, PPTX decks, HTML output, previews, reports, and local assets.

## First Run

Run `python scripts/ppt_cli_workspace.py healthcheck --workspace {workspace.as_posix()}` after `python scripts/ppt_cli_workspace.py init --workspace {workspace.as_posix()}`. The healthcheck writes a JSON report for tools and a Markdown report for humans, covering OS, Python, package dependencies, PowerShell/PATH readiness, workspace write access, and the MCP adapter boundary.

The first-run files also explain local-only defaults, upload/telemetry policy, model/contract versions, and private-beta workspace-code behavior. If private-beta entitlement is activated, `python scripts/ppt_workspace_entitlement.py usage --workspace <workspace>` shows today's remaining call allowance and reset time without printing the raw workspace code.

## Basic Flow

1. Write or place an intake file under `intake/`.
2. In Assistant Mode, review the structure blueprint before creating output files. Auto Mode skips this checkpoint by default.
3. Compose a deck spec under `specs/`.
4. Build local PPTX and HTML outputs.
5. Validate the generated artifacts.

## Route Matrix

| Route | Assistant Mode | Auto Mode |
| --- | --- | --- |
| `python scripts/ppt_make.py` | Natural-language first-run wrapper. Creates planning artifacts, `draft_design_brief.md`, and `ppt_make_report.json`; waits with `status=waiting_for_approval`. Final PPTX/HTML requires `--build-approved` or `--continue-build`. | Natural-language fast draft route. Builds immediately. |
| `python scripts/ppt_agent.py` | Guide-packet/sparse-prompt route. Plans first by default; final files require `--build-approved`. | Builds two strategy-routed variants plus comparison/recommendation reports. |
| `python scripts/ppt_agent_mcp_adapter.py` | `deck_plan_compose` returns planning artifacts unless `build_approved=true`. | `two_variant_auto_build` renders variants without an approval checkpoint. |

## Commands

```powershell
python scripts/ppt_cli_workspace.py healthcheck --workspace {workspace.as_posix()}
python scripts/ppt_system.py blueprint {workspace.as_posix()}/intake/example.json --kind intake --approval-mode assistant
python scripts/ppt_system.py compose-spec {workspace.as_posix()}/intake/example.json --output {workspace.as_posix()}/specs/example.json
python scripts/ppt_system.py build-outputs {workspace.as_posix()}/specs/example.json --validate --report-dir {workspace.as_posix()}/reports --html-output {workspace.as_posix()}/html/example.html
python scripts/ppt_system.py gate
python scripts/mcp_adapter.py --list-tools
python scripts/ppt_workspace_entitlement.py status --workspace {workspace.as_posix()}
python scripts/ppt_workspace_entitlement.py usage --workspace {workspace.as_posix()}
```

## Output Folders

- `specs/`: generated deck specs
- `decks/`: editable PPTX outputs
- `html/`: browser presentation outputs
- `reports/`: validation and rationale reports
- `previews/`: screenshots, PDFs, or image previews
- `assets/`: local images, logos, icons, fonts, and templates
- `.ppt-agent/`: local config, consent, healthcheck, gateway summaries, and run state

## Privacy Defaults

This workspace defaults to local-only operation. Uploads, telemetry, public sharing, gateway calls, local font access, external folder access, and local asset indexing are off unless explicitly enabled.

MCP setup uses the same CLI/package APIs and the same local consent files. The adapter returns compact summaries and paths; it must not upload files, scan unrelated folders, or create a separate renderer/composer path.

Workspace-code activation is optional for local-only use. Private beta package access uses masked/hash-only entitlement state. Support bundles are explicit local files and are never uploaded automatically.

Private-beta quota policy: the current fixture contract supports 3 activations per workspace code and 100 calls per local day. The public CLI shows counts and remaining allowance only. These are local preview counters, not central external-PC monitoring. Private admin systems must own real user identity, activation counters, daily usage counters, code issuance records, revocation, rotation, and audit.

Model/contract versions: CLI `0.1.0`, workspace contract `0.2.0`, composer `deterministic_intake_composer_v0`, renderer `template_slide_renderer_v0`, MCP adapter `thin_cli_adapter_v0`, gateway contract `0.2.0`, premium recommendation `disabled`.

Blueprint policy: Assistant Mode shows the structure blueprint by default and requires an explicit approve, revise, continue, or skip decision before final PPTX/HTML generation. Auto Mode skips the blueprint checkpoint by default unless a workflow explicitly requests it. The ASCII blueprint is not a rendered visual preview; use HTML/PPTX preview or thumbnail rendering for visual approval.

Workspace path: `{workspace.as_posix()}`
"""


def command_init(args: argparse.Namespace) -> int:
    workspace = resolve_workspace(args.workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    for relative in WORKSPACE_DIRS:
        (workspace / relative).mkdir(parents=True, exist_ok=True)

    readme_path = workspace / "README.md"
    if args.force_readme or not readme_path.exists():
        readme_path.write_text(readme_text(workspace), encoding="utf-8")

    config_path = workspace / ".ppt-agent" / "config.json"
    consent_path = workspace / ".ppt-agent" / "consent.json"
    gateway_path = workspace / ".ppt-agent" / "gateway.json"

    config = default_config(workspace, gateway_enabled=args.gateway_enabled)
    consent = default_consent(
        workspace,
        consent_mode=args.consent_mode,
        read_local_fonts=args.read_local_fonts,
        read_workspace_assets=args.read_workspace_assets,
        read_local_templates=args.read_local_templates,
        gateway_asset_metadata_visible=args.gateway_asset_metadata_visible,
        upload_allowed=args.upload_allowed,
    )
    gateway = default_gateway(gateway_enabled=args.gateway_enabled)
    write_json(config_path, config)
    write_json(consent_path, consent)
    write_json(gateway_path, gateway)
    summary = {
        "command": "init",
        "status": "passed",
        "workspace_root": workspace.as_posix(),
        "artifact_paths": {
            "readme": workspace_relative("README.md"),
            "config": workspace_relative(".ppt-agent/config.json"),
            "consent": workspace_relative(".ppt-agent/consent.json"),
            "gateway": workspace_relative(".ppt-agent/gateway.json"),
        },
        "policy_summary": {
            "mode": config["mode"],
            "gateway_enabled": config["gateway_enabled"],
            "upload_allowed": consent["upload_allowed"],
            "telemetry_enabled": consent["telemetry_enabled"],
            "consent_mode": consent["consent_mode"],
        },
    }
    write_human_guidance(init_guidance(workspace, summary))
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def which(name: str) -> str | None:
    return shutil.which(name)


def command_output(args: list[str]) -> str | None:
    try:
        result = subprocess.run(args, check=False, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    output = (result.stdout or result.stderr).strip()
    return output.splitlines()[0] if output else None


def dependency_version(package_name: str) -> str | None:
    try:
        return importlib_metadata.version(package_name)
    except importlib_metadata.PackageNotFoundError:
        return None


def package_check(
    *,
    label: str,
    module_name: str,
    package_name: str,
    required: bool,
    fix_hint: str,
) -> dict[str, Any]:
    module_available = importlib.util.find_spec(module_name) is not None
    return {
        "required": required,
        "ok": module_available,
        "version": dependency_version(package_name) if module_available else None,
        "path": None,
        "message": f"{label} is available." if module_available else f"{label} is not installed.",
        "fix_hint": fix_hint,
    }


def check_record(
    *,
    required: bool,
    ok: bool,
    version: str | None = None,
    path: str | None = None,
    message: str,
    fix_hint: str,
) -> dict[str, Any]:
    return {
        "required": required,
        "ok": ok,
        "version": version,
        "path": path,
        "message": message,
        "fix_hint": fix_hint,
    }


def font_exists(font_names: list[str]) -> bool:
    candidates: list[Path] = []
    if platform.system().lower() == "windows":
        windir = Path(str(Path.home().drive) + "\\Windows") if Path(str(Path.home().drive) + "\\Windows").exists() else Path("C:/Windows")
        candidates.append(windir / "Fonts")
    candidates.extend([Path("/Library/Fonts"), Path("/System/Library/Fonts"), Path("/usr/share/fonts")])
    lowered = [name.lower() for name in font_names]
    for root in candidates:
        if not root.exists():
            continue
        try:
            for file in root.rglob("*"):
                file_name = file.name.lower()
                if any(name in file_name for name in lowered):
                    return True
        except OSError:
            continue
    return False


def healthcheck(workspace: Path) -> dict[str, Any]:
    workspace.mkdir(parents=True, exist_ok=True)
    config = read_json(workspace / ".ppt-agent" / "config.json")
    consent = read_json(workspace / ".ppt-agent" / "consent.json")
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    os_name = platform.system() or "unknown"
    powershell_path = which("pwsh") or which("powershell")
    node_path = which("node")
    npx_path = which("npx")
    soffice_path = which("soffice") or which("libreoffice")
    python_path_ok = Path(sys.executable).exists()
    path_lookup_ok = which("python") is not None or which("py") is not None or python_path_ok
    checks = {
        "os": check_record(
            required=True,
            ok=os_name.lower() in {"windows", "darwin", "linux"},
            version=f"{os_name} {platform.release()}",
            path=None,
            message=f"Detected {platform.platform()}.",
            fix_hint="Use Windows, macOS, or Linux for the invite-beta CLI/MCP flow.",
        ),
        "python": {
            "required": True,
            "ok": sys.version_info >= MIN_PYTHON,
            "version": python_version,
            "path": sys.executable,
            "message": f"Python {python_version} is running.",
            "fix_hint": "Install Python 3.11 or newer and rerun healthcheck.",
        },
        "path_lookup": check_record(
            required=True,
            ok=path_lookup_ok,
            version=None,
            path=sys.executable if python_path_ok else None,
            message="Python executable can be resolved for subprocess CLI calls." if path_lookup_ok else "Python was not found through PATH-style lookup.",
            fix_hint="Add Python to PATH or launch the CLI with the full Python path.",
        ),
        "powershell": check_record(
            required=os_name.lower() == "windows",
            ok=powershell_path is not None,
            version=command_output([powershell_path, "-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"]) if powershell_path else None,
            path=powershell_path,
            message="PowerShell is available for Windows setup commands." if powershell_path else "PowerShell was not found.",
            fix_hint="Install PowerShell or run from a shell that can execute the documented commands.",
        ),
        "python_package_pptx": package_check(
            label="python-pptx",
            module_name="pptx",
            package_name="python-pptx",
            required=True,
            fix_hint="Install python-pptx in the active Python environment.",
        ),
        "python_package_pillow": package_check(
            label="Pillow",
            module_name="PIL",
            package_name="Pillow",
            required=True,
            fix_hint="Install Pillow in the active Python environment.",
        ),
        "python_package_pymupdf": package_check(
            label="PyMuPDF",
            module_name="fitz",
            package_name="PyMuPDF",
            required=True,
            fix_hint="Install PyMuPDF in the active Python environment.",
        ),
        "python_package_pydantic": package_check(
            label="Pydantic",
            module_name="pydantic",
            package_name="pydantic",
            required=True,
            fix_hint="Install pydantic in the active Python environment.",
        ),
        "node": check_record(
            required=False,
            ok=node_path is not None,
            version=command_output(["node", "--version"]) if node_path else None,
            path=node_path,
            message="Node.js is available for optional bridge/dev workflows." if node_path else "Node.js is not available.",
            fix_hint="Install Node.js only if you need optional bridge/dev workflows.",
        ),
        "npx": check_record(
            required=False,
            ok=npx_path is not None,
            version=command_output(["npx", "--version"]) if npx_path else None,
            path=npx_path,
            message="npx is available for optional browser/tool workflows." if npx_path else "npx is not available.",
            fix_hint="Install npm/npx only if you need optional browser/tool workflows.",
        ),
        "libreoffice": check_record(
            required=False,
            ok=soffice_path is not None,
            version=command_output([soffice_path, "--version"]) if soffice_path else None,
            path=soffice_path,
            message="LibreOffice is available for PPTX render/preview conversion." if soffice_path else "LibreOffice was not found.",
            fix_hint="Install LibreOffice if PPTX preview rendering fails.",
        ),
        "cjk_font": check_record(
            required=False,
            ok=font_exists(["malgun", "malgun gothic", "noto sans cjk", "source han"]),
            version=None,
            path=None,
            message="A Korean/CJK-capable font was detected." if font_exists(["malgun", "malgun gothic", "noto sans cjk", "source han"]) else "No Korean/CJK font was detected by the quick scan.",
            fix_hint="Install Malgun Gothic, Noto Sans CJK, or Source Han Sans for better Korean output.",
        ),
        "mcp_adapter_policy": check_record(
            required=True,
            ok=True,
            version="thin_adapter_over_cli",
            path="scripts/mcp_adapter.py",
            message="MCP uses the public CLI/package APIs and local consent policy.",
            fix_hint="Do not configure a separate MCP renderer, composer, upload path, or workspace scanner.",
        ),
        "workspace_write": {
            "required": True,
            "ok": False,
            "version": None,
            "path": workspace.as_posix(),
            "message": "Workspace write probe has not run yet.",
            "fix_hint": "Choose a writable workspace folder and rerun healthcheck.",
        },
    }
    probe = workspace / ".ppt-agent" / "healthcheck.write-test"
    try:
        probe.parent.mkdir(parents=True, exist_ok=True)
        probe.write_text("ok\n", encoding="utf-8")
        probe.unlink(missing_ok=True)
        checks["workspace_write"]["ok"] = True
        checks["workspace_write"]["message"] = "Workspace write access is available."
    except OSError:
        checks["workspace_write"]["ok"] = False
        checks["workspace_write"]["message"] = "Workspace write access failed."

    required_failures = [name for name, check in checks.items() if check["required"] and not check["ok"]]
    optional_missing = [name for name, check in checks.items() if not check["required"] and not check["ok"]]
    next_actions = [checks[name]["fix_hint"] for name in required_failures]
    status = "failed" if required_failures else "passed"
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "command": "healthcheck",
        "status": status,
        "workspace_root": workspace.as_posix(),
        "required_failures": required_failures,
        "optional_missing": optional_missing,
        "next_actions": next_actions,
        "checks": checks,
        "policy_summary": {
            "mode": config.get("mode", "local_only"),
            "gateway_enabled": bool(config.get("gateway_enabled", False)),
            "upload_allowed": bool(consent.get("upload_allowed", False)),
            "telemetry_enabled": bool(consent.get("telemetry_enabled", False)),
            "consent_mode": consent.get("consent_mode", "workspace_only"),
            "mcp_adapter_shape": "thin_adapter_over_cli",
            "standalone_exe_required": False,
        },
        "model_versions": MODEL_VERSIONS,
    }


def write_healthcheck_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# PPT Workspace Healthcheck",
        "",
        f"- status: {report['status']}",
        f"- workspace: {report['workspace_root']}",
        f"- required failures: {len(report['required_failures'])}",
        f"- optional missing: {len(report['optional_missing'])}",
        "",
        "## Model And Contract Versions",
    ]
    for name, version in report.get("model_versions", {}).items():
        lines.append(f"- {name}: {version}")
    lines.extend([
        "",
        "## Human First-Run Guidance",
        "",
        "- Local-only compose/build/validate can run without a workspace code.",
        "- Private beta usage counters in this preview are local fixture state, not central external-PC monitoring.",
        "- Real active user/device counts, activation limits, daily quota audit, revocation, and rotation require the future private admin/gateway service.",
        "- Assistant Mode should show the structure blueprint and wait for an explicit approve, revise, continue, or skip decision before final PPTX/HTML generation.",
        "- Auto Mode may skip the blueprint checkpoint by default.",
        "- The ASCII blueprint is structure-only. Use HTML/PPTX preview or rendered thumbnails for visual approval.",
        "",
        "## Checks",
    ])
    for name, check in report["checks"].items():
        marker = "ok" if check["ok"] else "missing"
        required = "required" if check["required"] else "optional"
        lines.append(f"- {name}: {marker} ({required}) - {check.get('message', '')}")
        if not check["ok"]:
            lines.append(f"  Fix: {check.get('fix_hint', 'Resolve the missing dependency and rerun healthcheck.')}")
    if report.get("next_actions"):
        lines.extend(["", "## Next Actions"])
        lines.extend(f"- {item}" for item in report["next_actions"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def command_healthcheck(args: argparse.Namespace) -> int:
    workspace = resolve_workspace(args.workspace)
    report = healthcheck(workspace)
    report_json = workspace / ".ppt-agent" / "healthcheck.json"
    report_md = workspace / "reports" / "healthcheck.md"
    write_json(report_json, report)
    write_healthcheck_markdown(report_md, report)
    summary = {
        "command": "healthcheck",
        "status": report["status"],
        "workspace_root": report["workspace_root"],
        "artifact_paths": {
            "healthcheck_json": workspace_relative(".ppt-agent/healthcheck.json"),
            "healthcheck_md": workspace_relative("reports/healthcheck.md"),
        },
        "validation_summary": {
            "required_failures": report["required_failures"],
            "optional_missing": report["optional_missing"],
        },
        "policy_summary": report["policy_summary"],
        "model_versions": report.get("model_versions", {}),
    }
    write_human_guidance(healthcheck_guidance(report, report_json, report_md))
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 1 if report["required_failures"] else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Public CLI workspace init and healthcheck scaffold.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init")
    init.add_argument("--workspace", required=True)
    init.add_argument("--consent-mode", choices=sorted(CONSENT_MODES), default="workspace_only")
    init.add_argument("--read-local-fonts", action="store_true")
    init.add_argument("--read-workspace-assets", action="store_true")
    init.add_argument("--read-local-templates", action="store_true")
    init.add_argument("--gateway-asset-metadata-visible", action="store_true")
    init.add_argument("--upload-allowed", action="store_true")
    init.add_argument("--gateway-enabled", action="store_true")
    init.add_argument("--force-readme", action="store_true")
    init.set_defaults(func=command_init)

    health = subparsers.add_parser("healthcheck")
    health.add_argument("--workspace", required=True)
    health.set_defaults(func=command_healthcheck)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
