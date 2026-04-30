# Troubleshooting

## Healthcheck Fails

Open `reports/healthcheck.md` in the workspace. It lists required failures and fix hints. Common issues are an unsupported Python version, missing Python packages, missing PowerShell on Windows, or a workspace folder that is not writable.

## MuPDF Structure-Tree Warnings

MuPDF may print structure-tree warnings during thumbnail or recommendation preview paths. These are currently nonblocking when the full regression gate passes and generated PPTX/HTML validation succeeds.

## Workspace Code Problems

Workspace-code statuses may be allowed, denied, expired, revoked, rotated, malformed, or missing. Local-only features should continue even when private package access is denied or unavailable.

Never paste raw workspace codes into support tickets, screenshots, chat, or Git. Use the masked code shown by the CLI.

## Gateway Unavailable

If gateway checks are unavailable, skipped by consent, denied, or out of policy, continue with local-only templates, reports, and validation. The first beta does not require the gateway for local deck generation.

## Build Or Validation Fails

Run a support bundle and inspect it locally before sharing:

```powershell
python scripts\ppt_support_bundle.py --workspace .\ppt-workspace
```

The support bundle may include bounded redacted failed-command snippets, but it should not include source documents, generated deck contents, raw references, secrets, or raw workspace codes.
