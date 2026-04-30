# PPT Agent Skill

Use this skill when a user asks the local PPT agent to create, validate, or connect a deck workflow from a design guide packet.

## Operating Modes

- Assistant mode is the default. It creates `deck-plan.json`, `draft_design_brief.md`, `guide-data.public.json`, `renderer-contract.json`, `asset-slot-plan.json`, and `qa-plan.json`, then waits with `status=waiting_for_approval`. Final PPTX/HTML generation requires an explicit approved continuation such as `--build-approved`, `--continue-build`, or MCP `build_approved=true`.
- Auto mode must generate two distinct PPTX variants, `variant-comparison-report.json`, `auto-mode-recommendation.md`, and QA for both variants.
- On the first interactive deck-making request, offer Assistant mode or Auto mode. In non-interactive use, honor `--mode assistant` or `--mode auto`; otherwise default to Assistant mode.

## Route Matrix

| Route | Assistant Mode | Auto Mode |
| --- | --- | --- |
| `scripts\ppt_make.py` | Natural-language first-run wrapper; planning/checkpoint only until `--build-approved` or `--continue-build`. | Natural-language fast draft route; builds immediately. |
| `scripts\ppt_agent.py` | Guide-packet/sparse-prompt route; planning/checkpoint only until `--build-approved`. | Builds two strategy-routed variants. |
| `scripts\ppt_agent_mcp_adapter.py` | `deck_plan_compose` plans unless `build_approved=true`. | `two_variant_auto_build` renders variants. |

## Sparse Request Intake

For vague requests such as `파일인데 참고해서 만들어줘`, `ㅇㅇ 내용 찾아서 만들어줘`, `이 제품 소개자료 자동으로 만들어줘`, public institution reports, portfolios, IR pitches, or product-sector introductions, create machine-facing artifacts before slide generation:

- `request-intake.json`: bounded public-safe request excerpt, locale, source references, requested action, constraints, missing constraints, assumptions, and mode evidence.
- `source-summary.json`: bounded summaries for supplied files, URLs, search topics, and pasted material. Unreadable sources become blockers or assumptions.
- `intent-profile.json`: deck family, sector subtype, audience, objective, tone, density, confidence, evidence, assumptions, and clarification needs.
- `routing-report.json`: registry-bounded A/B strategy pair, rejected candidates, confidence, evidence, assumptions, and fallback status.

Use deterministic keyword/entity matching first. Optional AI nearest-label matching must stay inside `config/deck_intent_taxonomy.json` and return candidates plus evidence only.

## Guide Packet Rule

guide-data.public.json is the primary machine input. It must validate against `config/ppt-maker-design-guide-packet.schema.json` before PPTX generation.

When no approved guide packet is supplied, compose `guide-data.public.json` from the intent profile and strategy routing artifacts. Keep visible slide content separate from guidance, router metadata, and source evidence.

## HTML Guide Rule

HTML guide output is human review evidence only. Do not insert an HTML guide screenshot into PPTX content. Auto mode may skip HTML guide generation unless review is explicitly requested.

## Commands

```powershell
python scripts\ppt_make.py "Create a 5-slide deck about a library pilot" --mode assistant
python scripts\ppt_make.py "Create a 5-slide deck about a library pilot" --mode assistant --build-approved
python scripts\ppt_agent.py make --mode assistant --guide-bundle <bundle>
python scripts\ppt_agent.py make --mode assistant --guide-bundle <bundle> --build-approved
python scripts\ppt_agent.py make --mode auto --guide-bundle <bundle>
python scripts\ppt_agent.py make --mode assistant --prompt "파일인데 참고해서 공공기관 보고자료로 만들어줘" --source ".\input\memo.md"
python scripts\ppt_agent.py make --mode auto --prompt "ㅇㅇ 내용 찾아서 만들어줘" --search-topic "B2B SaaS market"
python scripts\ppt_agent.py make --mode auto --prompt "이 제품 소개자료 자동으로 만들어줘"
python scripts\ppt_agent.py validate-guide <bundle-or-guide-json>
python scripts\ppt_agent.py install-host codex --workspace "<workspace>"
python scripts\ppt_agent_mcp_adapter.py --serve
```

## Privacy

Generated reports should use workspace-relative paths where possible and must not include raw private paths, Drive IDs, tokens, or source attachment paths.
Do not send full local files, raw source payloads, private paths, Drive IDs, or tokens to remote advisors by default.
