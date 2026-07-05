"""
Creature Library — PDF Section 18.

Covers mounts, animals, monsters, sea creatures, birds, insects, flying
creatures. Not a playable/dominant species (see species.py) — a fauna entry.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Creature:
    """One entry in the Creature Library (Section 18)."""
    creature_id: str
    name: str
    category: Optional[str] = None      # e.g. "mount", "sea_creature", "insect", "flying"
    size: Optional[str] = None
    appearance: Optional[str] = None
    behavior: Optional[str] = None       # "tập tính"
    habitat: Optional[str] = None        # "môi trường sống"

    earth_analog: Optional[str] = None   # optional real-animal design reference

    visual_prompt_keywords: List[str] = field(default_factory=list)
