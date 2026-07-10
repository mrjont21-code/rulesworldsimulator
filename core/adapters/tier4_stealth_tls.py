"""
core/adapters/tier4_stealth_tls.py — Tier 4: curl_cffi (TLS fingerprint impersonation)
========================================================================================
Vượt qua Cloudflare / WAF dựa trên TLS/JA3 fingerprint matching Chrome thật.
Rẻ hơn Playwright (~0.5-2s/call, không cần headless browser).
Được thử TRƯỚC tier3 khi probe trả 403/503.
Output: HTML thô hoặc None.
"""
from __future__ import annotations
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def fetch(url: str, obs=None) -> Optional[str]:
    """Fetch bằng curl_cffi với TLS impersonation Chrome 120."""
    try:
        from curl_cffi.requests import AsyncSession  # lazy import
    except ImportError:
        logger.error("[tier4_stealth_tls] curl_cffi chưa cài — pip install curl_cffi")
        return None

    try:
        async with AsyncSession(impersonate="chrome120") as session:
            resp = await session.get(url, timeout=25)
            if resp.status_code < 400:
                return resp.text
            logger.warning(f"[tier4_stealth_tls] Status {resp.status_code} cho '{url}'")
            return None
    except Exception as e:
        logger.warning(f"[tier4_stealth_tls] Lỗi curl_cffi '{url}': {e}")
        return None
