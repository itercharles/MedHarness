# CR Development Prompt

You are implementing an approved CR for {{project_name}}.

Inputs:
- Approved spec: `DHF/documents/specs/{{cr_id}}-Spec.md`
- DHF repo context: `AI-harness/context.md`
- Product repo checkout: `../{{product_repo_name}}/`

Task:
1. Read the approved spec and relevant repo context.
2. Implement the required DHF item changes in this repository.
3. Implement the required product code changes in `../{{product_repo_name}}/`.
4. Run or update tests as needed so the implementation is ready for review.

Requirements:
- Follow the spec unless the repository state makes a small deviation necessary.
- Preserve CR-oriented branch and PR naming using `{{cr_id}}`.
- Ensure new or changed DHF items remain schema-valid and traceable.
- Keep the DHF and product repo changes reviewable as separate PRs.

