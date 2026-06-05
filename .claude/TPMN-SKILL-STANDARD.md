(* ══════════════════���════════════════════════════��════════════════════════════ *)
(* TPMN_SKILL_STANDARD v4.1 — Grammar, UNIT-SKILL Definition,               *)
(* Skill File Structure. The reusable standard for writing AI skills.        *)
(*                                                                           *)
(* Companion: TPMN-LIFECYCLE-GUIDE.md — Artifact definitions (tagging,       *)
(* work-plan, unit-contract) and reference (example, validation checklist).   *)
(*                                                                           *)
(* Replaces: TPMN_SKILL_STANDARD v4.0 (single-file, §0-§23)                *)
(* ══════════════════════════════════════════��═════════════════════════════════ *)

TPMN_SKILL_STANDARD ≜ [

(* ═══ §0 Terminology ═══ *)
(* This standard uses several related terms. This section prevents confusion. *)
Terminology ≜ [
  "TPMN Skill Standard": "Defines AI skills using algebraic logical notation (TPMN).
                           Three properties prose skills cannot guarantee:
                             typed state (A → B | P),
                             computable flow (bounded step sequence),
                             compaction safety (formal notation resists meaning dilution).
                           12 lifecycle skills that work with git alone (L0). No server required.
                           Published as @gem_squared/tpmn-skill-install (MIT).",

  (* — Standard Application layers — *)
  "L0":  "Platform agnostic — MIT license, fully local, always works. Spec + filesystem + any AI agent.
          Works with Claude Code, Codex, Gemini CLI, Cursor, or any agent that can read markdown files.
          No server, no infrastructure. Git + .gem-squared/ files. Your work has basic file-based memory across sessions.
          (* Currently optimized for Claude Code. *)",

  "L1":  "gem2-studio — MIT + Free binary, fully local. Your work has DB-memory across sessions.
          Adds task tracking, cross-session memory, cross-session messaging,
          knowledge graph, and web UI. Skills fall back to L0 when L1 is unavailable.",

  "L2":  "GEM² Epistemic Studio — cloud service. Free tier. Your work is epistemically verified.
          Truth proposed by machines (multi-provider LLM consensus), grounded by humans
          (feedback calibration loop). Used by /verify-by-gem2. Requires L0, optional
          alongside L1. Each layer is independently useful.",

  (* — Artifact Types — *)
  "SKILL":  "Reusable capability template. Permanent. Defines WHAT an AI can do via CONTRACT.
              Two scopes:
                Global: ~/.claude/skills/{name}/SKILL.md — shared across all projects.
                  The 12 TPMN lifecycle skills live here.
                Local:  {project_root}/.claude/skills/{name}/SKILL.md — project-specific.
                  Domain skills, extracted patterns, team conventions live here.",

  "WP":     "Work-Plan (.gem-squared/work-plan/WP-ST-{N}.md) — instance of planned work.
              Created by /plan-work, executed by /proceed-work, archived by /archive-work.
              Contains 1-9 unit-contracts. Mutable. Flows through lifecycle:
              PENDING → IN_PROGRESS → COMPLETED → archived.
              (* Full WP structure: see TPMN-LIFECYCLE-GUIDE.md §2 *)",

  "UC":     "Unit-Contract (unit-work within a WP) — one contracted unit of work.
              Has A → B | P (contract) + Clarity, Unclear, Tags (planning metadata) +
              Result, State, Truth (execution metadata, filled progressively).
              NOT a SKILL — a UC is an instance; a SKILL is a template.
              (* Full UC definition: see TPMN-LIFECYCLE-GUIDE.md §3 *)",

  (* — Add on infra — *)
  "gem2-studio":  "Free local dev server. L1 enhancement layer — optional.
                   Adds persistent task tracking, cross-session memory,
                   semantic search, web UI.",

  "GEM² Epistemic Studio": "Cloud epistemic verification service. L2 layer — optional.
                             Truth scoring via multi-provider LLM consensus, grounded
                             by human feedback. Used by /verify-by-gem2.
                             Proprietary — GEM².AI.",

  (* — Skill driver — *)
  "AI (e.g., Claude Code)": "Any AI agent acting on behalf of the human to read B,
               route between skills, and verify CONTRACTs. The standard is
               platform-agnostic — works with Claude Code, Codex, Gemini CLI,
               Cursor, or any agent that can read markdown files."
],

(* ╔═══════���═══════════════════════════════════════════════════════���══════════╗ *)
(* ║  PART 1 — TPMN GRAMMAR                                                 ║ *)
(* ║  Domain-agnostic meta-language for GEM² formal notation                 ║ *)
(* ╚══════════════════════════════════════════════════════════════════════════╝ *)

  (* ═══ §1 Symbol Definitions ═══ *)
  (* Complete reference for all symbols used in TPMN *)
  Symbols ��� [

    (* — Type Symbols — *)
    𝕊:  "String — text value",
    ℕ:  "Natural number — non-negative integer {0, 1, 2, ...}",
    ℤ:  "Integer — positive, negative, or zero",
    ℝ:  "Real number — continuous value. ℝ[a,b] = bounded range [a..b]",
    𝔹:  "Boolean — {⊤, ⊥} (true, false)",

    (* — Value Symbols — *)
    ⊤:  "True / satisfied / top",
    ⊥:  "Undefined / null / bottom — absence of value",

    (* — Definition — *)
    ≜:  "Defined as — binds a name to its definition (TLA+ standard)",

    (* — Logic Connectives — *)
    ∧:  "Logical AND — conjunction",
    ∨:  "Logical OR — disjunction",
    ¬:  "Logical NOT — negation",
    ⟹: "Implies — if left then right",
    ⟺: "If and only if — bidirectional implication",

    (* — Quantifiers — *)
    ∀:  "For all — universal quantifier",
    ∃:  "There exists — existential quantifier",
    ∃!: "Unique exists — exactly one element satisfies",

    (* — Set Operations — *)
    ∈:  "Element of — membership",
    ∉:  "Not element of — non-membership",
    ⊆:  "Subset of",
    ∪:  "Union",
    ∩:  "Intersection",

    (* — Collection Types — *)
    Seq:    "Seq(T) — ordered sequence of elements of type T. Maps to: JSON Array, Go []T, YAML list",
    Record: "Named field record [k₁: v₁, k₂: v₂, ...]. Maps to: JSON Object, Go struct",
    Path:   "Filesystem path (𝕊 with path semantics)",

    (* — Contract Symbols — *)
    A:  "Input state — what the skill receives",
    B:  "Output state — what the skill produces (NEVER an action or trigger)",
    F:  "Transformation function — the blackbox process A → B",
    P:  "Preconditions — constraints that must hold for F to execute",
    ¬B: "Negative contract — what B must NEVER contain, what F must NEVER do",

    (* — Epistemic Tags — *)
    ⊢:  "GROUNDED — claim from spec, input, or verifiable fact",
    ⊨:  "INFERRED — derived from ⊢ claims, derivation chain visible",
    ⊬:  "EXTRAPOLATED — beyond evidence, basis must be stated",

    (* — Structural — *)
    "<<>>":    "Sequence literal — ordered steps. <<S₁, S₂, S₃>>",
    "(*..*)":  "TPMN comment — inline explanation",
    "|x|":     "Cardinality / length — |Seq| = count of elements",
    "↦":       "Maps to — used in function mappings [x ∈ S ↦ expr]",

    (* — Type Modifiers — *)
    "T?":      "Optional — value may be ⊥ (e.g., 𝕊? means string or undefined)",
    "{a,b,c}": "Enumeration — value must be one of the listed elements"
  ],

  (* ���══ §2 TLA+ Conventions ═══ *)
  (* Base format for GEM² formal notation *)
  TLA_Conventions ≜ [
    records:       "[field: value, ...]",
    records_ex:    "Person ≜ [name: 𝕊, age: ℕ]",

    sets:          "{element, ...}",
    sets_ex:       "Status ≜ {PENDING, IN_PROGRESS, COMPLETED, BLOCKED, ABORTED}",

    sequences:     "<<element, ...>>",
    sequences_ex:  "Pipeline ≜ <<plan, design, implement, test, deploy, verify>>",

    functions:     "f(x) ≜ expr",
    functions_ex:  "clarity(units) ≜ avg([u.clarity | u ∈ units])",

    mappings:      "[x ∈ S ↦ expr]",
    mappings_ex:   "Square ≜ [x ∈ ℕ ↦ x × x]",

    conditionals:    "IF c THEN a ELSE b",
    conditionals_ex: "Max(a,b) ≜ IF a > b THEN a ELSE b"
  ],

  (* ═══ §3 Panini Adaptation ═══ *)
  (* Compact grammar for acronyms and predicate operators *)
  Panini_Adaptation ��� [
    acronym_pattern:   "NAME ≜ [Letter: \"Meaning\", ...]",
    acronym_ex:        "TPMN ≜ [T: \"TLA+\", P: \"Panini\", M: \"Math\", N: \"NL\"]",

    predicate_pattern: "Predicate(args) ≜ expression",
    predicate_ex:      "Valid(x) ≜ x ∈ Domain ∧ x ≠ ⊥",

    compact_rule:      "Minimize tokens while preserving clarity"
  ],

  (* ═══ §4 Math Notation ═══ *)
  (* The decisional layer — for programmatic decisions and formal constraints *)
  (* TLA+ provides structure (records, sequences, definitions).              *)
  (* Math notation provides the logic that fills those structures:           *)
  (* preconditions (P), predicates, invariants, STATE verification.          *)
  Math_Notation ≜ [
    purpose:        "For programmatic decisions and formal constraints.
                     TLA+ organizes; math notation decides.
                     Every P in F: A → B | P, every INV rule, every STATE verification
                     predicate (§7) is expressed in this layer",

    quantifiers:    "∀ (for all), ∃ (exists), ∃! (unique exists)",
    quantifiers_ex: "∀ x ∈ S: f(x) ≠ ⊥",

    connectives:    "∧ (and), ∨ (or), ¬ (not), ⟹ (implies), ⟺ (iff)",
    connectives_ex: "Valid(x) ⟹ ¬Empty(x)",

    sets:           "∈ (in), ∉ (not in), ⊆ (subset), ∪ (union), ∩ (intersect)",
    sets_ex:        "A ⊆ B ∧ C ∉ A",

    usage_rule:     "Prefer math notation over NL when expressing logic"
  ],

  (* ═��═ §5 Natural Language Rules ═══ *)
  (* When NL is more effective than formal notation *)
  NL_Rules ≜ [
    comments:        "(* ... *) for inline explanation",
    comments_ex:     "(* B is state — AI decides next action *)",

    descriptions:    "String values for NL meanings",
    descriptions_ex: "who: \"ARCHITECT beginning a work session\"",

    allowed_in_skills: [
      "YAML frontmatter description field (≤1024 chars)",
      "(* ... *) inline TPMN comments",
      "String literals inside records",
      "Flow step action field — operational NL"
    ],

    prohibited: {
      "markdown tables in TPMN body",
      "ASCII trees or diagrams",
      "verbose paragraphs",
      "bullet-point instruction lists",
      "numbered step lists in prose",
      "example conversations or dialogues",
      "'Use when user says...' trigger language"
    },

    usage_rule: "NL for prompts, commands, messages — NOT for definitions"
  ],

(* ╔═══════��══════════════════════════════════════════════════════════════════╗ *)
(* ║  PART 2 — UNIT-SKILL DEFINITION                                        ║ *)
(* ║  What a UNIT-SKILL is, why it exists, how it's selected                 ║ *)
(* ╚════════��════════════════════��═════════════════════════════��══════════════╝ *)

  (* ═���═ §6 Purpose ═══ *)
  Purpose ≜ [
    problem:  "Prose-based skills are ambiguous, silently fail 50-56% of the time,
               lose meaning after context compaction, and cannot be selected by AI",
    solution: "Define UNIT-SKILL as a pure state transformation written in TPMN grammar.
               AI (e.g., Claude Code) selects skills by CONTRACT, not by trigger phrases",
    outcome:  "Skills become provable, traceable, compaction-safe, AI-selectable"
  ],

  (* ═══ §7 UNIT-SKILL Core ═══ *)
  (* The foundational concept — everything else follows from this *)
  Unit_Skill ≜ [
    definition: "A UNIT-SKILL is a pure state transformation:
                 STATE A → F(A) → STATE B
                 where B is output STATE, never an action or trigger",

    A: "Input state — files, records, parameters the skill receives",
    F: "Blackbox process — read, check, reason, write. Opaque to caller",
    B: "Output state — report, record, artifact. NEVER triggers next skill",
    P: "Preconditions — constraints for F to execute",

    (* Verification predicate — how STATE is determined *)
    STATE_verification: "
      Given a = actual input, b = actual output, CONTRACT = (A, B, P):
        STATE = SUCCESS ⟺
          (∀ field ∈ B: b[field] ≠ ⊥ ∧ type(b[field]) = B[field].type)
          ∧ P(a, b) holds
        STATE = FAILURE otherwise.
      Three checks:
        1. Field coverage:  ∀ field ∈ B → b[field] ≠ ⊥
        2. Type conformance: type(b[field]) = B[field].type
        3. Constraint satisfaction: P(a, b)
      This is structural type-checking, not subjective judgment.
      AI can self-evaluate STATE against its own CONTRACT",

    core_invariant: "B is state. Not action.
                     AI reads B and decides the next skill.
                     UNIT-SKILL produces B and STOPS",

    sovereignty: "Inside F, the skill has full sovereignty.
                  Caller controls at CONTRACT edge only (A in, B out).
                  No observation, no interruption, no micro-management"
  ],

  (* ═══ §8 UNIT-SKILL Rules ═══ *)
  Rules ≜ [
    R1: "B does NOT trigger any next skill — AI is the flow handler",
    R2: "No sibling skill invocation — UNIT-SKILL produces state and stops",
    R3: "Max 5 flow steps (desire), max 9 (hard limit) — Miller's law (7±2) bounds cognitive chunking. Same principle as unit-work decomposition. Decompose into separate skills instead of extending flow",
    R4: "Query-distinguishable — title + description unique for AI selection",
    R5: "CONTRACT-clear — unambiguous F:A→B|P for AI contract-based selection",
    R6: "MANDATE BOUNDARY — scope is exactly what CONTRACT says, nothing more",
    R7: "¬B declared — explicit negative contract (what the skill NEVER does)"
  ],

  (* ═══ §9 Mandate Boundary ═══ *)
  (* The sovereignty principle *)
  Mandate_Boundary ≜ [
    definition: "Each UNIT-SKILL's scope is exactly what its CONTRACT says.
                 Nothing more. Nothing less",

    rules: [
      "⊢ UNIT-SKILL does NOT trigger sibling skills",
      "⊢ UNIT-SKILL does NOT read B of another skill to decide action",
      "⊢ UNIT-SKILL produces B and STOPS — AI handles flow",
      "⊢ ¬B declares what is explicitly OUT of scope",
      "⊢ INV includes MANDATE BOUNDARY statement"
    ],

    sovereignty: "Inside F (between A and B), the skill has full autonomy.
                  Parent/caller controls at CONTRACT edge only:
                    - Provides A (input)
                    - Receives B (output)
                    - Verifies P (preconditions)
                  No observation of internal steps. No interruption",

    violation_examples: [
      "init-session calling /init-sdlc → VIOLATION (sibling invocation)",
      "update-task redirecting to /complete-task → VIOLATION (sibling trigger)",
      "proceed-unit-test fixing implementation bugs → VIOLATION (mandate overflow)"
    ]
  ],

  (* ═══ §10 AI Selection Model ═══ *)
  (* How UNIT-SKILLs are selected — by CONTRACT structure, not by trigger matching *)
  AI_Selection ≜ [
    premise: "Skills are NOT selected by trigger matching or keyword patterns.
              AI (e.g., Claude Code) selects by CONTRACT",

    (* — L0 Selection (primary — works with any AI agent) — *)
    L0_selection: [
      principle: "AI reads skill descriptions and CONTRACTs to select",
      method:    "Selection is by CONTRACT structure: different A/B/P shapes = different skills",
      design:    "12 lifecycle skills are structurally distinct by design — selection is unambiguous",
      sufficiency: "The AI agent's native capability (reading markdown, matching intent to
                    CONTRACT) is sufficient for the core skill catalog"
    ],

    (* — L1 Enhancement (optional — gem2-studio adds a scaled pipeline) — *)
    L1_enhancement: [
      note: "gem2-studio provides a 4-phase pipeline that scales to larger catalogs
             beyond the 12 lifecycle skills",
      phases: <<
        [name: "Fuzzy Pre-Check",    method: "Trigram similarity on title + description"],
        [name: "LLM Narrow",         method: "Reduce to 3-5 candidates by title + description"],
        [name: "CONTRACT Select",    method: "Read full CONTRACTs of candidates → select best fit"],
        [name: "Execute",            method: "Validate A against P → execute Flow → return B"]
      >>
    ],

    (* What this means for SKILL.md authoring — valid at both L0 and L1: *)
    authoring_implications: [
      title:       "Must be query-distinguishable — AI narrows by title",
      description: "Must describe WHAT + WHEN concisely — AI reads to match intent",
      contract:    "Must have clear A, B, P, ¬B — AI reads full CONTRACT to select",
      B_type:      "Must be structured state — AI reads B for routing"
    ]
  ],

  (* ═══ §11 Knowledge Accumulation ═��═ *)
  (* The lifecycle closes a loop — proven work compounds across projects *)
  Knowledge_Accumulation ≜ [
    principle: "Workflows compound. Every verified work-plan (COMPLETED + SUCCESS) is a
                proven template. The lifecycle does not just execute — it learns",

    cycle: [
      "1. /archive-work stores proven contracts in archive/ (L0) and gem2-kg (L1)",
      "2. /search-kg retrieves relevant proven patterns for new work",
      "3. /plan-work invokes /search-kg + /search-skill before decomposition",
      "4. New work-plan is informed by what worked before — not starting from zero",
      "5. Cycle repeats: execute → verify → archive → search → plan"
    ],

    mechanism: [
      archive:  "/archive-work: terminal WPs → archive/. L1: contracts stored as searchable knowledge",
      search:   "/search-kg: retrieves proven patterns by tag or semantic similarity",
      plan:     "/plan-work: invokes /search-kg + /search-skill to find patterns before decomposition",
      extract:  "/extract-skill: formats proven contracts as reusable SKILL.md in .claude/skills/"
    ],

    invariant: "The 12 lifecycle skills stay fixed. The knowledge compounds.
                N projects × M work-plans = growing pattern library.
                Each new /plan-work has access to all prior proven patterns"
  ],

  (* ═══ §12 Why TPMN, Not Prose ═══ *)
  (* Concrete problems TPMN solves — grounded in measured data *)
  Prose_Problems ≜ [
    data_source: "Claude Skill community pain points research (2026-04-16)",

    problem_1: [
      name:     "50-56% silent failure rate",
      cause:    "Prose instructions are ambiguous — AI interprets differently each run",
      tpmn_fix: "CONTRACT F:A→B|P — machine-checkable input/output specification"
    ],

    problem_2: [
      name:     "73% of community skills broken",
      cause:    "No success/failure contract — skill 'runs' but produces wrong output",
      tpmn_fix: "¬B (negative contract) + INV (invariants) — explicit failure conditions"
    ],

    problem_3: [
      name:     "Context compaction loses meaning",
      cause:    "Prose instructions get summarized during context compaction — conditions,
                 edge cases, and constraints are silently dropped",
      tpmn_fix: "Formal notation resists meaning dilution (§13) — P ≜ x ≠ ⊥ ∧ y ≠ ⊥
                 cannot be summarized without visibly breaking the formula"
    ],

    problem_4: [
      name:     "Trigger collision across skills",
      cause:    "Prose descriptions overlap — 'Use when user says...' matches multiple",
      tpmn_fix: "AI (e.g., Claude Code) selects by CONTRACT (not trigger) — §10"
    ]
  ],

  (* ��══ §13 Compaction Safety ═══ *)
  Compaction_Safety ≜ [
    principle: "TPMN resists meaning dilution under context compaction.
                Prose gets summarized — summaries lose nuance, conditions, edge cases.
                Formal notation cannot be lossy-compressed without breaking syntax",

    why_safe: [
      panini:  "Structured grammar (§1) — field names and nesting survive compaction intact",
      tla:     "Logic operators (§2) — ∧, ∨, ¬, ∈ are atomic; removing one changes truth value",
      math:    "Type signatures (§4) — 𝕊, ℕ, 𝔹, Seq(T) are incompressible single tokens",
      contract: "A → B | P (§7) — the three-part structure is the minimum unit of meaning.
                 Summarizing 'A: input state' into prose destroys the typed constraint"
    ],

    contrast: [
      prose_risk:   "AI compaction of 'When the user wants to plan work and there are
                     preconditions that must hold...' → 'Plans work' — conditions lost",
      tpmn_safety:  "P ≜ work ≠ ⊥ ∧ project_slug ≠ ⊥ — cannot be summarized further
                     without removing a conjunct, which visibly breaks the formula"
    ],

    practical_rule: "Move reference material to references/ subdirectory, NOT into SKILL.md body.
                     The SKILL.md body should contain only formal notation — the part that
                     survives compaction. Prose context goes in references/ where it can be
                     re-read on demand"
  ],

  (* ═══ §14 Epistemic Tags ══�� *)
  Epistemic_Tags ≜ [
    rule: "Claims in SKILL.md body use epistemic tag prefixes",

    ⊢: "GROUNDED — from spec, input, or verifiable fact",
    ⊨: "INFERRED — derived from ⊢ claims, derivation chain visible",
    ⊬: "EXTRAPOLATED — beyond evidence, basis must be stated",

    usage: "INV and ¬B entries use ⊢ prefix (grounded constraints).
            Flow action descriptions are NL (operational, not epistemic claims)"
  ],

(* ╔══════════════════════════════════════════════════════════════════════════╗ *)
(* ║  PART 3 — SKILL FILE STRUCTURE & NOTATION                              ║ *)
(* ║  How to write a UNIT-SKILL file                                         ║ *)
(* ╚══════���═══════���════════════════════════════════════���══════════════════════╝ *)

  (* ═══ §15 Skill File Structure ��══ *)
  (* This section guides writing LOCAL project skills: {project_root}/.claude/skills/{name}/SKILL.md *)
  (* The 12 TPMN lifecycle skills live in GLOBAL: ~/.claude/skills/ — do not modify them.            *)
  (* Local skills compose WITH the 12 core skills, not replace them.                                  *)
  (* For WP/UC structure, see TPMN-LIFECYCLE-GUIDE.md §2 and §3.                                     *)
  Skill_File_Structure ≜ [
    scope:     "Local project skills — {project_root}/.claude/skills/{name}/SKILL.md",
    core_ref:  "12 TPMN lifecycle skills — ~/.claude/skills/{init-session..end-session}/SKILL.md (global, do not modify)",
    frontmatter: "Standard YAML (name, description, argument-hint, metadata, allowed-tools)",
    body:        "TPMN grammar — 7 mandatory sections + 2 optional sections",
    mandatory:   "Layers, Input (A), Output (B), Precondition (P), Transform (F), Constraint, Invariant (INV)",
    optional:    "Pre-Execution Dialog (Ask_Human), Post-Execution Routing",

    skeleton: "
---
name: {kebab-case, ≤64 chars}
description: >
  (Who) {executor — AI, sub-agent, or human}.
  (What) {state transformation — the deliverable}.
  (When) {condition — what triggers selection}.
  (Where) {location — execution environment, output path, deploy target}.
  (Why) {rationale — why this exists as a separate skill}.
  (* ≤1024 chars. 5W grounding (§17). Written for AI contract-based selection. *)
argument-hint: \"{parameter hints}\"  (* optional — omit if skill takes no arguments *)
metadata:
  author: {author}
  version: {semver}  (* use -draft suffix for unreleased: e.g. 12.0.0-draft *)
allowed-tools:
  - {tool_1}
  - {tool_2}
---

(* TPMN SKILL — {name} *)

(* === Layers === *)
L0 ≜ \"{minimal capability — what works with filesystem + git alone}\"
L1 ≜ \"{enhanced capability — what gem2-studio MCP adds (optional)}\"

(* === Input === *)
A ≜ [
  {field_1}: {Type},                   (* description *)
  {field_2}: {Type}?                   (* optional field *)
]

(* === Output === *)
B ≜ [
  {field_1}: {Type},                   (* state, not action *)
  {field_2}: {Type}
]

(* === Precondition === *)
P ≜ {predicate_1}
    ∧ {predicate_2}

(* === Transform === *)
F ≜ <<
  1. {Step description}:
       {Action details. Reference L0/L1 where behavior differs.}
  2. {Step description}:
       {Action details.}
  (* N steps, N ≤ 9, desire N ≤ 5 *)
>>

(* === Constraint === *)
CONSTRAINT ≜ [
  ⊢ NEVER {what this skill must never do — mandate boundary},
  ⊢ NEVER {boundary violation with sister skill},
  ⊢ {positive constraint}
]

(* === Invariant === *)
INV ≜ [
  ⊢ {structural truth that always holds},
  ⊢ {another invariant},
  ⊢ MANDATE BOUNDARY: {what is in scope} — {what is NOT in scope}
]

(* === Pre-Execution Dialog === *)  (* optional — omit if no human input needed *)
Ask_Human ≜ <<
  [field: \"{field_name}\",
   prompt: \"{question to ask}\",
   required: ⊤|⊥]
>>

(* === Post-Execution Routing === *)
Routing ≜ [
  {condition_1} → {next skill},
  {condition_2} → {next skill or action}
]
    "
  ],

  (* ═══ §16 Contract Notation ═══ *)
  Contract_Notation ≜ [
    pattern:    "F: A → B | P",
    definition: "Function F transforms input state A to output state B under preconditions P",

    F:  "Skill name (PascalCase in contract, kebab-case in YAML)",
    A:  "Input state — TLA+ record. Fields typed with symbols from §1",
    B:  "Output state — TLA+ record. MUST be state, NEVER action",
    P:  "Preconditions — predicate conjunction (∧). Checked before F executes",
    ¬B: "Negative contract — what B must NEVER contain, what F must NEVER do.
         Declares mandate boundary explicitly. Uses ⊢ prefix for each rule",

    example: "
      Start_Task: A → B | P ≜ [
        A: [title: 𝕊,
            mode: {feature, bug},
            priority: {CRITICAL, HIGH, MEDIUM, LOW}?],
        B: [task_id: 𝕊,
            wp_path: Path,
            alarm_updated: 𝔹],
        P: title ≠ ⊥ ∧ project_slug ≠ ⊥
      ]

      ¬B ≜ [
        ⊢ NEVER start implementation — creation only,
        ⊢ NEVER resume existing tasks — /resume-task's mandate
      ]
    "
  ],

  (* ��══ §17 Grounding 5W ═══ *)
  (* Why 5W, not Claude's default (what/when)? *)
  Grounding_5W ≜ [
    problem: "Claude Code's default skill description guidance suggests (what) and (when).
              Two fields are insufficient — AI drifts without explicit guardrails:
                - WHO missing → AI guesses who owns the UC (self, sub-agent, human).
                  Guessing = wrong auto-proceed vs wrong pause
                - WHERE missing → AI guesses where A comes from, where B goes to.
                  Guessing = wrong input source, wrong output destination
                - WHY missing → AI guesses which skill to select when two share similar what/when.
                  Guessing = trigger-collision (§12 problem_4)
              5W guardrails AI to explicitly know ownership, location, and purpose
              before proceeding. No guessing. No drifting",

    solution: "5W in the YAML description field — all five dimensions in one place.
               No separate body section needed. The YAML description IS the grounding",

    format: "
      description: >
        (Who) {executor — AI, sub-agent, or human}.
        (What) {state transformation — the deliverable}.
        (When) {condition — what triggers selection}.
        (Where) {location — execution environment, output path, deploy target}.
        (Why) {rationale — why this exists as a separate skill}.
    ",

    fields: [
      who:   "Guardrails AI on ownership — who executes this UC.
                AI (e.g., Claude Code): auto-proceed.
                Sub-agent: AI spawns and delegates.
                Human: AI stops and asks.
              At flow level (§18), each step can declare its own WHO",
      what:  "Guardrails AI on transformation — what state change A→B this skill performs",
      when:  "Guardrails AI on selection — what condition triggers this skill",
      where: "Guardrails AI on location — where A comes from (input source),
              where B goes to (output destination).
              Examples: .gem-squared/work-plan/ → .gem-squared/archive/,
              stdin → .claude/skills/{name}/SKILL.md, git log → stdout",
      why:   "Guardrails AI on purpose — why this exists as a separate unit.
              Prevents trigger-collision when two skills share similar what/when"
    ],

    rule: "∀ skill: YAML description MUST contain all 5W fields.
           This is the primary grounding for AI contract-based selection"
  ],

  (* ═══ §18 Flow Notation ═══ *)
  Flow_Notation ≜ [
    pattern:  "F ≜ <<S₁, S₂, ..., Sₙ>>  where N ≤ 9, desire N ≤ 5",
    step_def: "Sᵢ ≜ [name: 𝕊, action: 𝕊, pre: Predicate, post: Predicate]",

    (* — L0 example: filesystem only, no server — *)
    L0_example: "
      F ≜ <<
        [name: \"scaffold\",
         action: \"Generate task_id (uuidgen). Write .gem-squared/work-plan/WP-ST-{N}.md
                  with CONTRACT per unit-work\",
         pre:  work ≠ ⊥ ∧ project_slug ≠ ⊥,
         post: wp_path ≠ ⊥ ∧ task_id ≠ ⊥],

        [name: \"update_alarm\",
         action: \"Edit alarm.md — add to Active Tasks, update counters\",
         pre:  wp_path ≠ ⊥,
         post: alarm_updated = ⊤]
      >>
    ",

    (* — L1 enhancement: additionally syncs to gem2-studio — *)
    L1_note: "On L1, step 1 additionally calls gem2_task_create(title, project_slug)
              for server-side task tracking. Step 2 additionally calls
              gem2_task_update(status=IN_PROGRESS). L0 flow is the baseline",

    chain_invariant: "∀ i ∈ 1..N-1: F[i].post ⟹ F[i+1].pre",

    no_branching: "UNIT-SKILL flow is a straight sequence.
                   Branching is the AI's job (reads B, decides next skill).
                   IF/THEN/ELSE within a step's action field is acceptable (local logic).
                   IF/THEN/ELSE between steps is NOT — split into separate skills"
  ]

  (* For artifact definitions (tagging, work-plan structure, unit-contract),     *)
  (* see companion document: TPMN-LIFECYCLE-GUIDE.md                             *)

  (* For authoring protocol (method, dimensions, modes, anti-patterns),          *)
  (* see: .gem-squared/reference/authoring-guide.md                              *)

]

(* ═════════════════════════════════════════════════���══════════════════════════ *)
(* END TPMN_SKILL_STANDARD v4.1                                              *)
(*                                                                            *)
(* Part 1: §1-5   — TPMN Grammar (symbols, TLA+, Panini, math, NL)          *)
(* Part 2: §6-14  — UNIT-SKILL Definition (core, rules, mandate, selection, *)
(*                   knowledge accumulation, rationale, compaction, epistemic)*)
(* Part 3: §15-18 — Skill File Structure (skeleton, contract, 5W, flow)     *)
(*                                                                            *)
(* Companion: TPMN-LIFECYCLE-GUIDE.md (tagging, WP, UC, example, validation) *)
(* Companion: authoring-guide.md (authoring protocol)                         *)
(*                                                                            *)
(* Source: WP-ST-55 + WP-ST-92 + WP-ST-93 + WP-ST-94                        *)
(* Source: WP-ST-50 AI Skill Selection Pipeline                               *)
(* Source: Claude Skill Community Pain Points Research (2026-04-16)           *)
(* ═══���════════════════════════════════════════════════════════════════════════ *)
