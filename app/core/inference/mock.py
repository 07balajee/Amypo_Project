"""MockGateway: deterministic, no-weights stand-in for GatewayClient used by all tests and by
services when gateway.use_mock=true (e.g. CI, offline dev without the llama.cpp containers running).
"""
from __future__ import annotations

import asyncio
import hashlib

from app.core.inference.client import GenerateResult, Tier

_TOKENS_PER_SECOND = {"local": 18.0, "remote": 40.0}
_BASE_LATENCY_MS = {"local": 120, "remote": 60}


class MockGateway:
    def __init__(
        self,
        latency_s: float = 0.0,
        fail_tiers: set[Tier] | None = None,
        tokens_per_second: dict[str, float] | None = None,
    ) -> None:
        """
        latency_s: extra artificial sleep before returning (for timeout/breaker tests).
        fail_tiers: tiers that should raise ConnectionError (simulates an unreachable tier).
        tokens_per_second: override EWMA throughput used to size latency_ms.
        """
        self._latency_s = latency_s
        self._fail_tiers = fail_tiers or set()
        self._tps = tokens_per_second or _TOKENS_PER_SECOND

    async def generate(
        self, tier: Tier, messages: list[dict[str, str]], max_tokens: int
    ) -> GenerateResult:
        if tier in self._fail_tiers:
            raise ConnectionError(f"MockGateway: tier '{tier}' is configured to fail")
        if self._latency_s:
            await asyncio.sleep(self._latency_s)

        prompt = " ".join(m.get("content", "") for m in messages)
        tokens_in = max(1, len(prompt.split()))
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8]
        tokens_out = min(max_tokens, max(8, tokens_in // 2))
        text = f"[mock:{tier}:{digest}] deterministic response to: {prompt[:120]}"
        latency_ms = _BASE_LATENCY_MS[tier] + int(1000 * tokens_out / self._tps[tier])
        return GenerateResult(
            text=text, tokens_in=tokens_in, tokens_out=tokens_out, latency_ms=latency_ms
        )

    async def health(self, tier: Tier) -> bool:
        return tier not in self._fail_tiers

    async def aclose(self) -> None:
        return None
