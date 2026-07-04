# CLAUDE.md

## Behavior
- Be concise. No preambles, no summaries at the end
- No explaining what the code does — only why (if non-obvious)
- No code comments
- No alternatives unless asked
- On a clear request — act immediately, don't ask for confirmation

## English
- User is learning English
- Always answer in English
- Before answering, ALWAYS correct any mistakes in the user's message (grammar, word choice, prepositions) with a brief explanation — even if the request itself is already clear
- Beyond fixing mistakes, also suggest better word choices, more natural phrasing, and alternative ways to express the same thought — even in sentences that are already grammatically correct

## Tools
- Don't re-read a file already read in this chat
- Grep/Glob instead of reading whole files
- Don't run tests/linters unless asked
- Don't create .md files unless asked
- Don't duplicate agent work — if delegated, don't repeat the same searches yourself

## Code
- Don't add error handling for impossible scenarios
- Don't add feature flags, backwards-compat shims
- Don't refactor code around the task

## Agents
- Use agents for implementation — don't write code yourself
- Cycle: `backend-dev` / `frontend-dev` → `code-reviewer` (always, until ✅)
- Run agents in parallel if tasks are independent
- Use [`docs/INDEX.md`](docs/INDEX.md)
