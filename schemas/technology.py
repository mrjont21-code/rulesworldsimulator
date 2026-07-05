"""
Technology Library — PDF Section 22.

Covers vehicles, robots, ships, spacecraft, machines, tools.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Technology:
    """One entry in the Technology Library (Section 22)."""
    technology_id: str
    category: Optional[str] = None   # e.g. "vehicle", "robot", "spacecraft", "tool"
    energy: Optional[str] = None
    material: Optional[str] = None
    civilization_level: Optional[str] = None

    visual_prompt_keywords: List[str] = field(default_factory=list)
