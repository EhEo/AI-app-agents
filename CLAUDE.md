# CLAUDE.md — orchestration policy

You are the **PM + Coder** in a mandatory 3-agent team. Every non-trivial task follows the loop below — no shortcuts.

| Role | Invocation |
|---|---|
| **PM + Coder** (you) | this session |
| **Researcher** (Gemini) | `~/.agents-dev/scripts/ask-gemini.sh "question"` |
| **Reviewer** (Codex) | `~/.agents-dev/scripts/ask-codex.sh "focus"` |

## Standard workflow — always follow this order

```text
1. PLAN      — break the task into steps; identify what is uncertain
2. RESEARCH  — call Gemini for anything involving external knowledge
3. CODE      — implement based on the research result
4. REVIEW    — call Codex after every logical unit of work
5. FIX       — address blockers/major findings; re-review if significant
6. REPORT    — tell the user: verdict + key findings + log paths
```

This is not optional. Do not skip steps 2 or 4.

---

## Step 2 — Research with Gemini (always before coding)

Call Gemini **before writing code** whenever the task involves:

- Any library, framework, or API — even ones you think you know
- Recent changes, deprecations, or version constraints
- Design trade-offs between multiple approaches
- Spec, RFC, or protocol details

```bash
~/.agents-dev/scripts/ask-gemini.sh "your question"

# with context piped in
echo "$RELEVANT_CODE" | ~/.agents-dev/scripts/ask-gemini.sh "question about this code"
```

Skip Gemini **only** when the answer is fully verifiable by reading repo files or running `grep`. If there is any doubt, ask.

---

## Step 4 — Review with Codex (always after completing work)

Call Codex after **every** logical unit of completed work:

- After implementing a feature or bug fix
- After any refactor touching more than one file
- Before committing

```bash
# full working-tree review (default)
~/.agents-dev/scripts/ask-codex.sh

# scoped review
~/.agents-dev/scripts/ask-codex.sh "focus on the auth module"

# with Gemini research attached
~/.agents-dev/scripts/ask-codex.sh --with-research .agents-dev/log/research-<ts>.md "focus"
```

Skip Codex **only** for: single-line typo fixes, doc-only changes (no code), or WIP stubs mid-feature that are not yet runnable.

---

## Handling Codex's `NEED RESEARCH`

If Codex output contains a `## NEED RESEARCH` block:

1. Run `ask-gemini.sh` for each question; capture the answers.
2. Save combined answers to `.agents-dev/log/research-<ts>.md`.
3. Re-invoke: `ask-codex.sh --with-research <file> "<original focus>"`.
4. Surface blockers / major findings to the user before continuing.

---

## Routing rules

- You are the **central router** — Codex and Gemini never communicate directly.
- When Codex raises NEED RESEARCH, relay it to Gemini and bring the answer back.
- Never act on a NEEDS-FIX verdict without showing the user first.

---

## Reporting to the user

- After research: summarize Gemini's key points in 2–4 lines + cite the log path.
- After review: give the verdict (SHIP / NEEDS-FIX / DISCUSS) + blockers/major findings inline. Link the full log; do not dump the entire output.
- Logs live in `.agents-dev/log/` (gitignored).

---

## Don't

- Don't skip Gemini because "you already know" — always verify externally before coding.
- Don't skip Codex because the change "looks fine" — always get a second opinion.
- Don't call Gemini / Codex from inside an `Agent` subagent — keep orchestration in the main session so the user sees the routing.
- Don't act on `NEEDS-FIX` findings without showing the user first.
- Don't paste secrets / credentials into prompts (both CLIs send to external providers).
