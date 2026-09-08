"""Tests for the capped body reader the icon fetches share."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import Mock

from aiohttp import StreamReader
import pytest

from custom_components.mos.utils import async_read_capped_body

if TYPE_CHECKING:
    from collections.abc import Sequence


def _response(chunks: Sequence[bytes]) -> Mock:
    """
    Build a response whose body arrives one chunk at a time.

    Each chunk is fed after the reader has had a chance to run, which is what a
    body spread over several packets looks like from the reader's side.

    Returns:
        A response object exposing only the ``content`` stream.

    """
    stream = StreamReader(Mock(_reading_paused=False), limit=2**16)

    async def feed() -> None:
        for chunk in chunks:
            stream.feed_data(chunk)
            await asyncio.sleep(0)
        stream.feed_eof()

    asyncio.get_running_loop().create_task(feed())
    return Mock(content=stream)


async def test_a_body_split_over_several_chunks_is_read_in_full() -> None:
    """A single read answers with what is buffered, which would cut an icon short."""
    chunks = [b"\x89PNG\r\n\x1a\n", b"middle" * 100, b"IEND"]

    assert await async_read_capped_body(_response(chunks), 100_000) == b"".join(chunks)


async def test_a_body_over_the_limit_is_refused() -> None:
    """The fetch serves a request nobody authenticated, so an oversized body is dropped."""
    assert await async_read_capped_body(_response([b"x" * 64, b"y" * 64]), 100) is None


async def test_an_empty_body_is_not_confused_with_a_refusal() -> None:
    """Nothing to read is an empty answer, not a body too large to serve."""
    assert await async_read_capped_body(_response([]), 100) == b""


@pytest.mark.parametrize("limit", [1, 128])
async def test_a_body_exactly_at_the_limit_is_served(limit: int) -> None:
    """The limit is the largest body accepted, not the first one refused."""
    assert await async_read_capped_body(_response([b"z" * limit]), limit) == b"z" * limit
