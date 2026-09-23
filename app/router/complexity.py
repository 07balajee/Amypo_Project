"""Complexity scoring for incoming queries.

M0 stub: a cheap heuristic (token count + question-type keywords), no model calls, <5ms — good
enough to exercise the /route contract before router_prompts.jsonl exists. M3/M5 replace `score()`
with a LogisticRegression model trained on data/synthetic/router_prompts.jsonl (joblib-persisted),
blended with complexity_hint per CLAUDE.md §7: p_final = 0.6*onehot(hint) + 0.4*p_model.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_HIGH_KEYWORDS = re.compile(
    r"\b(compare|design|prove|derive|analyze|analyse|architecture|trade-?off)\b", re.IGNORECASE
)
_LOW_KEYWORDS = re.compile(r"\b(what is|define|list|when is|who is)\b", re.IGNORECASE)


@dataclass(frozen=True)
class ComplexityResult:
    label: str  # "low" | "medium" | "high"
    prob: float  # confidence in `label`, in [0, 1]


def score(query: str, hint: str | None = None) -> ComplexityResult:
    tokens = query.split()
    n = len(tokens)
    if _HIGH_KEYWORDS.search(query) or n > 60:
        label, prob = "high", 0.7
    elif _LOW_KEYWORDS.search(query) or n <= 12:
        label, prob = "low", 0.7
    else:
        label, prob = "medium", 0.6

    if hint:
        # p_final = 0.6 * onehot(hint) + 0.4 * p_model (CLAUDE.md §7).
        onehot_conf = 1.0
        model_conf = prob if hint == label else (1 - prob)
        blended = 0.6 * onehot_conf + 0.4 * model_conf
        label = hint
        prob = round(blended, 4)

    return ComplexityResult(label=label, prob=prob)
