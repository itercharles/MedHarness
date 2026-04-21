# Pre-Checklist

Read this before starting any DHF change.

- **CR exists and is `planned`** — verify with `python -m utils item list --type CR`; create one if it doesn't exist before writing anything
- **Identify affected item types** — determine which of UC, CRS, SYS, SRS, SWDD, RISK, RCM, TC need to be created or updated
- **Check existing traceability** — run `compliantflow --dhf DHF validate traceability` to see the current state before adding new links
- **Validate draft before creating** — for new items, use `compliantflow --dhf DHF validate draft <file> --type <TYPE>` to catch issues early
- **Branch from main** — include the CR ID in the branch name (e.g. `feat/CR-042-add-input-validation`)
