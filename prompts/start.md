# Session Start Prompt

Run this workflow for the current session.

1. Confirm the selected `mode`.
2. Read only mode-relevant documents.
3. Check `docs/ops/known_issues.md` for active issues related to this mode.
4. Re-prioritize up to 3 goals from `current_sprint.md`.
5. Separate "decision items" from "execution items".
6. Pre-declare which documents must be updated at session close.

## Forbidden Patterns

Do NOT:
- Change mode mid-session without logging the reason in `current_sprint.md`.
- Skip reading context files (even if you "remember" them).
- Make architectural decisions without creating an ADR.
- Leave test stubs or placeholder assertions (`assert True`, `pass`, `return nil`).
- Modify existing tests solely to make them pass.

## Output format

- Mode:
- Today goals (max 3):
- Active known issues for this mode:
- Decision items:
- Execution items:
- End-of-session update targets:
