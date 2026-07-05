"""
Costume Library — PDF Section 21.

Includes explicit compatibility fields so Repo 3/Repo 4 can validate an
outfit against the Rule Library (e.g. "MC nữ không mặc giáp hạng nặng")
without the LLM having to reason about it freeform.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Costume:
    """One entry in the Costume Library (Section 21)."""
    costume_id: str
    material: Optional[str] = None
    color: Optional[str] = None
    style: Optional[str] = None

    planet_compatibility: List[str] = field(default_factory=list)   # Planet.planet_id list
    species_compatibility: List[str] = field(default_factory=list)  # Species.species_id list

    visual_prompt_keywords: List[str] = field(default_factory=list)
