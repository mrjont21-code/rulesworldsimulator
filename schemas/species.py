"""
Species Library — PDF Section 17.

"Đây là thư viện quyết định tính nhất quán của toàn bộ hình ảnh."
Repo 4 reads only Species_ID to generate a consistent prompt — so every
visual-relevant field here must ultimately resolve into
`visual_prompt_keywords` / `negative_prompt`.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Morphology:
    """Body-plan fields from Section 17 (height/weight/body parts)."""
    height: Optional[str] = None
    weight: Optional[str] = None
    body_ratio: Optional[str] = None
    skin_color: Optional[str] = None
    eye_color: Optional[str] = None
    hair: Optional[str] = None
    ear: Optional[str] = None
    horn: Optional[str] = None
    tail: Optional[str] = None
    hand: Optional[str] = None
    foot: Optional[str] = None
    face: Optional[str] = None
    expression: Optional[str] = None


@dataclass
class Species:
    """One entry in the Species Library (Section 17)."""
    species_id: str
    name: str
    inspiration: Optional[str] = None  # design-pattern source, NOT copied plot/lore

    morphology: Optional[Morphology] = None

    clothing: Optional[str] = None
    jewelry: Optional[str] = None
    technology: Optional[str] = None
    profession: Optional[str] = None      # default/typical; Repo 3 may override per-character
    culture_id: Optional[str] = None      # -> Culture.culture_id
    architecture_id: Optional[str] = None # -> Architecture.architecture_id

    visual_prompt_keywords: List[str] = field(default_factory=list)
    negative_prompt: List[str] = field(default_factory=list)
