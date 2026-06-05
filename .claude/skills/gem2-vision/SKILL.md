---
name: gem2-vision
description: Project identity skill for gem2-vision. Carries project slug, mandate, and references. The sole anchor for project identity in the TPMN system.
---

(* TPMN PROJECT-IDENTITY — gem2-vision *)

Project ≜ [
  slug:       "gem2-vision",
  root:       "/Users/inseokseo/GEM-Squared-Universe/gem2-vision",
  created:    "2026-06-05",
  mandate:    ⊥,                        (* TBD — surface during /plan-work *)
  references: <<
    ".claude/TPMN-SKILL-STANDARD.md",
    ".gem-squared/alarm.md",
    ".gem-squared/work-plan/"
  >>
]

(* === Identity invariants === *)
INV ≜ [
  ⊢ slug is the sole canonical project identity used across alarm.md, WPs, and MCP calls,
  ⊢ mandate must be defined before any /plan-work invocation,
  ⊢ this file is the project's identity anchor — never delete
]
