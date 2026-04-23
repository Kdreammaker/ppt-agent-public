# Public Gate And Private Boundary CI

This CI boundary keeps the public-thin smoke path small while keeping packaging, entitlement, asset catalog, and leak-scan checks in the private/local gate.

## Public CI

Public CI is `Smoke Test` in `.github/workflows/smoke-test.yml`. It should prove only public-safe behavior:

- public CLI module imports;
- public JSON fixture parsing;
- local workspace init;
- local workspace healthcheck;
- public asset contribution gate dependency validation;
- public-safe sync manifest fixture validation;
- public gate project bootstrap smoke.
- public-thin PPT build smoke using `data/specs/public_smoke_blank_spec.json`.

Public CI must not read tokens or secrets, deploy a private gateway, follow Drive links, include Slack evidence, publish private assets, upload telemetry, or write to the public gate repository. It should not depend on private reference analysis outputs, private assetization results, binary assets, workspace manifests, or work logs.

## Private And Local CI

Private/local CI owns the broader boundary checks:

- clean release export;
- beta packaging dry run;
- public/private repo split;
- asset catalog build and validation;
- workspace-code entitlement, issuance masking, and admin fixtures;
- private admin gateway activation fixture contract;
- local path hardening;
- support bundle leak scan;
- public gate dependency, sync, and bootstrap validators.
- public-thin PPT smoke against the clean export.

Failures in those checks block private release-candidate promotion and distribution review. They do not imply the public smoke path should learn private behavior.

## Release Candidate Gate

`python scripts/run_regression_gate.py` remains the local release-candidate gate. It may run heavier visual/template checks and private boundary validators. Distribution is still blocked by default until final QA and explicit human approval.

Heavy visual or rendering gates should stay private/local unless their assets, dependencies, and outputs are separately reclassified as public-safe.
