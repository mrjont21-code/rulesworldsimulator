"""
Architecture Library — PDF Section 20.

Covers houses, castles, temples, towers, plazas, cities, bridges, gates.
Linked from Planet.architecture_id and Species.architecture_id, and used by
Repo 4's Environment Consistency rule (Section 67): every slide on the same
planet must reuse the same architecture blueprint.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Architecture:
    """One entry in the Architecture Library (Section 20)."""
    architecture_id: str
    style: Optional[str] = None
    material: Optional[str] = None
    shape: Optional[str] = None
    roof: Optional[str] = None
    decoration: Optional[str] = None
    color: Optional[str] = None

    earth_analog: Optional[str] = None  # design-pattern inspiration only, no plot/lore copy

    visual_prompt_keywords: List[str] = field(default_factory=list)
