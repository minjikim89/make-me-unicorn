---
description: Run the mmu vibecheck launch gate and fix what it blocks on
argument-hint: "[--changed | --staged | --since <ref> | path]"
allowed-tools: Bash(mmu:*), Bash(uvx:*), Read, Edit
---

Run the launch gate on this project and act on the result.

1. Run `mmu vibecheck $ARGUMENTS --format agent` (default to `--changed` when no argument was given and the project is a git repository; otherwise scan everything). If `mmu` is not on PATH, use `uvx make-me-unicorn vibecheck` with the same flags.
2. Exit 0: report "vibecheck passed" with the count of P1 warnings, and list them in one line each.
3. Exit 1: for every P0 finding, open the reported `path:line`, apply the fix it describes, and re-run the same command. Repeat until it reports 0 blocking.
4. Exit 2: the scanner could not run. Show the error and fix the invocation; do not report a pass.

Do not silence a finding to make the gate pass. Only for a verified false positive, add `mmu-ignore[<rule-id>]: <reason>` on the flagged line and tell me which ones you silenced and why.
