# Python Best Practices

## Style
- Follow PEP 8
- Use type hints (PEP 484)
- f-strings over .format() or %
- Context managers for resources
- Pathlib over os.path

## Structure
- Virtual environments for every project
- requirements.txt or pyproject.toml
- src layout for packages
- Tests in tests/ directory
- __init__.py for clean imports

## Common Patterns
- Dataclasses for data containers
- Enums for constants
- itertools for iteration patterns
- pathlib for file paths
- logging over print
- argparse/click for CLI

## Anti-patterns to Avoid
- Mutable default arguments
- Bare except clauses
- Global state
- Circular imports
- print() for production logging
- eval() on untrusted input

## Testing
- pytest over unittest
- Fixtures for setup
- parametrize for similar tests
- Mock external dependencies
- Test edge cases
