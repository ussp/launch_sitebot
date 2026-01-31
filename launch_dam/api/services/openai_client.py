"""OpenAI client for embeddings and vision analysis."""

import json
import os
from typing import Any

from openai import AsyncOpenAI

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
VISION_MODEL = "gpt-4o"


class OpenAIService:
    """Service for OpenAI API interactions."""

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        self.client = AsyncOpenAI(api_key=api_key)

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for text using text-embedding-3-small."""
        response = await self.client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text,
            dimensions=EMBEDDING_DIMENSIONS,
        )
        return response.data[0].embedding

    async def generate_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts in one API call."""
        response = await self.client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=texts,
            dimensions=EMBEDDING_DIMENSIONS,
        )
        return [item.embedding for item in response.data]

    async def analyze_image(
        self, image_url: str | None = None, image_base64: str | None = None, is_video: bool = False
    ) -> dict[str, Any]:
        """Analyze an image using GPT-4o Vision and return structured metadata.

        Args:
            image_url: Public URL to the image (OpenAI will fetch it)
            image_base64: Base64-encoded image data (for private/inaccessible URLs)
            is_video: Whether this is a video thumbnail
        """
        media_type = "video thumbnail" if is_video else "image"

        # Build image content - prefer base64 if provided (works for private URLs)
        if image_base64:
            image_content = {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
            }
        elif image_url:
            image_content = {"type": "image_url", "image_url": {"url": image_url}}
        else:
            raise ValueError("Either image_url or image_base64 must be provided")

        response = await self.client.chat.completions.create(
            model=VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self._get_extraction_prompt(media_type)},
                        image_content,
                    ],
                }
            ],
            response_format={"type": "json_object"},
            max_tokens=4096,
        )

        return json.loads(response.choices[0].message.content)

    def _get_extraction_prompt(self, media_type: str) -> str:
        """Get the vision extraction prompt."""
        return f"""Analyze this {media_type} for a digital asset management system for Launch Family Entertainment (a trampoline park / family entertainment center). Extract ALL of the following in JSON format:

{{
  "scene": {{
    "setting": "trampoline_park | party_room | arcade | restaurant | bar | lobby | exterior | studio | abstract",
    "setting_details": "<specific description>",
    "lighting": "bright | dim | natural | neon | mixed",
    "time_of_day": "day | night | indoor_neutral"
  }},
  "people": {{
    "count": <int>,
    "count_category": "none | individual | small_group | crowd",
    "age_groups": ["kids", "teens", "adults", "families", "seniors"],
    "primary_age": "<most prominent>",
    "activities": ["jumping", "flipping", "celebrating", "eating", "posing", "playing_games"],
    "emotions": ["excited", "happy", "surprised", "focused"],
    "facing_camera": <bool>,
    "identifiable_faces": <bool>
  }},
  "objects": {{
    "equipment": ["trampolines", "foam_pit", "ninja_course", "arcade_machines", "bowling_lanes"],
    "food_drink": ["pizza", "cake", "drinks"],
    "props": ["balloons", "party_hats", "presents"],
    "brand_items": ["joey_mascot", "launch_signage", "branded_socks"]
  }},
  "text_content": {{
    "headline": "<main text or null>",
    "subheadline": "<secondary text or null>",
    "cta": "<call to action or null>",
    "prices": ["<any prices shown>"],
    "dates": ["<any dates shown>"],
    "times": ["<any times shown>"],
    "locations": ["<any locations/addresses>"],
    "phone_numbers": [],
    "urls": [],
    "promo_codes": [],
    "legal_text": "<fine print or null>"
  }},
  "hardcoded_elements": {{
    "has_date": <bool>,
    "has_location": <bool>,
    "has_price": <bool>,
    "has_promo_code": <bool>,
    "has_phone": <bool>,
    "reusability_score": <1-5>,
    "reusability_notes": "<why this score>"
  }},
  "composition": {{
    "focal_point": "center | left | right | top | bottom | distributed",
    "focal_point_description": "<what's the focus>",
    "negative_space": {{
      "available": <bool>,
      "positions": ["top_left", "bottom", ...],
      "suitable_for_text_overlay": <bool>
    }},
    "depth": "shallow | medium | deep",
    "clutter_level": "minimal | moderate | busy"
  }},
  "framing": {{
    "shot_type": "wide | medium | close_up | extreme_close_up | aerial",
    "angle": "eye_level | low_angle | high_angle | birds_eye | dutch",
    "orientation": "landscape | portrait | square"
  }},
  "edges": {{
    "clean_edges": <bool>,
    "busy_edges": ["<sides with complex edges>"],
    "transparency": <bool>,
    "vignette": <bool>
  }},
  "colors": {{
    "dominant": ["#hex1", "#hex2"],
    "palette_type": "brand_primary | brand_secondary | rainbow | neutral | warm | cool",
    "on_brand": <bool>,
    "saturation": "vibrant | muted | desaturated",
    "contrast": "high | medium | low"
  }},
  "style": {{
    "type": "photography | graphic_design | illustration | 3d_render | mixed",
    "photo_style": "candid | posed | action_shot | lifestyle | product",
    "design_style": "modern | playful | corporate | retro | minimalist",
    "filter_applied": "none | warm | cool | vintage | high_contrast"
  }},
  "quality": {{
    "sharpness": "sharp | slightly_soft | blurry",
    "noise_level": "clean | some_grain | noisy",
    "professional_grade": <bool>
  }},
  "brand": {{
    "logo_present": <bool>,
    "logo_version": "full_color | one_color_white | one_color_black | icon_only | none",
    "logo_placement": "top_left | top_right | bottom_center | watermark | none",
    "joey_mascot": <bool>,
    "correct_fonts": <bool>,
    "brand_colors_used": <bool>,
    "brand_compliance_score": <1-5>,
    "compliance_notes": "<notes>"
  }},
  "sub_brand": "launch | krave | barhops | none",
  "mood": {{
    "primary": "energetic | celebratory | fun | calm | exciting | welcoming | professional",
    "energy_level": <1-10>,
    "emotions_evoked": ["excitement", "joy", "nostalgia", "urgency"],
    "suitable_for": ["upbeat_promo", "brand_awareness", "party_booking", "corporate", "kids_focused", "family_focused"]
  }},
  "tone": {{
    "formality": "casual | balanced | formal",
    "urgency": "none | subtle | strong",
    "target_audience": ["families", "kids", "teens", "young_adults", "corporate"]
  }},
  "editorial": {{
    "suggested_use": ["hero_shot", "b_roll", "background", "transition", "end_card", "thumbnail", "overlay_graphic"],
    "pairs_well_with": ["upbeat_music", "voiceover", "kinetic_text", "other_action_shots"],
    "story_position": "opener | middle | climax | closer",
    "standalone_capable": <bool>,
    "needs_context": <bool>
  }},
  "editing_notes": {{
    "cropping_flexibility": "high | medium | low",
    "zoom_potential": <bool>,
    "pan_potential": <bool>,
    "text_overlay_zones": ["top", "bottom_left"],
    "avoid_cropping": ["logo", "faces"]
  }},
  "auto_tags": ["<searchable tags - be comprehensive>"],
  "semantic_description": "<natural language description for search - be detailed and specific>",
  "search_queries": ["<queries this would match - think like a marketer searching>"]
}}

Be thorough and accurate. For Launch-specific items:
- Launch's brand colors are green (#5CBA47), yellow (#F4E501), and rainbow secondary colors
- Their mascot is Joey the Kangaroo
- Sub-brands include Krave (restaurant) and BarHops (bar)
- They are a family entertainment center with trampolines, arcade, parties
"""


def build_search_text(asset: dict) -> str:
    """Combine all searchable fields into one text blob for embedding."""
    parts = []

    # Filename cleaned
    filename = asset.get("filename", "")
    parts.append(filename.replace("_", " ").replace("-", " ").replace(".", " "))

    # Album info
    parts.append(asset.get("album_name") or "")
    parts.append(asset.get("album_path") or "")

    # Vision semantic description (most important!)
    parts.append(asset.get("semantic_description") or "")

    # Scene & setting
    scene = asset.get("scene") or {}
    parts.append(scene.get("setting_details") or "")
    parts.append(scene.get("setting") or "")

    # People & activities
    people = asset.get("people") or {}
    parts.extend(people.get("activities") or [])
    parts.extend(people.get("emotions") or [])
    parts.extend(people.get("age_groups") or [])

    # Objects
    objects = asset.get("objects") or {}
    parts.extend(objects.get("equipment") or [])
    parts.extend(objects.get("props") or [])
    parts.extend(objects.get("food_drink") or [])
    parts.extend(objects.get("brand_items") or [])

    # Mood
    mood = asset.get("mood") or {}
    parts.append(mood.get("primary") or "")
    parts.extend(mood.get("suitable_for") or [])
    parts.extend(mood.get("emotions_evoked") or [])

    # Editorial
    editorial = asset.get("editorial") or {}
    parts.extend(editorial.get("suggested_use") or [])

    # Auto-generated tags
    parts.extend(asset.get("auto_tags") or [])

    # Search queries (what this would match)
    parts.extend(asset.get("search_queries") or [])

    # Source tags from Canto
    parts.extend(asset.get("source_tags") or [])
    parts.extend(asset.get("source_keywords") or [])

    # Filter out empty strings and join
    return " ".join(filter(None, parts))
