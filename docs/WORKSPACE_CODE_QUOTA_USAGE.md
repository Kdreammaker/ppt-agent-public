# Workspace Code Quota And Usage

Date: 2026-04-23

## Current Decision

Invite beta uses workspace-code-only activation for private package access and MCP developer preview. Local-only CLI usage does not require a workspace code.

The current fixture contract supports:

- `max_activations_per_code`: 3
- `daily_call_limit`: 100
- `daily_reset`: local machine midnight
- raw workspace-code storage: disabled
- raw user identity storage: disabled
- raw machine fingerprint storage: disabled
- public CLI user list: disabled

Public CLI output may show counts, masks, hashes, remaining quota, reset time, and model/contract versions. Real user identity, raw workspace codes, issuance records, revocation records, and billing-grade audit logs belong to the private admin system only.

## Commands

Activate private beta entitlement:

```powershell
python scripts\ppt_workspace_entitlement.py activate --workspace .\ppt-workspace --workspace-code <workspace-code>
```

Check entitlement status:

```powershell
python scripts\ppt_workspace_entitlement.py status --workspace .\ppt-workspace
```

Show today's remaining private-beta call allowance and reset time:

```powershell
python scripts\ppt_workspace_entitlement.py usage --workspace .\ppt-workspace
```

Record one private feature call:

```powershell
python scripts\ppt_workspace_entitlement.py record-call --workspace .\ppt-workspace --operation build_outputs
```

The public CLI should call `record-call` only for entitlement-gated/private-beta operations. Local-only build, compose, validate, and healthcheck paths remain usable without a workspace code.

The current usage state is local preview/fixture state. It is useful for another-PC dry runs, but it is not central external-PC monitoring. Real active workspace counts, active user counts, activation quotas, daily private-call counters, revocation, rotation, and account-level audit must be owned by a future private admin/gateway service.

## First-Run Surface

`python scripts\ppt_cli_workspace.py init --workspace .\ppt-workspace --force-readme` creates `README.md` with:

- basic CLI/MCP flow
- local-only privacy defaults
- workspace-code policy
- quota policy
- model and contract versions
- support bundle policy

`python scripts\ppt_cli_workspace.py healthcheck --workspace .\ppt-workspace` writes:

- `.ppt-agent/healthcheck.json`
- `reports/healthcheck.md`

The healthcheck report now includes model and contract versions.

## Current Model And Contract Versions

- CLI: `0.1.0`
- workspace contract: `0.2.0`
- composer: `deterministic_intake_composer_v0`
- renderer: `template_slide_renderer_v0`
- MCP adapter: `thin_cli_adapter_v0`
- gateway contract: `0.2.0`
- premium recommendation: `disabled`

## Boundary

This is still invite-beta fixture behavior, not live billing or production entitlement. Before real distribution, the private admin service must own durable issuance, activation counters, daily counters, revocation, rotation, backup, restore, abuse handling, and account-level audit policy.
