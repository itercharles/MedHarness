# CR Spec Review (Soft)

You are reviewing the CR spec that was just generated for CR {{cr_id}}.

Front-matter schema (cr_id, direction_fit value, affected_items IDs, test_plan
keys) has already been verified mechanically by the harness before this review
runs. Your job is the things a script cannot judge: content quality, internal
consistency, and actionability.

## Inputs

- CR item: `DHF/items/09_cr/{{cr_id}}.yaml`
- Generated spec: `docs/cr-specs/{{cr_id}}-Spec.md`

## Review Steps

1. Read the CR item and the generated spec.

2. Judge:
   - **No placeholders** — any TBD, TODO, or blank sections? A spec with
     unresolved gaps should not proceed to design.
   - **Scope consistency** — does `direction_fit` match what the CR actually
     asks for? A CR that adds a net-new capability should be `scope-expansion`;
     one that fits the current roadmap as-stated should be `in-scope`.
   - **Narrative vs. front-matter** — are the `affected_items` consistent with
     the DHF Impact section? Items mentioned in the narrative but absent from
     `affected_items` are a gap worth flagging.
   - **Implementation Plan actionability** — is the plan specific enough for
     the design agent to act on? Vague steps like "update the UI" or
     "adjust the service" without naming the component are a flaw.
   - **DHF Impact completeness** — for each impact area (Product, Requirements,
     Architecture, Risk, SOUP, Test), does the assessment reach a clear
     conclusion? "Follow-up needed" is acceptable only when a concrete question
     is stated.
   - **Open Questions quality** — are these genuine blockers for design, or
     observations that can be deferred? Keep only questions whose answer would
     change what is designed; remove noise.

3. Do not re-verify front-matter schema, direction_fit validity, or
   affected_items IDs — those are checked deterministically. If you spot a
   mechanical issue that the harness should have caught, flag it as a harness
   bug, not a spec issue.

## Output

Write the review to `docs/cr-specs/{{cr_id}}-Spec-Review.md`:

```markdown
# Spec Review: {{cr_id}}

**Verdict:** Approved | Needs Revision

## Summary
<one paragraph>

## Issues
- [ ] <section>: <what is wrong and what fix is needed>
```

If no issues are found, write `No issues found.` under Issues.

Do not modify the spec file — this is a review pass only.
