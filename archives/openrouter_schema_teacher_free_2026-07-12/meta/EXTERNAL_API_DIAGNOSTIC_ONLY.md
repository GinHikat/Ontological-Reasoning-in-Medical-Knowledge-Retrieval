# EXTERNAL_API_DIAGNOSTIC_ONLY

All outputs under `output/openrouter_schema_teacher/` were produced with **external
OpenRouter API calls**.

## Competition compliance

The competition description states that external APIs are not allowed for LLM/agent
solutions.

Therefore:

- Do **not** use these outputs in a competition submission.
- Do **not** use them to train the final competition model unless the organizers
  explicitly confirm that external-API-generated offline training data is allowed.

## Purpose

Diagnostic only: measure whether frontier models infer the organizer's intended schema
substantially better than frozen v7 / v10 pipelines.

Project name: `openrouter_schema_teacher` (not a competition pipeline version / not v11).
