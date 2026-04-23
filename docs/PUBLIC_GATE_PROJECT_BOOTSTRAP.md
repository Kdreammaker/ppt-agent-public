# Project Bootstrap For Public Gate Integration

This bootstrap connects a new local project workspace to the clean public CLI/package path and the public asset contribution gate without requiring private gateway access.

## Flow

1. Start from the clean public-thin repo seed or a clean release export.
2. Initialize a local workspace.
3. Run workspace healthcheck.
4. Validate the public asset contribution gate dependency pin and boundary.
5. Run the public-safe sync manifest fixture smoke.
6. Build the public-thin blank smoke deck from `data/specs/public_smoke_blank_spec.json`.
7. Keep private assetization, private registry activation, reference analysis outputs, binary assets, Drive linkage, work logs, and workspace manifests outside the public gate.

## Command

```powershell
python scripts/bootstrap_public_gate_workspace.py --workspace outputs/bootstrap_smoke_workspace --force-readme
```

The script runs:

- `python scripts/ppt_cli_workspace.py init --workspace <workspace>`;
- `python scripts/ppt_cli_workspace.py healthcheck --workspace <workspace>`;
- `python scripts/validate_public_gate_toolkit_dependency.py`;
- `python scripts/validate_public_gate_sync_path.py`.

It writes a local report to `outputs/reports/public_gate_bootstrap_validation.json` and a workspace copy to `reports/public_gate_bootstrap.json`.

## CLI And MCP

The CLI remains the canonical path. MCP developer-preview users should use the same workspace files and the same CLI/package APIs through the thin adapter. The bootstrap does not introduce a separate MCP renderer, composer, gateway client, or standalone `.exe`.

## Private Gateway

Private entitlement, private package retrieval, private assetization, or premium recommendation may be added later only after explicit operator approval and separate private gateway configuration. Local-only init, healthcheck, public gate validation, and sample fixture smoke do not require the private gateway.

## Public PPT Smoke

The public-thin clean export includes a source-free deck spec that can build without private template binaries:

```powershell
python scripts/build_deck.py data/specs/public_smoke_blank_spec.json
```

Expected output:

```text
outputs/decks/public_thin_smoke.pptx
```
