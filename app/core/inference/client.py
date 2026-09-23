"""GatewayClient: uniform interface to the local and remote (simulated cloud) llama.cpp tiers.

Both tiers speak the llama.cpp server's OpenAI-compatible /v1/chat/completions endpoint, so one
HTTP client handles both — the router only ever talks to this interface, never to a real cloud SDK,
so swapping in an actual provider later means adding a new implementation of GatewayClient, not
touching router code (see ADR-1 in CLAUDE.md).
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal, Protocol

import httpx

Tier = Literal["local", "remote"]


@dataclass(frozen=True)
class GenerateResult:
    text: str
    tokens_in: int
    tokens_out: int
    latency_ms: int


class GatewayClient(Protocol):
    async def generate(
        self, tier: Tier, messages: list[dict[str, str]], max_tokens: int
    ) -> GenerateResult: ...

    async def health(self, tier: Tier) -> bool: ...

    async def aclose(self) -> None: ...


class HttpGatewayClient:
    """Talks to real llama.cpp server containers over HTTP."""

    def __init__(self, local_url: str, remote_url: str, timeout_s: float = 25.0) -> None:
        self._urls: dict[Tier, str] = {"local": local_url, "remote": remote_url}
        self._client = httpx.AsyncClient(timeout=timeout_s)

    async def generate(
        self, tier: Tier, messages: list[dict[str, str]], max_tokens: int
    ) -> GenerateResult:
        start = time.perf_counter()
        resp = await self._client.post(
            f"{self._urls[tier]}/v1/chat/completions",
            json={"messages": messages, "max_tokens": max_tokens, "stream": False},
        )
        resp.raise_for_status()
        data = resp.json()
        latency_ms = int((time.perf_counter() - start) * 1000)
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return GenerateResult(
            text=text,
            tokens_in=usage.get("prompt_tokens", 0),
            tokens_out=usage.get("completion_tokens", 0),
            latency_ms=latency_ms,
        )

    async def health(self, tier: Tier) -> bool:
        try:
            resp = await self._client.get(f"{self._urls[tier]}/health", timeout=2.0)
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def aclose(self) -> None:
        await self._client.aclose()


def build_gateway_client(use_mock: bool, local_url: str, remote_url: str) -> GatewayClient:
    if use_mock:
        from app.core.inference.mock import MockGateway

        return MockGateway()
    return HttpGatewayClient(local_url=local_url, remote_url=remote_url)
