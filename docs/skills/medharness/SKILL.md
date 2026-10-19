---
description: Work on a change to this product's Design History File (DHF) with MedHarness. Use when asked to open, design, build or check a change request, or to change what the product does.
---

This repository keeps its Design History File in `DHF/`, checked by MedHarness. A change to what the
product does is not finished until its DHF is.

## Steps

1. **Start a change:** `medharness item create --type CR --data '{"title": "…", "description": "…"}'`.
2. **Design it:** run `medharness build plan --cr CR-NNN --prompt` and do what it says.
3. **Check it:** `medharness verify dhf`, and fix what it reports.
4. **Build it:** run `medharness build code --cr CR-NNN --prompt` and do what it says.
5. **Check it again**, and fix what each reports:
   - `medharness verify changes --cr CR-NNN`
   - `medharness verify completion --cr CR-NNN --junit <results>`

## Rules

- Read and write the DHF with `medharness item list|get|create|update|transition`, never by editing
  the files under `DHF/`: the commands check the schema, allocate IDs and change only the fields given.
- A long value (a CR's `impact_analysis`) is easier to write to a file and pass as `--data @fields.json`
  than to quote inline; `--data -` reads standard input.
- A failing check names the item and field that are wrong. Fix that, then run the check again; do not
  describe a check as passing before it has.
- Moving a CR between states (`item transition`) is the project's call: do it only when asked.
