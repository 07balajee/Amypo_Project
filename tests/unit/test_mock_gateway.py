import pytest

from app.core.inference.mock import MockGateway


@pytest.mark.asyncio
async def test_generate_is_deterministic():
    gw = MockGateway()
    r1 = await gw.generate("local", [{"role": "user", "content": "hello world"}], 64)
    r2 = await gw.generate("local", [{"role": "user", "content": "hello world"}], 64)
    assert r1.text == r2.text
    assert r1.tokens_in == r2.tokens_in == 2
    assert r1.tokens_out > 0
    assert r1.latency_ms > 0


@pytest.mark.asyncio
async def test_fail_tiers_raise():
    gw = MockGateway(fail_tiers={"remote"})
    with pytest.raises(ConnectionError):
        await gw.generate("remote", [{"role": "user", "content": "x"}], 16)
    assert await gw.health("remote") is False
    assert await gw.health("local") is True


@pytest.mark.asyncio
async def test_max_tokens_caps_output():
    gw = MockGateway()
    long_prompt = " ".join(["word"] * 200)
    result = await gw.generate("local", [{"role": "user", "content": long_prompt}], 10)
    assert result.tokens_out <= 10
