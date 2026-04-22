# CR Analysis Prompt

You are working in the DHF repository for {{project_name}}.

Inputs:
- CR item: `DHF/items/{{cr_id}}.yaml`
- Product repo: `{{product_repo}}`
- Shared context: `AI-harness/context.md`

Task:
1. Read the CR and repository context.
2. Produce a technical implementation spec at `DHF/documents/specs/{{cr_id}}-Spec.md`.
3. Do not modify other files in this step.

The spec must cover:
- Problem summary and intended outcome
- Technical approach
- DHF items to create or update
- Product code changes expected
- Verification and test cases
- Compliance and traceability implications

Keep the spec concrete enough that a follow-up implementation agent can execute it directly.

