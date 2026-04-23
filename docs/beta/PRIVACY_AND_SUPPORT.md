# Privacy And Support

The invite beta defaults to local-only operation.

## Defaults

- No telemetry.
- No automatic upload.
- No public sharing.
- No learning-data collection.
- No gateway call unless explicitly enabled by policy and consent.
- No full-file upload by default.

## Gateway Boundary

The first beta gateway path is entitlement and metadata-only gateway contract validation. Real premium recommendation is disabled by default.

Metadata-only requests may include compact fields such as deck type, industry, tone, slide purposes, quality summaries, B49 lightweight DNA summaries, and asset intent summaries. They must not include full specs, generated HTML, generated PPTX binaries, local image binaries, raw references, raw workspace codes, private templates, secrets, or tokens.

Every future gateway-facing recommendation or document-intake call should show a preflight payload preview before any network call is allowed.

## Support Bundle

Support bundles are created only by explicit user command:

```powershell
ppt-agent support-bundle --workspace .\ppt-workspace
```

The bundle is written locally so the user can inspect it before sharing. It may include runtime, consent, entitlement, healthcheck, validation, gateway summary, B49, B50, clean-export, and bounded redacted failed-command snippets.

The bundle excludes raw workspace codes, local file contents, generated decks, generated HTML, images, templates, private docs, full specs, raw references, tokens, and secrets.
