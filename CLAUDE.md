# CLAUDE.md

@AGENTS.md

## Specialized Agents

Three sub-agents live in `.claude/agent-memory/`. The main session acts as
orchestrator — consult agents, synthesize outputs, make decisions.

**product-manager** — scope, roadmap, business context.
**system-architect** — system design and layer boundaries.
**software-developer** — implementation patterns and conventions.

**New feature / CR:** consult product-manager + system-architect → write a plan spec → implement.
**Bug fix:** consult software-developer → implement.
**Architectural decision:** consult system-architect + product-manager → write a plan spec → implement.

### Plan Spec

Write after consulting agents, before writing code. Required for any new feature CR or
any fix touching more than one file or layer.

Must contain: (1) scope; (2) affected files by layer; (3) non-obvious design decisions;
(4) test approach; (5) explicit out-of-scope constraints.

Write inline in the session. Do not save to disk unless the user asks.
