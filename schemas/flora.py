"""
Flora Library — PDF Section 19.

Covers trees, flowers, fungi, algae/moss, forests, shrubs.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Flora:
    """One entry in the Flora Library (Section 19)."""
    flora_id: str
    name: str
    category: Optional[str] = None   # e.g. "tree", "flower", "fungus", "shrub", "forest"
    color: Optional[str] = None
    size: Optional[str] = None
    shape: Optional[str] = None
    habitat: Optional[str] = None    # "môi trường"

    visual_prompt_keywords: List[str] = field(default_factory=list)
