# Eval sets

Saved fixtures for the suites in `06-ai-agents-spec.md` section 10. Pages are saved text, never fetched live.

## recheck.jsonl

60 page pairs for the `recheck` feature (06 section 5.12): 15 `confirmed`, 15 `changed` (3 with hidden instructions),
15 `not_shown` (5 where the model claims a change that is not on the page, so grounding downgrades it) and 15
`unreachable` (error statuses, a PDF, empty pages, JavaScript shells, and 3 blocked hosts that must never be opened).

One JSON object per line: `id`, `fact` (the saved text), `source_url`, `page` (`kind`, `body`, optional `status` and
`content_type`), `model` (the scripted answer a model gave), `expected` (the final result) and `expected_value`.

Run: `apps/api/tests/ai/test_recheck.py::test_recheck_eval_set_runs_on_the_fake_client_with_every_value_grounded`.
Gate: result accuracy 95% or more and every shown `current_value` grounded in the page (100%).
This set is a scripted fixture harness: it proves fetch, grounding and the decision code, not model accuracy. The live
accuracy run (`EVALS_LIVE=1`, with a `--max-usd`) belongs to WF-057; it will replace the scripted `model` with real answers.
