"""
Rule Library — PDF Section 27.

"Repo 3 và Repo 4 đều phải kiểm tra Rule Library trước khi tạo nội dung."
This is the constraint layer that keeps the world internally consistent
(e.g. "Planet_A không có tuyết.", "Species_B không có sừng.",
"MC nữ không mặc giáp hạng nặng.").

Kept intentionally simple/declarative: Python validates against these
records, the LLM does not interpret free-form rule prose.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class RuleScope(str, Enum):
    PLANET = "planet"
    SPECIES = "species"
    CHARACTER = "character"
    MC = "mc"
    GLOBAL = "global"


class RuleType(str, Enum):
    FORBIDDEN = "forbidden"    # e.g. "Planet_A không có tuyết"
    REQUIRED = "required"      # e.g. "Species_C luôn có đuôi"
    IMMUTABLE = "immutable"    # e.g. "MC nam không đổi kiểu tóc"


@dataclass
class Rule:
    """One entry in the Rule Library (Section 27)."""
    rule_id: str
    scope: RuleScope
    rule_type: RuleType
    target_id: Optional[str] = None   # e.g. a planet_id / species_id / character_id
    attribute: Optional[str] = None   # e.g. "snow", "horn", "hairstyle", "heavy_armor"
    description: Optional[str] = None # human-readable rule text, Vietnamese or English


@dataclass
class RuleLibrary:
    """Full collection of Rule Library entries.

    Convenience wrapper only (no query logic); Repo 3/Repo 4 validation
    code lives outside the schema layer.
    """
    rules: List[Rule] = field(default_factory=list)
