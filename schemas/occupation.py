"""
Occupation Library — PDF Section 24.

"Repo 3 sẽ random nghề từ thư viện này thay vì để LLM tự nghĩ."
=> This is a closed enumeration Repo 3's Python layer samples from;
the LLM never invents a profession.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Occupation:
    """One entry in the Occupation Library (Section 24)."""
    occupation_id: str
    name: str                      # e.g. "thương nhân", "chiến binh", "kỹ sư"
    description: Optional[str] = None
    compatible_technology_level: Optional[str] = None

    visual_prompt_keywords: List[str] = field(default_factory=list)
