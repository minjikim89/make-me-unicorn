# Session Close Prompt

Update project state based on today's work. Use the structured tags below.

## Output Format

### [DONE] Completed Work
- What was completed this session
- Files changed and why

### [DECISION] Decisions Made
- Decision: what was decided
- Context: why this choice
- Alternatives rejected: what was considered
- If significant, create ADR in `docs/adr/`

### [ISSUE] Open Issues
Classify each issue:
- **context_deficit**: needed information was missing at session start
- **direction_error**: wrong approach was selected or requirements misunderstood
- **structural_conflict**: code and docs contradict each other

Format:
- Category: context_deficit | direction_error | structural_conflict
- Description: what went wrong or remains unresolved
- Impact: what is blocked
- Log to `docs/ops/known_issues.md` if unresolved

### [NEXT] Next Session
- First task: what to do immediately
- Mode: recommended mode for next session
- Context files needed: which docs to inject
- Carry-forward: unresolved items from this session

## Checklist
1. Update completed/incomplete items in `current_sprint.md`.
2. If [DECISION] items exist, create ADR drafts in `docs/adr/`.
3. If [ISSUE] items exist, log to `docs/ops/known_issues.md`.
4. Apply minimal updates to changed `docs/core/*` or `docs/ops/*` files.
5. Verify `mmu doctor` still passes.
