# Shared Drupal client

This directory contains the framework-neutral HTTP boundary for the lab's shared Drupal substrate.

It may own:

- Drupal URL and HTTP Basic authentication handling
- correlation IDs
- request/response envelope transport
- sanitized HTTP errors

It must not own:

- prompts or model calls
- LangGraph graphs or checkpoints
- CrewAI crews, flows, or role decomposition
- Drupal AI agent orchestration
- framework retry, recovery, sequencing, or persistence behavior

Step 17 adds `find_images_needing_review()`, a deterministic read-only operation. The three later
implementations may call this client, but each framework must still own its context assembly, model
invocation, state, verification, human-continuation, and recovery behavior.
