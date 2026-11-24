# Results: Claude 5 family, 3 runs (Nov 11 2026)

Setup: qs 6.17.1 (the query string library Express uses), 6 planted bugs, 31 of 1,699 test assertions failing. Four
Claude Code agents, one copy each with fresh git history, the prompt in `PROMPT.md` sent to all four in the same second.
Default effort for each model: Fable 5.2, Sonnet 5.5 and Haiku 5.5 on medium, Opus 5.5 on high. Claude Max plan.

Time = the prompt landing to the final answer, from each agent's transcript (it matches Claude Code's own on screen
"... for" line). Output tokens are counted once per message (see "How tokens are counted" below).

| Run | Fable 5.2 | Opus 5.5 | Sonnet 5.5 | Haiku 5.5 |
|---|---|---|---|---|
| 1 (recorded) | **3:04** · 8 tool calls · 3,349 tokens | 3:42 · 9 · 3,496 | 3:16 · 7 · 2,896 | 4:35 · 19 · 14,900 |
| 2 | **2:05** · 3,457 tokens | 2:33 · 2,841 | 3:51 · 3,287 | 3:48 · 13,155 |
| 3 | **2:20** · 3,720 tokens | 2:42 · 3,231 | 3:01 · 2,786 | 4:08 · 12,976 |
| **Median** | **2:20** | 2:42 | 3:16 | 4:08 |

- 12 of 12 runs fixed all six bugs: 1,699 of 1,699 passing, `test/` untouched.
- Fable won all 3 runs. In run 2 Haiku beat Sonnet.
- Haiku used about 4x the output tokens of the others in every run.
- In run 1, Fable and Opus restored the original lines exactly; Sonnet and Haiku fixed the comma limit bug a different way.
- `python race.py score` re-reads these numbers from the transcripts. None of the 12 opened the answer key.

## Caveats
One repo, one prompt, three runs. Opus ran on high effort and the others on medium (each model's default). Off by one
bugs in a well tested library are a narrow kind of work; treat this as one data point, not a ranking.

## How tokens are counted
Claude Code writes one transcript row per content block (text, each tool call) and repeats the message's usage on every
row. Summing rows double counts: an earlier draft of these results said 56,003 tokens for one run that way. `race.py`
keeps one number per message id.
