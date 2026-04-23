# Security And Permission Policy

This policy separates public contribution, private assetization, entitlement, support, and delivery permissions. The default product mode remains local-only: no default telemetry, no default upload, no production gateway, and no public distribution without explicit human approval.

## Public Boundary

Public repositories may contain public CLI contracts, the thin MCP adapter, public-safe samples, local workspace init and healthcheck, public gate smoke fixtures, and public-safe docs. Forbidden public material includes tokens, secrets, GitHub Actions secrets, Drive links or permission records, Slack evidence or credentials, raw workspace codes, workspace manifests, work logs, reference analysis outputs, private assetization results, binary assets, registry activation data, support bundles, and local absolute paths.

The public asset contribution gate is for metadata-only candidate intake, schema validation, safety review, and CLI/script smoke. It is not a content store, telemetry endpoint, private asset migration path, or production registry. Public gate writes are disabled by default and require explicit operator approval before a later private runner may open a public PR.

## Private Asset Transfer

References analysis, private assetization, registry activation, binary assets, Drive linkage, and workspace manifests stay in private repositories or private workspaces. Any workspace-to-workspace asset transfer must use a manifest, record operator approval, and follow the source workspace policy. Private asset transfer cannot target a public repository unless the material has been reclassified, rebuilt through clean export, and passed boundary validation.

Public contribution and private assetization are separated by permission, artifact, and review boundaries:

- permission boundary: operator approval is required before private assets cross into public artifacts;
- artifact boundary: public artifacts are rebuilt through clean export and validators;
- review boundary: private review evidence is not public contribution evidence.

## Tokens And Secrets

Tokens, secrets, payment credentials, gateway credentials, and raw workspace codes must not be read, printed, copied, committed, placed in support bundles, or placed in public contribution manifests. GitHub Actions secrets belong only in private workflows and must not be mirrored into public docs, logs, reports, or fixtures.

Drive sharing permission changes require explicit human confirmation. Slack delivery uses the configured bridge or connector; token ownership stays with that integration and evidence must not include token values.

## Entitlement

The entitlement model is workspace-code only for the current beta. Local state stores hash and mask only. Raw workspace codes must not appear in CLI output, reports, screenshots, support bundles, Slack messages, Git history, clean exports, or package artifacts.

Real workspace-code issuance, central user tracking, upload, telemetry, payment, production gateway activation, and premium recommendation remain disabled unless a separate private approval and credential plan exists.

## Support Bundles

Support bundles are created only by explicit user command and written locally for inspection before sharing. They may include sanitized runtime, healthcheck, entitlement mask/hash presence, validation summaries, and bounded redacted failed-command snippets. They must exclude raw workspace codes, source documents, generated deck contents, raw references, tokens, secrets, Drive credentials, Slack credentials, private docs, and local absolute paths unless redacted or hashed by policy.

## Approval Points

Explicit operator approval is required for public distribution, public gate repository writes, private asset transfer, Drive sharing permission changes, Slack delivery, production gateway activation, real workspace-code issuance service activation, telemetry or upload enablement, payment activation, and premium recommendation activation.
