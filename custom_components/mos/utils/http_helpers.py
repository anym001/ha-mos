"""HTTP response helpers for mos."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiohttp

# How much of a body is taken from the stream at a time.
_CHUNK_BYTES = 65536


async def async_read_capped_body(response: aiohttp.ClientResponse, limit: int) -> bytes | None:
    """
    Read a response body in full, refusing it as soon as it passes ``limit``.

    ``StreamReader.read(n)`` answers with whatever is buffered rather than with
    ``n`` bytes, so a body that arrives in more than one chunk has to be
    assembled here; reading it in one call truncates it at the first chunk
    boundary. The limit is still enforced while reading, so an oversized body is
    abandoned rather than held in memory in full.

    Args:
        response: The open response to read.
        limit: The largest body accepted, in bytes.

    Returns:
        The body, or ``None`` when it is larger than ``limit``.

    """
    body = bytearray()
    async for chunk in response.content.iter_chunked(_CHUNK_BYTES):
        body.extend(chunk)
        if len(body) > limit:
            return None
    return bytes(body)
