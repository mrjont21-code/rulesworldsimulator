"""
World Simulator Pipeline — Fiction Knowledge Base Schemas
===========================================================
Repo 1 output contract (PDF sections 16–27).

These are SCHEMA-ONLY definitions. No scraping logic, no DB clients,
no business logic. Pure data shape so that:
  - Repo 1 knows what to write into MongoDB #1.
  - Repo 3 / Repo 4 know what to read.
  - LLMs only fill blank fields on an existing template; they never
    invent new top-level entities (see rule.py / RuleLibrary).

Common structural convention across all libraries, where applicable:
  - earth_analog          -> real-world reference point (mapping "skin")
  - physics_attributes    -> gravity / climate / radiation-like physical facts
  - morphology            -> body-plan / physical structure of a lifeform
  - visual_prompt_keywords -> ready-to-concatenate string tokens for Repo 4
"""

from .planet import Planet, EarthAnalog, PhysicsAttributes
from .species import Species, Morphology
from .creature import Creature
from .flora import Flora
from .architecture import Architecture
from .costume import Costume
from .technology import Technology
from .culture import Culture
from .occupation import Occupation
from .visual_style import VisualStyle
from .character_blueprint import CharacterBlueprint
from .rule import Rule, RuleLibrary, RuleScope, RuleType

__all__ = [
    "Planet",
    "EarthAnalog",
    "PhysicsAttributes",
    "Species",
    "Morphology",
    "Creature",
    "Flora",
    "Architecture",
    "Costume",
    "Technology",
    "Culture",
    "Occupation",
    "VisualStyle",
    "CharacterBlueprint",
    "Rule",
    "RuleLibrary",
    "RuleScope",
    "RuleType",
]
