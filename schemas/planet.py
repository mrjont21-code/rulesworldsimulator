"""
Planet Library — PDF Section 16.

Rule from source doc: "LLM không được tự tạo hành tinh mới. Nếu thiếu dữ liệu,
chỉ được phép điền vào các trường còn trống dựa trên Planet Template."
=> Planet is a closed template. LLM fills blanks only; it never creates a
new Planet_ID at runtime.

Each planet is fixed-mapped to one real Vietnamese province/city (Section 32/33),
which is why `earth_analog` is mandatory here: it is the literal Reality Data
join key Repo 2 / World Engine use to translate real weather into planet skin.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class EarthAnalog:
    """The real-world reference this planet is a 'skin' for.

    Per Section 32: each planet <-> a fixed Vietnamese province/city.
    Weather/disaster data from Repo 2 is joined to the planet via this key.
    """
    province_or_city: str            # e.g. "Hà Nội", "Đà Nẵng", "TP. Hồ Chí Minh"
    country: str = "Việt Nam"
    weather_station_ref: Optional[str] = None  # optional external station/API id


@dataclass
class PhysicsAttributes:
    """Physical constants of the planet (Section 16 fields)."""
    gravity: Optional[str] = None            # e.g. "0.9g"
    temperature_range: Optional[str] = None  # e.g. "-5°C to 40°C"
    atmosphere: Optional[str] = None         # e.g. "Nitrogen-Oxygen, thin"
    sun_type: Optional[str] = None
    moon_count: Optional[int] = None


@dataclass
class Planet:
    """One entry in the Planet Library (Section 16).

    Fields map 1:1 to the PDF's field list. Optional fields represent
    "còn trống" (blank) slots an LLM is allowed to complete — never
    fields it's allowed to invent wholesale.
    """
    planet_id: str
    name: str
    planet_type: Optional[str] = None
    climate: Optional[str] = None
    sky_color: Optional[str] = None
    ocean_color: Optional[str] = None
    soil_color: Optional[str] = None
    terrain: Optional[str] = None
    water: Optional[str] = None
    resource: Optional[str] = None
    biome: Optional[str] = None
    dominant_species_id: Optional[str] = None   # -> Species.species_id
    technology_level: Optional[str] = None
    culture_id: Optional[str] = None            # -> Culture.culture_id
    architecture_id: Optional[str] = None       # -> Architecture.architecture_id

    earth_analog: Optional[EarthAnalog] = None
    physics_attributes: Optional[PhysicsAttributes] = None

    visual_prompt_keywords: List[str] = field(default_factory=list)
