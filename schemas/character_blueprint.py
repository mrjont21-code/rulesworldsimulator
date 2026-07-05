"""
Character Blueprint Library — PDF Section 26.

"Mỗi Blueprint mô tả đầy đủ DNA hình ảnh của một nhân vật... Prompt hình ảnh
sau này chỉ việc ghép các ID thay vì để AI sáng tạo lại khuôn mặt ở mỗi tập."

This is the Character Consistency contract for Repo 4 (Section 66): every
field below is an ID pointer into another library/table, not free text —
so a character's face/body never drifts between episodes.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CharacterBlueprint:
    """One entry in the Character Blueprint Library (Section 26).

    Every *_id field is a pointer into its respective sub-part library
    (head/hair/eye/etc. shape tables). This schema does not define those
    sub-libraries — only the DNA record that references them, per the PDF.
    """
    blueprint_id: str
    character_id: Optional[str] = None  # link back to the character record

    head_id: Optional[str] = None
    hair_id: Optional[str] = None
    eye_id: Optional[str] = None
    nose_id: Optional[str] = None
    mouth_id: Optional[str] = None
    ear_id: Optional[str] = None
    horn_id: Optional[str] = None
    tail_id: Optional[str] = None
    body_id: Optional[str] = None
    skin_id: Optional[str] = None
    clothes_id: Optional[str] = None       # -> Costume.costume_id
    accessory_id: Optional[str] = None
    color_palette_id: Optional[str] = None

    # Derived/cached, not authored freehand: assembled by concatenating
    # the *_id lookups above, per Section 26/65 ("Prompt cuối cùng chỉ là
    # kết quả ghép các thành phần này").
    visual_prompt_keywords: List[str] = field(default_factory=list)
