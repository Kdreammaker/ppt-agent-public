# Prompt Pack Boundary

Mode prompts use a two-layer package model.

The public layer contains prompt skeletons with placeholders, stage objectives, and output contracts. It can be included in clean export because it does not contain proprietary examples, private prompt wording, private ranking logic, or raw connector payloads.

The private layer contains real prompt packs. Private execution requires a private manifest referenced by `PPT_AGENT_PRIVATE_PROMPT_PACK_MANIFEST`. Public smoke may run with skeleton IDs only and must report `public_skeleton_smoke_only` rather than pretending that real private execution is available.

Public reports may cite prompt skeleton IDs and private prompt-pack version IDs. They must never echo private prompt text.
