"""BMAM Memory Middleware Python SDK.

Usage::

    from bmam_client import BMAMClient, AsyncBMAMClient

    # Synchronous
    client = BMAMClient("http://localhost:8100")
    client.add(content="I love hiking", user_id="u1")
    results = client.search("outdoor", user_id="u1")

    # Asynchronous
    async_client = AsyncBMAMClient("http://localhost:8100")
    await async_client.add(content="I love hiking", user_id="u1")
"""

from bmam_client.client import BMAMClient
from bmam_client.async_client import AsyncBMAMClient
from bmam_client.exceptions import BMAMError, NotFoundError, AuthError

__all__ = [
    "BMAMClient",
    "AsyncBMAMClient",
    "BMAMError",
    "NotFoundError",
    "AuthError",
]
