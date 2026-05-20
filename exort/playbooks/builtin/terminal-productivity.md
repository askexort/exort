# Terminal Productivity Guide

## Essential Commands
- `find . -name "*.py" -exec grep -l "TODO" {} \;` — Find files with TODO
- `git log --oneline --graph --all` — Visual git history
- `du -sh * | sort -rh | head -20` — Largest files/dirs
- `curl -s https://api.github.com/users/{user}/repos | jq '.[].name'` — List repos

## Useful Aliases
```bash
alias ll='ls -alF'
alias gs='git status'
alias gp='git push'
alias dc='docker compose'
```

## Shell Tricks
- `!!` — Repeat last command
- `!$` — Last argument of previous command
- `Ctrl+R` — Reverse search history
- `Ctrl+A/E` — Jump to start/end of line
- `| pbcopy` — Copy output to clipboard (macOS)
