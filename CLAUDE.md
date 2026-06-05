# CLAUDE.md — gem2-vision

**Version:** v15.0.0 | **Initialized:** 2026-06-05

---

## Git Commit Convention
```bash
git commit -m "{Detailed message}

Date: $(date +"%Y-%m-%d %H:%M:%S %Z")
Author: David Seo of GEM².AI"
```

---
## CANNONICAL DIRECTIVE, YOU MUST OBEY ##
**No ad-hoc execution. NEVER jump into implementation without triggering the matching skill first.**

---

## Session Protocol

Trigger `/init-session` on every session start. The skill handles all bootstrap logic.

On memory drift or context compaction → `gem2_session_context(role="ARCHITECT", project_slug="gem2-vision")` — MANDATORY when gem2-studio MCP is reachable.

---

## Skill Trigger Pattern

On user request, match the situation to a skill and trigger it. **No ad-hoc execution. NEVER jump into implementation without triggering the matching skill first.**

| Situation | Skill |
|-----------|-------|
| Session start, context compaction, "where was I?" | `/init-session` |
| Want status, counters, what's pending | `/check-session` |
| "Have we done something like this?", search prior art | `/search-kg` |
| "What skills do we have?", discover installed domain skills | `/search-skill` |
| Sweep non-core skills to archive, or restore a specific skill | `/skill-to-kg` |
| New work request, decomposition needed | `/plan-work` |
| Ready to execute a planned unit-work | `/proceed-work` |
| Need to add, modify, abort, or reorder units in a live WP | `/update-work-plan` |
| All units done, need acceptance gate | `/verify-work` |
| Want external epistemic verification (L2) | `/verify-by-gem2` |
| Verified work ready to finalize + commit | `/archive-work` |
| Extract proven WP as reusable TPMN skill | `/extract-skill` |
| Done for now, save state for next session | `/end-session` |

### Mandatory Execution Rule

**ALL implementation work MUST flow through `/proceed-work`.** No exceptions.

- Writing code → `/proceed-work` (executes a unit-work from a WP)
- Writing files → `/proceed-work`
- Any task that changes the codebase → `/proceed-work`

If no WP exists for the work → `/plan-work` first, then `/proceed-work`.

**NEVER** start writing code, creating files, or modifying the codebase without first:
1. Having a WP with a PENDING unit-work that covers the task
2. Triggering `/proceed-work` to get human permission
3. Receiving human approval before execution begins

Every work cycle MUST produce a git commit. No silent work.

---

## Communication

Inter-session communication via `gem2_msg_create`. No filesystem. No ad-hoc text.

- `from_role` = `'ARCHITECT'`
- `project_slug` = `'gem2-vision'` (ALWAYS SET on every gem2-studio MCP call)
- Broadcasts: `to_role = 'BROADCAST'` (status reports, work completion)
- Questions: `to_role = 'HUMAN'` (decisions, clarifications)
- Decisions: `gem2_decision_create` for architectural choices

---

## Project Context

Project identity and references live in:
```
.claude/skills/gem2-vision/  (project skill)
```

Current task state, progress, and recent work live in:
```
.gem-squared/alarm.md  (mutable)
```

Work plans live in:
```
.gem-squared/work-plan/  (WP files)
```

CLAUDE.md contains behavioral rules only. It does NOT contain architecture data.

---

## Core Invariants

- **gem2-studio MCP** is the DEFAULT execution layer — task tracking, session recovery, semantic search, broadcasts
- **L0 fallback** (git + `.gem-squared/`) activates ONLY when gem2-studio MCP is unreachable
- Every work cycle MUST produce a git commit
- `gem2_task_create` BEFORE every work begins — no silent work
- `gem2_msg_create` for all inter-session communication
- `gem2_session_context` on every context recovery
- `project_slug` is set on EVERY gem2-studio MCP call

---

## L0 Fallback (gem2-studio MCP unreachable)

When gem2-studio MCP is not available, all skills degrade to L0 mode:
- Task IDs are local uuid8 (no remote registration)
- No semantic search (tag-based filesystem search only)
- No broadcasts or inter-session messages
- No session recovery from gem2-studio
- Git + `.gem-squared/` files are the sole state store
- All core workflows remain functional — L0 is complete, not broken

---

## TPMN Quick Reference

Full standard: `.claude/TPMN-SKILL-STANDARD.md`.

**Types:** `𝕊` string | `ℕ` natural | `ℝ` real | `𝔹` boolean | `Seq(T)` sequence | `Path` filepath | `T?` optional
**Values:** `⊤` true | `⊥` null/absent | `{a,b,c}` enum
**Logic:** `∧` and | `∨` or | `¬` not | `∈` element of | `≜` defined as
**Epistemic:** `⊢` grounded | `⊨` inferred | `⊬` extrapolated | `⊥` unknown
**Contract:** `A` input state | `B` output state | `F` transform | `P` preconditions | `¬B` negative contract

**Core rule:** UNIT-SKILL = `STATE A → F(A) → STATE B`. B is STATE, never action. Skill produces B and STOPS.

---


## GEM^2 Output Protocol

**MANDATORY:** Every substantive AI response MUST be wrapped in `<GEM^2_MSG>` tags. This is how gem2-studio captures and persists your output. Responses without these tags are invisible to the platform.

### When to emit `<GEM^2_MSG>`

- After completing any task, analysis, or implementation step
- When answering a question or providing information
- When reporting status, progress, or errors
- **Exception:** Pure tool calls with no textual output do not need tags

### Format

```
<GEM^2_MSG>
GEM2_MSG:=
{
  "type": "GEM^2_msg",
  "from": "ARCHITECT",
  "to": "HUMAN",
  "project_slug": "gem2-vision",
  "terminal_id": "undefined",
  "terminal_title": "undefined",
  "message": "Summary (1-2 sentences)",
  "metadata": {
    "source": "AI",
    "timestamp": "<ISO8601 UTC>",
    "local_time": "<YYYY-MM-DD HH:MM:SS TZ>",
    "EEF": {
      "extrapolation": false,
      "confidence": "HIGH",
      "rules": { "GND": "PASS", "EXT": "PASS", "UNC": "N/A", "SPT": "PASS" },
      "spt_violations": null,
      "traits": {},
      "ambiguity": null
    }
  }
}
=:GEM2_MSG

(Your detailed response content here — markdown, code blocks, explanations, etc.)

</GEM^2_MSG>
```

### Rules

1. **ALWAYS** wrap your final response in `<GEM^2_MSG>...</GEM^2_MSG>` tags
2. The JSON envelope between `GEM2_MSG:=` and `=:GEM2_MSG` is the structured header
3. `"message"` field = 1-2 sentence summary of what this response contains
4. `"from"` field = your role (usually `"ARCHITECT"`)
5. `"confidence"` = `"HIGH"` when all claims are grounded, `"MEDIUM"` when some inference, `"LOW"` when uncertain
6. Content after `=:GEM2_MSG` is your actual response (free-form markdown)
7. **ONE** `<GEM^2_MSG>` block per response — do not split into multiple blocks
8. Get timestamps via: `date -u +"%Y-%m-%dT%H:%M:%SZ"` (UTC) and `date +"%Y-%m-%d %H:%M:%S %Z"` (local)


*CLAUDE.md v15.0.0 | GEM² Project Template | gem2-vision*
