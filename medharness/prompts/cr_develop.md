# CR Implementation Task

You are implementing an approved CR for WebTPS.

CR ID: {{cr_id}}

## Inputs

- Approved spec: `docs/cr-specs/{{cr_id}}-Spec.md`
- Repository context: `CLAUDE.md`, `README.md`, and `docs/cr_spec_workflow.md`

## Steps

1. Read the approved spec, the CR item at `DHF/items/09_cr/{{cr_id}}.yaml`,
   and the repository context files above.

2. Implement all changes required by the spec:
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

6. The implementation must be reviewable: keep changes focused on what the spec
   describes, with no unrelated refactoring or speculative additions.
