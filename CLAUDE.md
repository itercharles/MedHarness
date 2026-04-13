# CLAUDE.md

@AGENTS.md

## Specialized Agents

Three sub-agents live in `.claude/agent-memory/`. The main session acts as
orchestrator — consult agents, synthesize outputs, make decisions.

**product-manager** — scope, roadmap, business context.
**system-architect** — system design and layer boundaries.
**software-developer** — implementation patterns and conventions.

**New feature / CR:** consult product-manager + system-architect → implement.
**Bug fix:** consult software-developer → implement.
**Architectural decision:** consult system-architect + product-manager → implement.
