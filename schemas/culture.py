"""
Culture Library — PDF Section 23.

Covers language, rituals, cuisine, music, festivals, laws, customs.
Linked to planets and species via culture_id.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Culture:
    """One entry in the Culture Library (Section 23)."""
    culture_id: str
    name: Optional[str] = None
    language: Optional[str] = None
    rituals: List[str] = field(default_factory=list)
    cuisine: List[str] = field(default_factory=list)
    music: Optional[str] = None
    festivals: List[str] = field(default_factory=list)
    laws: List[str] = field(default_factory=list)
    customs: List[str] = field(default_factory=list)

    visual_prompt_keywords: List[str] = field(default_factory=list)
