# CLI And MCP Golden Path

The first beta path is local and file-based:

```powershell
python scripts\ppt_cli_workspace.py init --workspace .\ppt-workspace
python scripts\ppt_cli_workspace.py healthcheck --workspace .\ppt-workspace
python scripts\ppt_system.py blueprint .\ppt-workspace\intake\example.json --kind intake --approval-mode assistant
python scripts\ppt_system.py compose-spec .\ppt-workspace\intake\example.json --output .\ppt-workspace\specs\example.json
python scripts\ppt_system.py build-outputs .\ppt-workspace\specs\example.json --validate --report-dir .\ppt-workspace\reports --html-output .\ppt-workspace\html\example.html
python scripts\ppt_system.py patch-spec .\ppt-workspace\specs\example.json --slide 3 --text-slot title --value "Updated title" --dry-run
python scripts\ppt_cli_history.py history --workspace .\ppt-workspace
python scripts\ppt_cli_history.py rollback --workspace .\ppt-workspace --run-id <run-id>
```

Assistant Mode shows the ASCII structure blueprint by default and should wait for an explicit approve, revise, continue, skip, or `--build-approved` decision before final PPTX/HTML generation. Auto Mode skips the blueprint checkpoint by default unless a workflow explicitly requests it. The ASCII blueprint is not a visual preview; use HTML/PPTX preview or rendered thumbnails for visual approval.

## Outputs

- PPTX: editable enterprise handoff.
- HTML: browser presentation and review output.
- Reports: validation, rationale, healthcheck, support, gateway summary, and audit outputs.

## MCP

MCP remains a developer-preview companion surface. It must call the same CLI/package APIs and return compact structured results, paths, and report summaries. It must not implement a separate renderer, composer, upload path, or workspace scanner.

Expected MCP tools are high-level wrappers such as:

- `plan_blueprint`
- `compose_spec`
- `build_outputs`
- `patch_slide_slot`
- `validate_outputs`
- `summarize_project`
