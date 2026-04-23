# Private PowerShell To Public Gate Sync Path

B84 defines a dry-run-first path for preparing public-safe candidate metadata for `https://github.com/Kdreammaker/ai-asset-contribution-gate`.

No tracked PowerShell entrypoints existed before B84 in this repository. The new public-safe entrypoint is:

```powershell
pwsh -File scripts/Prepare-PublicGateSync.ps1 -Manifest config/public_gate_sync_manifest_fixture.json
```

The script writes `outputs/reports/public_gate_sync_dry_run.json` and does not write to the public repository. It does not read, print, copy, or commit tokens.

## Manifest Shape

The sync manifest contains only:

- schema and manifest ID;
- source-boundary booleans proving private material is excluded;
- public gate target metadata;
- public-safe candidate metadata;
- operator approval metadata.

Candidate metadata is limited to candidate ID, asset type, title, description, declared license, hash-only source summary, AI-generation disclosure, and safety-review status.

## Exclusions

The sync path excludes raw references, binary assets, registry exports, local absolute paths, Drive linkage, work logs, workspace manifests, tokens, secrets, and raw workspace codes.

## Approval

Public repo writes are disabled by default. A later private runner may require an explicit operator approval record before opening a public PR, but this repository only creates the dry-run review artifact. The approval switch on the PowerShell script does not perform public writes; it only verifies that the manifest has recorded approval.
