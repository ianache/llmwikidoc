---
type: concept
name: Exponential Backoff
created: 2026-05-01T23:47:04Z
updated: 2026-05-01T23:47:04Z
confidence: 0.70
sources: [snapshot-20260501-234218]
related: []
tier: working
---
# Exponential Backoff

A retry strategy implemented in `LLMClient.generate` that increases the waiting time between failed API call attempts to prevent overwhelming the server and handle transient errors.

## References

- [snapshot: snapshot-20260501-234218]
