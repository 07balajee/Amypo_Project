"""M0/M1 placeholder standing in for the llama.cpp server containers (`inference`, `remote-tier`).

M2 replaces this with the real `ghcr.io/ggml-org/llama.cpp:server` image + baked GGUF weights
(Qwen2.5-1.5B-Instruct for local, Llama-3.2-3B-Instruct for remote — see CLAUDE.md §3). Until then,
this speaks just enough of the OpenAI-compatible /v1/chat/completions + /health surface that
GatewayClient(use_mock=false) has something real to hit for integration testing, with canned text
instead of a real model. Not used when gateway.use_mock=true (the default).
"""
from __future__ import annotations

import os
import time

from fastapi import FastAPI, Request

app = FastAPI(title="inference-stub")
TIER_NAME = os.environ.get("TIER_NAME", "local")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/v1/chat/completions")
async def chat_completions(request: Request) -> dict:
    body = await request.json()
    messages = body.get("messages", [])
    prompt = " ".join(m.get("content", "") for m in messages)
    max_tokens = body.get("max_tokens", 64)
    tokens_in = max(1, len(prompt.split()))
    tokens_out = min(max_tokens, max(8, tokens_in // 2))
    text = f"[stub-inference:{TIER_NAME}] canned response, real weights land in M2. prompt={prompt[:80]}"
    return {
        "id": f"stub-{int(time.time() * 1000)}",
        "object": "chat.completion",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": tokens_in, "completion_tokens": tokens_out, "total_tokens": tokens_in + tokens_out},
    }
