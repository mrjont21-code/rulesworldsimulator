"""
Visual Style Library — PDF Section 25.

"Toàn bộ series chỉ sử dụng một phong cách hình ảnh thống nhất."
In practice there is exactly one active VisualStyle per series/run, applied
uniformly across all episodes so every image prompt shares an identity.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class VisualStyle:
    """One entry in the Visual Style Library (Section 25).

    e.g. "3D Stylized", "Semi Realistic", "Anime", "Painterly".
    """
    style_id: str
    name: str                       # e.g. "3D Stylized"
    color_palette: Optional[str] = None
    lighting: Optional[str] = None
    detail_level: Optional[str] = None
    material_rendering: Optional[str] = None   # "chất liệu"
    rendering_technique: Optional[str] = None  # "cách dựng hình"

    visual_prompt_keywords: List[str] = field(default_factory=list)
    negative_prompt: List[str] = field(default_factory=list)
