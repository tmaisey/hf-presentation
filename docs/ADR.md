## ADR model — decision records

Architecture decisions (**imperative** how-and-why) live in **`docs/ADR.jsonl`**, one per line.
**MUST** add sparingly: only where a constraint or tech bet must be honoured. This is the durable,
greppable home for central architecture reasoning: PRD is too high-level, spec is feature intent,
git is history, and docstrings hold it implicitly and decentralised, so a fresh context loses it.

### Schema

Fields **MUST** be in this order:

```json
{"id": "ADR-001", "status": "proposed", "originator": "agent:<owner>", "validated_by": null, "name": "Spec backlog is JSONL", "description": "the binding constraint future code must honour", "justification": "why, over which rejected alternatives, on what assumptions", "refs": ["docs/"]}
```

- `id`: `ADR-0NN`, unique; code points back to it.
- `status`: `proposed` / `accepted` / `superseded` / `deprecated` (lifecycle below).
- `originator` / `validated_by`: one grammar, **`<actor>:<accountable-human>`**. Actor is `agent`,
  an agent name, or `user`; suffix is always the accountable person. `validated_by: null` = an
  unvalidated agent bet. **NEVER** store the LLM model: the git author holds it.
- `name`: ~5-word label.
- `description`: the constraint, the stable *what* future code must honour.
- `justification`: *why*, over which *rejected alternatives*, on what *assumptions*.
- `refs`: coarse, directional pointers (lockfile, module root, `ARCHITECTURE.md`, research doc,
  prototype). **NEVER** path-to-line: precision lives in reverse markers (below).
- `superseded_by`: `"ADR-0NN"`, present **only** when `status: superseded` (one-directional; grep
  the reverse). `deprecated` = abandoned with no replacement.

### Lifecycle: proposed → accepted → {superseded, deprecated}

- `proposed`: identified (requirements / research / prototype) but not yet in code.
- `accepted`: constraint adopted in code. The builder **MUST** flip it at the accept point and write
  `justification`, then build. Health invariant: an `accepted` ADR has **≥1 marker** in code/docs;
  `accepted` with no marker, or `proposed` with one, is a bad smell.
- **Keep, NEVER delete.** Superseded/deprecated ADRs stay: a retired record is an anti-repeat
  guardrail that stops a fresh context re-treading a reversed decision. Filter `status: accepted`
  to read live constraints.
- Once accepted, an ADR is **superseded, NEVER rewritten**: the same anti-tampering property the
  red commit gives tests (an editable accepted decision is untrustworthy).

### ADR ↔ code link (MUST)

- Code **or doc** implementing a decision **MUST** back-reference it via the marker `ADR: ADR-0NN`
  in its docstring (code) or prose (docs). Grep the marker to find everything a decision governs.
  The link lives once, in the implementing artifact (DRY, code as ground truth); the ADR line
  carries only a coarse forward hint in `refs`.
- `ADR:` is a **distinct primitive** from `Spec:` and is **not** bound by the tests-not-helpers
  rule: they are separate grep namespaces, so the marker attaches wherever the decision is
  implemented, including a `helper_` module. **MUST** mark **every** site, not just one, so grep
  returns the decision's full footprint.
