# Inter-rater agreement — DFAH calibration corpus (v0.8.6 P2)

> Companion to `corpus.jsonl` + the framework subset files.
> Documents the v0.8.6 cycle's multi-rater methodology +
> Cohen's Kappa probe results.

## What we did

Per the v0.8.6 plan §29 P2, we computed Cohen's Kappa κ
between two raters on the bundled framework-agnostic
calibration corpus (`corpus.jsonl`, 51 entries).

- **Rater 1**: Allen's hand-labels (the corpus's `faithful`
  field)
- **Rater 2**: deterministic rule-based jaccard scorer
  (`scripts/compute_inter_rater_kappa.py --rule jaccard
  --rule-threshold N`); claim is faithful iff the
  best-clause jaccard token-overlap meets the threshold

Why a rule-based rater 2 instead of an LLM rater or human
rater 2: cost-aware single-session compression. The kappa
infrastructure ships in v0.8.6; an honest rule-based probe
surfaces real signal (where the rule disagrees with hand-
labels) without burning LLM tokens or human time.

## Results

Cohen's Kappa swept across thresholds against `corpus.jsonl`
(51 entries; 25 hand-labeled faithful, 26 unfaithful):

| Threshold | κ | Landis-Koch |
|---|---|---|
| 0.30 | 0.0585 | slight |
| 0.50 | 0.0956 | slight |
| 0.70 | 0.3284 | fair |
| 0.85 | 0.4848 | moderate |

**Best κ = 0.4848 (moderate) at threshold 0.85.** Below the
v0.8.6 acceptance target of κ ≥ 0.80 (Landis-Koch
substantial-or-better boundary).

Per the v0.8.6 §29 R3 mitigation: when κ remains < 0.80
after threshold-tuning, ship as **"single-rater + κ probe
inconclusive"** with documented rationale + carry the
multi-rater work forward.

## What this tells us

The rule-based jaccard rater is a deliberately weak proxy for
hand-labels. The corpus DESIGN (per `README.md` §"Entry
categories") includes:

- **Verbatim faithful** entries — claim text appears in source
  clauses → high jaccard → rule + Allen agree
- **Paraphrase faithful** entries — same meaning, different
  vocabulary → low jaccard → rule says unfaithful, Allen says
  faithful → DISAGREEMENT
- **Semi-related unfaithful** entries — high token overlap,
  different topic → high jaccard → rule says faithful, Allen
  says unfaithful → DISAGREEMENT
- **Hallucination unfaithful** entries — no overlap → low
  jaccard → rule + Allen agree

The substantial moderate-to-poor agreement at all thresholds
empirically demonstrates **exactly what motivated the v0.8.3
P1.1 sentence-transformers semantic faithfulness path**:
token-overlap is a poor approximation of semantic faithfulness
when paraphrase + semi-related entries are in scope.

A rule-based rater 2 IS NOT a human rater — high κ with this
rule would mean "the rule mostly agrees with Allen", NOT
"Allen's labels are correct". Low κ surfaces a known + intended
gap. Both signals are useful for label-quality probing.

## Acceptance status (v0.8.6)

- **Cohen's Kappa script**: SHIPPED — `scripts/compute_inter_rater_kappa.py`
- **Two-rater file mode**: SHIPPED — accepts `--rater1` +
  `--rater2` JSONL files
- **Rule-based rater mode**: SHIPPED — accepts `--rule jaccard`
  + `--rule-threshold N`
- **CI gate**: SHIPPED — exit 0 when κ ≥ `--target` (default
  0.80), exit 1 otherwise
- **Tests**: SHIPPED — 25 unit tests covering κ formula +
  Landis-Koch labels + rule-based rater
- **Cohen's Kappa κ ≥ 0.80 acceptance**: NOT MET — best κ
  (0.4848 at threshold 0.85) is moderate but below substantial
- **Multi-rater methodology**: documented as single-rater +
  rule-probe-inconclusive per §29 R3

## v0.8.7 / v0.9.0 reservation

A real LLM-assisted second rater (e.g., `claude-3-5-sonnet`
prompted to label a 30-entry stratified-random subset using
the same rubric Allen used) is the next step toward κ ≥ 0.80.
Practically:

- LLM tokens cost: ~30 entries × ~500 tokens ≈ ~15K input
  tokens ≈ ~$0.05 with Claude Sonnet
- Human time: ~30 minutes to review the LLM's labels +
  reconcile divergent entries
- Output: `tests/data/dfah-calibration/labels-rater2.jsonl`
  (the 30-entry subset with rater 2 labels)
- Gate: re-run `compute_inter_rater_kappa.py --rater1 ...
  --rater2 labels-rater2.jsonl`; expect κ ≥ 0.80 if the rubric
  is unambiguous

A human-second-rater pass (Allen's GRC mentor / domain expert)
remains reserved for v0.9.0 federal-compliance theme — the
walk-through opener naturally surfaces a candidate.

## Reproducibility

To re-run this analysis:

```bash
# Sweep thresholds against the framework-agnostic corpus
for t in 0.30 0.50 0.70 0.85; do
    echo "=== threshold $t ==="
    uv run python scripts/compute_inter_rater_kappa.py \
        --rater1 tests/data/dfah-calibration/corpus.jsonl \
        --rule jaccard \
        --rule-threshold $t
done

# Per-framework probe
uv run python scripts/compute_inter_rater_kappa.py \
    --rater1 tests/data/dfah-calibration/corpus_nist.jsonl \
    --rule jaccard \
    --rule-threshold 0.60
```

The kappa formula + Landis-Koch interpretation are deterministic;
results reproduce byte-for-byte across hosts.
