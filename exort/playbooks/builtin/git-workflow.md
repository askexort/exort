# Git Best Practices

## Commits
- Atomic commits (one change per commit)
- Conventional format: `type(scope): description`
- Types: feat, fix, docs, style, refactor, test, chore
- Keep subject under 50 chars
- Body explains WHY, not WHAT

## Branching
- `main` — production-ready
- `develop` — integration branch
- `feat/xxx` — new features
- `fix/xxx` — bug fixes
- `hotfix/xxx` — urgent production fixes

## Pull Requests
- Small, focused changes
- Clear description of what and why
- Link to issue/ticket
- Self-review before requesting review
- Squash merge for clean history

## Commands
- `git stash` — save work in progress
- `git rebase -i` — clean up commits
- `git bisect` — find bug-introducing commit
- `git blame` — find who wrote what
- `git log --oneline --graph` — visual history
