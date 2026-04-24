# Public/Private Runtime Connector

The public repository is the installable CLI control plane. Its job is not to contain the product's private template library or design intelligence. Its job is to install the public dependencies, initialize a workspace, activate entitlement, connect to the private runtime, and call the private build entrypoint that produces production-quality PPT outputs.

## Product Shape

Public repo responsibilities:

- install Python runtime dependencies;
- initialize a local workspace and consent files;
- run healthcheck and public-safe smoke builds;
- activate or inspect workspace-code entitlement with masked/hash-only state;
- configure private package repository or gateway connectivity;
- install or update the private runtime package into a workspace-controlled path;
- invoke the private CLI build command for full template-library based PPT generation.

Private repo or gateway responsibilities:

- own full template-library based high-quality PPT generation;
- own private template binaries, private Design DNA, and premium assets;
- own real user/device activation counters, daily quota, revocation, rotation, and audit;
- issue signed private package or gateway responses;
- enforce product/legal approval before distribution.

## CLI Flow

Public-safe smoke remains available, but it is only a fallback and installation check:

```powershell
python scripts\ppt_cli_workspace.py init --workspace outputs\public_smoke_workspace --force-readme
python scripts\ppt_cli_workspace.py healthcheck --workspace outputs\public_smoke_workspace
python scripts\build_deck.py data\specs\public_smoke_blank_spec.json
```

The intended useful path is private runtime generation:

```powershell
python scripts\ppt_workspace_entitlement.py activate --workspace outputs\public_smoke_workspace --workspace-code <workspace-code>
python scripts\ppt_private_connector.py configure --workspace outputs\public_smoke_workspace --enable --private-package-repo-env PPT_AGENT_PRIVATE_PACKAGE_REPO --private-build-command-env PPT_AGENT_PRIVATE_BUILD_COMMAND_JSON
python scripts\ppt_private_connector.py status --workspace outputs\public_smoke_workspace --github-check
python scripts\ppt_private_connector.py install --workspace outputs\public_smoke_workspace
python scripts\ppt_private_connector.py build --workspace outputs\public_smoke_workspace --spec data\specs\business_growth_review_spec.json --operating-mode assistant --execute
```

`PPT_AGENT_PRIVATE_BUILD_COMMAND_JSON` must be a JSON array command supplied by the private package or operator, for example:

```json
["python", "-m", "ppt_private_runtime", "build", "--workspace", "{workspace}", "--spec", "{spec}", "--output", "{output}", "--html-output", "{html_output}", "--request-summary", "{request_summary}", "--operating-mode", "{operating_mode}"]
```

Supported placeholders are `{workspace}`, `{spec}`, `{output}`, `{html_output}`, `{request_summary}`, `{capability}`, and `{operating_mode}`.

`--operating-mode auto` and `--operating-mode assistant` both use the existing private template-library build capability. The public connector only records the requested mode and approval expectation. Auto Mode is nonblocking by default and should record assumptions/review evidence. Assistant Mode carries the explicit approve, revise, continue, or skip expectation when review is requested before final generation or unattended delivery.

## Boundary

The connector writes local request summaries under `.ppt-agent/gateway_requests/`. It can install a private package into `.ppt-agent/private_runtime/` when entitlement and private repository access are configured. It can execute a private build command when that command is supplied by the private runtime package or the operator.

It must not:

- print or commit GitHub tokens, gateway tokens, or raw workspace codes;
- upload source files, local images, generated PPTX, generated HTML, or full deck contents by default;
- put private template binaries or private Design DNA in the public repo;
- pretend the public smoke deck is equivalent to private high-quality generation;
- make MCP the required production path.

This keeps the public repository useful as the CLI installer and control surface while keeping the proprietary generation engine private.
