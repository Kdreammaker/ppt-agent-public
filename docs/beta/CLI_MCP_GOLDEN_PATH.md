# CLI And MCP Golden Path

The first beta path is local and file-based:

```powershell
ppt-agent init --workspace .\ppt-workspace
ppt-agent healthcheck --workspace .\ppt-workspace
ppt-agent plan --intake intake\example.json --ascii-blueprint
ppt-agent compose --intake intake\example.json --output specs\example.json
ppt-agent build --spec specs\example.json --pptx --html --validate
ppt-agent validate --spec specs\example.json --outputs all
ppt-agent patch --spec specs\example.json --slide 3 --slot title --value "Updated title"
ppt-agent history --workspace .\ppt-workspace
ppt-agent rollback --workspace .\ppt-workspace --run-id <run-id>
```

Assistant Mode shows the ASCII structure blueprint by default and should wait for an explicit approve, revise, continue, or skip decision before final PPTX/HTML generation. Auto Mode skips the blueprint checkpoint by default unless a workflow explicitly requests it. The ASCII blueprint is not a visual preview; use HTML/PPTX preview or rendered thumbnails for visual approval.

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
