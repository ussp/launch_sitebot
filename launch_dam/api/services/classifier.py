"""Asset classification logic."""

import re

# Patterns that indicate location/date-specific (inspiration only)
LOCATION_PATTERNS = [
    "brooklyn",
    "annarbor",
    "ann_arbor",
    "westhouston",
    "west_houston",
    "warwick",
    "lewisville",
    "clearwater",
    "northattleboro",
    "north_attleboro",
    "edison",
    "springfield",
    "richmond",
    "trumbull",
    "norwalk",
    "freehold",
    "woodbridge",
    "deptford",
    "whitemarsh",
    "plymouth",
    "norristown",
]

DATE_PATTERNS = [
    r"\d{4}",  # Year: 2024, 2025, 2026
    r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\d{4}",
    r"_\d{2}_\d{2}_",  # Date formats
    r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}",  # Various date formats
]

EVENT_SPECIFIC = [
    "grandopening",
    "grand_opening",
    "mlkday",
    "mlk_day",
    "presidentsday",
    "presidents_day",
    "stpatricks",
    "st_patricks",
    "eid",
    "blackfriday",
    "black_friday",
    "newyears",
    "new_years",
    "laborday",
    "labor_day",
    "memorialday",
    "memorial_day",
    "4thofjuly",
    "july4th",
    "thanksgiving",
    "christmas",
    "halloween",
    "easter",
    "valentines",
]

# Patterns that indicate reusable templates
REUSABLE_ALBUMS = ["Brand Kit", "Templates", "Social Media Templates", "Marketing Templates"]
REUSABLE_PATTERNS = ["template", "flyer", "generic", "base", "blank", "editable"]


def classify_asset(filename: str, album_path: str | None = None) -> str:
    """
    Classify an asset as 'template' (reusable) or 'inspiration' (reference only).

    Args:
        filename: The asset filename
        album_path: Optional album path the asset belongs to

    Returns:
        'template' if the asset is reusable, 'inspiration' otherwise
    """
    name_lower = filename.lower().replace(" ", "").replace("-", "").replace("_", "")
    album_lower = (album_path or "").lower()

    # Check if in reusable album
    if any(album.lower() in album_lower for album in REUSABLE_ALBUMS):
        return "template"

    # Check for reusable patterns in filename
    if any(pat in name_lower for pat in REUSABLE_PATTERNS):
        return "template"

    # Check for location patterns (indicates location-specific)
    if any(loc in name_lower for loc in LOCATION_PATTERNS):
        return "inspiration"

    # Check for date patterns
    if any(re.search(pat, name_lower, re.IGNORECASE) for pat in DATE_PATTERNS):
        return "inspiration"

    # Check for event-specific patterns
    if any(event in name_lower for event in EVENT_SPECIFIC):
        return "inspiration"

    # Default: inspiration (safer default - requires explicit marking as template)
    return "inspiration"


def infer_media_type(content_type: str | None, filename: str | None = None) -> str:
    """
    Infer media type from content type or filename.

    Returns: 'image', 'video', 'document', or 'other'
    """
    if content_type:
        if content_type.startswith("image/"):
            return "image"
        if content_type.startswith("video/"):
            return "video"
        if content_type in (
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ):
            return "document"

    if filename:
        ext = filename.lower().split(".")[-1] if "." in filename else ""
        if ext in ("jpg", "jpeg", "png", "gif", "webp", "svg", "eps", "ai", "psd", "tiff", "bmp"):
            return "image"
        if ext in ("mp4", "mov", "avi", "webm", "mkv", "m4v"):
            return "video"
        if ext in ("pdf", "doc", "docx", "txt", "rtf"):
            return "document"

    return "other"


def extract_album_name(album_path: str | None) -> str | None:
    """Extract the album name from a full album path."""
    if not album_path:
        return None
    # Album path is typically like "Root/Category/Album Name"
    parts = album_path.split("/")
    return parts[-1].strip() if parts else None
