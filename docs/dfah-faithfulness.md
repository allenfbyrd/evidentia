# DFAH faithfulness scoring (v0.8.2 P3.1)

> Status: v0.8.2 stdlib baseline. Library API:
> `evidentia_ai.eval.faithfulness.faithfulness_score()`. Sister
> docs: `docs/eval-harness.md` (determinism + replay), §25 plan
> P3.1 (cycle context).

## What faithfulness scoring measures

The Decision-Faithfulness Assessment Harness (DFAH; arXiv
2601.15322) defines three audit-grade metrics for AI-produced
artifacts:

1. **Determinism** — same input + same model + same temperature
   produces the same output across N samples. Shipped in v0.8.0.
2. **Replay equivalence** — re-running with a pinned
   `GenerationContext` produces a hash-identical output. Shipped
   in v0.8.0.
3. **Faithfulness** — generated claims trace back to the source
   policy clauses. **Shipped in v0.8.2**.

Faithfulness catches a different failure mode from determinism.
A model can be perfectly deterministic (same output every run)
and still hallucinate — generating plausible-sounding text that
doesn't actually appear in the source policy. Faithfulness
scoring quantifies how grounded each generated claim is in the
input clauses.

## v0.8.2 stdlib baseline (Jaccard token-overlap)

The v0.8.2 implementation uses Jaccard token-overlap similarity:

```
faithfulness(claim, clauses) = max over c in clauses of
    |tokens(claim) ∩ tokens(c)| / |tokens(claim) ∪ tokens(c)|
```

Token extraction strips punctuation + lowercases + drops non-
ASCII. The default threshold is **0.3** — conservative for the
stdlib baseline (Jaccard scores tend to be lower than semantic-
similarity scores for paraphrases).

This baseline is intentionally conservative:

- **Catches gross hallucinations** — a claim with zero token
  overlap to any clause scores 0.0 + fails the threshold.
- **Misses paraphrases** — "the system enforces account
  management" vs "AC-2 requires account management procedures"
  share enough tokens to pass; "MFA is required for admin
  accounts" vs "AC-2 mandates two-factor authentication for
  privileged users" share very few tokens despite being
  semantically equivalent.

For paraphrase-tolerant scoring, see "Future work" below.

## Library API

```python
from evidentia_ai.eval import faithfulness_score

result = faithfulness_score(
    claim="The system enforces account management procedures",
    source_clauses=[
        "AC-2 requires the organization to manage user accounts",
        "AC-3 enforces access enforcement policies",
        "AU-2 specifies auditable events",
    ],
    threshold=0.3,
)

print(result.score)            # e.g., 0.4
print(result.passed)           # True (score >= threshold)
print(result.evidence_clauses) # ["AC-2 requires...", ...]  (top-3)
print(result.method)           # "jaccard-stdlib"
```

The result is a Pydantic model — JSON-serializable + Sigstore-
signable as part of a wider `EvalResult`.

## When to wire this into your pipeline

Faithfulness scoring is most valuable AFTER determinism
scoring passes. The flow:

1. Generate the AI artifact (e.g., a risk statement) N times
   under the same context. Determinism check confirms the
   output is stable.
2. For each atomic claim in the modal output, run
   `faithfulness_score(claim, source_clauses)`. Source clauses
   are the policy-document text the operator wants to anchor
   against.
3. CI gate fails if any per-claim score is below the threshold
   (the harness fires
   `EventAction.AI_EVAL_FAITHFULNESS_VIOLATION` per failing
   claim for audit visibility).

The atomic-claim extraction step is **not yet automated** in
v0.8.2 — operators bring their own decomposition (e.g., split
on sentence boundaries; or use the v0.8.1 PRT trace's
per-claim list directly via
`risk_statement.reasoning_trace.claims`). v0.8.3 will land
LLM-driven atomic-claim extraction reusing the PRT pattern.

## Tuning the threshold

The default 0.3 is conservative. Operator-side tuning:

- **Lower** (e.g., 0.1) for paraphrase-heavy corpora — your
  policy clauses don't share much vocabulary with the LLM's
  preferred phrasing.
- **Raise** (e.g., 0.5) for verbatim-quote corpora — your
  policy clauses are written in plain English the LLM
  reproduces literally.

Always pair threshold-tuning with a small audit set: hand-
label 20-50 known-faithful + known-unfaithful claims, then
choose the threshold that minimizes false-positives on
known-faithful + false-negatives on known-unfaithful.

## Future work (v0.8.3+)

- **Sentence-transformers semantic similarity**: install
  `evidentia-ai[eval-faithfulness]` to opt into a sentence-
  embeddings-based score. Higher precision on paraphrases at
  the cost of ~400 MB model download.
- **LLM-driven atomic-claim extraction**: reuse the v0.8.1 PRT
  decomposition prompt to split a generated risk statement
  into claims automatically + score each.
- **Calibration corpus expansion**: ship a 50-100 prompt-id
  corpus of (claim, source_clauses, faithful?) labels so
  operators can tune their threshold against a published
  baseline.
- **CI gate wiring**: extend `evidentia eval risk-determinism
  --check-faithfulness --faithfulness-threshold N` to fire the
  full faithfulness check inline alongside determinism.

## References

- arXiv 2601.15322 — DFAH framework
- `evidentia_ai.eval.faithfulness` — library implementation
- `tests/unit/test_eval/test_faithfulness.py` — invariants +
  example inputs
- §25.2 P3.1 / §25.3 step 6 (v0.8.2 cycle plan)
- Sister doc: `docs/dockerfile-pinning.md` (v0.8.2 G4 closure
  — supply-chain hardening companion)
