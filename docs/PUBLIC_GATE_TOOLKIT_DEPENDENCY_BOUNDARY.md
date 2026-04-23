# Public Gate Toolkit Dependency Boundary

The private PPT system depends on the public asset contribution gate as an external toolkit, not as a content store and not as a default upload path.

Public gate:

- `https://github.com/Kdreammaker/ai-asset-contribution-gate`
- observed default branch: `main`
- observed license: `Apache-2.0`
- observed commit pin on 2026-04-23: `57de80b808bd9cc28216a9e0b6f12058a666e227`

## Dependency Decision

Use a tagged release or pinned commit as the default private dependency mode. If a release tag is available, prefer the tag and record the tag's commit SHA. If a tag is not available, use a full commit SHA. Do not use an unpinned clone.

Submodule and vendored copies are not the default. A submodule makes private checkout and public repo state too easy to confuse, and a vendored copy increases stale-tooling risk. Manual reviewed sync exports are allowed only as a fallback when a specific public-safe toolkit snapshot must be copied into a private release workspace.

## Allowed Public Gate Surface

Private automation may call or mirror only public-safe toolkit surfaces:

- schemas;
- validators;
- fixture format;
- CLI/script entrypoints;
- public-safe smoke checks;
- license notice.

## Private-Only Surface

These never move to the public gate:

- private reference analysis outputs;
- private assetization results;
- binary assets;
- registry activation data;
- workspace manifests;
- secrets and tokens;
- Drive linkage;
- work logs;
- local absolute paths;
- raw workspace codes.

## Update And Rollback

Every update records a version pin, review decision, validation result, and previous known-good pin. Rollback means returning to the previous known-good tag or commit SHA and rerunning the public-safe smoke plus private boundary validators.

The public gate must not become telemetry, default upload, private asset materialization, or private reference migration infrastructure. It is a contribution intake and safety-review toolkit only.
