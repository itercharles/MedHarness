# CR Implementation Task

You are implementing a Change Request for this product.

CR ID: {{cr_id}}

## Inputs

- CR item: `DHF/items/09_cr/{{cr_id}}.yaml` — read this first for title, description,
  justification, and `affected_items` (the DHF items created or updated by the design phase)
- DHF items linked in `affected_items` — read each one for requirements and design detail
- Repository context: `CLAUDE.md`, `README.md`

## Steps

1. Read the CR item and each item listed in its `affected_items` field to understand
   what must be implemented.

2. Implement all changes required by the design:
   - Product code changes in the appropriate workspace (`apps/client/`,
     `apps/api/`, `packages/shared-types/`)
   - Tests colocated at `*.test.ts(x)` with `@links:SRS-xxx` or `@links:SYS-xxx`
     annotations for any DHF-linked requirements

3. Follow CLAUDE.md conventions:
   - TypeScript strict mode, no `any`
   - Tailwind only, no inline styles
   - Define shared types before using them
   - Write tests alongside every functional change

4. Run validation before finishing:

   ```bash
   pnpm --filter @webtps/client typecheck
   pnpm --filter @webtps/client test
   medharness --dhf DHF dhf validate schema
   ```

5. Do not modify `DHF/items/09_cr/{{cr_id}}.yaml` or any CR lifecycle fields.

6. Keep changes focused on what the CR describes — no unrelated refactoring or
   speculative additions.
