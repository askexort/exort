# Regex Quick Reference

## Character Classes
- `.` — any character
- `\d` — digit (0-9)
- `\w` — word char (a-z, A-Z, 0-9, _)
- `\s` — whitespace
- `[abc]` — character set
- `[^abc]` — negated set
- `[a-z]` — range

## Quantifiers
- `*` — 0 or more
- `+` — 1 or more
- `?` — 0 or 1
- `{n}` — exactly n
- `{n,m}` — n to m

## Anchors
- `^` — start of string
- `$` — end of string
- `\b` — word boundary

## Groups
- `(...)` — capture group
- `(?:...)` — non-capture group
- `(?P<name>...)` — named group
- `\1` — backreference

## Common Patterns
- Email: `[\w.+-]+@[\w-]+\.[\w.]+`
- URL: `https?://[^\s]+`
- Phone: `\+?\d[\d\s-]{7,}`
- IP: `\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}`
