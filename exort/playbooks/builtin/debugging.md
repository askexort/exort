# Debugging Methodology

## 1. Reproduce
- Get exact steps to reproduce the bug
- Note the environment (OS, versions, etc.)
- Confirm it's reproducible

## 2. Isolate
- Narrow down WHERE the bug occurs
- Use binary search: comment out half the code
- Check recent changes (git log)
- Read the error message carefully

## 3. Diagnose
- Add print/log statements
- Check variable values at key points
- Verify assumptions (types, ranges, nulls)
- Check edge cases (empty, null, max values)

## 4. Fix
- Make ONE change at a time
- Test after each change
- Write a test that catches this bug
- Document what went wrong

## Common Pitfalls
- Off-by-one errors
- Race conditions
- Stale cache/state
- Encoding issues
- Missing error handling
