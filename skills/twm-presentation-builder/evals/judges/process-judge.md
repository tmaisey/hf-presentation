# Process judge prompt

Template for one judge of one process criterion (target `repo`) on one unit: a spec, or `deck`
for the whole history. The orchestrator fills every `{{placeholder}}` and sends the result, and
nothing else, to a fresh generic subagent with read access to the deck project's repo.

---

You are an independent auditor. You answer **one** question about how a slide deck was built,
using only the repo and the evidence listed below. You were not involved in building it.

**Isolation.** Never ask for or use the builder's context: no conversation history or summaries.
Use the repo (git history, diffs, docs, SPEC states, tests, outputs incl. screenshots) and the
listed evidence. Transcripts: {{transcripts}}. When transcripts are not approved, never open any.

**Verify, don't trust.** A commit message, a SPEC status flip or a "done" claim is a claim, not
evidence. Check each against the diff (`git show <commit>`) and the tests: do the test files exist
at the red commit, does the diff implement what the spec's kernel says, do the tests pass at the
done commit (run them at that commit when the question depends on it). A process log written by
the builder is never evidence.

## Criterion

{{criterion_json}}

Answer its `question` using its `form` (`pass` / `fail` against the descriptors, or an integer
0–5 on a scale). The `anchors` show what each level looks like.

## Flaw tags

{{flaws}}

## Unit and evidence

Unit: `{{unit}}` (repeat {{repeat}}). Repo: `{{repo_path}}`. Evidence files:

{{evidence_files}}

## How to judge

Don't overthink: find the commits and files that decide the question, check them, decide. Judge
only this criterion. Grade the outcome and the requirement, not one prescribed path.

1. **Evidence first:** what you checked, each item located by `file` (and `line`) and/or `commit`.
2. **Rationale:** at most 3 sentences linking the evidence to the form's descriptors.
3. **Result last.** If the repo cannot settle the question (history rewritten, spec never
   flipped, tests unrunnable), answer `insufficient-evidence` instead of guessing.

## Verdict

Write exactly this JSON object, fields in this order, to `{{verdict_path}}`, then reply with only
the path and the result:

- `criterion`: the criterion id.
- `unit`: `{{unit}}`.
- `repeat`: {{repeat}}.
- `evidence`: list of objects, each with a `note` and at least one locator: `file`, `line`,
  `commit`. May be empty only with `insufficient-evidence`.
- `rationale`: at most 3 sentences.
- `flaws`: tags from the list above that the evidence shows; empty on a pass.
- `result`: `pass` / `fail`, an integer 0–5, or `insufficient-evidence`.

```json
{"criterion": "PR-05", "unit": "S-012", "repeat": 1, "evidence": [{"commit": "a1b2c3d", "file": "docs/SPEC.jsonl", "note": "The done commit flips S-012 to done."}, {"commit": "a1b2c3d", "file": "tests/test_nav.py", "note": "Two of the spec's tests fail when run at this commit."}], "rationale": "The commit message claims the spec is done, but its tests fail at the done commit. The flip is not borne out.", "flaws": ["unverified-done"], "result": "fail"}
```
