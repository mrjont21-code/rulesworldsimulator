"""
core/adapters/tier1_http.py — Tier 1: httpx + stealth headers
==============================================================
Adapter rẻ nhất. Di chuyển từ t2_scrape.py::scrape_url() phần fetch thông thường.
Output: HTML thô (str) hoặc None nếu fail.
"""
from __future__ import annotations
import logging
from typing import Optional
import httpx
import stealth

logger = logging.getLogger(__name__)


async def fetch(url: str, obs=None) -> Optional[str]:
    """Fetch URL bằng httpx + stealth headers. Trả HTML thô hoặc None."""
    try:
        _, headers = stealth.get_stealth_headers()
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(url, headers=headers, timeout=20.0)
            resp.raise_for_status()
            return resp.text
    except Exception as e:
        logger.warning(f"[tier1_http] Lỗi fetch '{url}': {e}")
        return None
