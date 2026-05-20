# Performance Optimization Guide

## Profiling
1. Measure before optimizing
2. Find the bottleneck (CPU, memory, I/O, network)
3. Profile with appropriate tools

## Python
- Use generators over lists for large data
- `dict` lookups over `list` searches
- `join()` for string concatenation
- `__slots__` for data classes
- `functools.lru_cache` for memoization
- `collections.defaultdict` over manual dict init

## Database
- Add indexes on WHERE/JOIN columns
- Use EXPLAIN to analyze queries
- Batch inserts over individual ones
- Connection pooling
- Limit result sets

## Network
- Batch API calls
- Cache responses (with TTL)
- Compress payloads (gzip)
- Use async for I/O-bound work
- Connection reuse

## Memory
- Process data in chunks/streaming
- Use weakref for caches
- Close files/connections explicitly
- Profile with tracemalloc
