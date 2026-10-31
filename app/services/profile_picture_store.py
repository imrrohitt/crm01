"""Save an Instagram profile image on disk and return the path the browser can load."""

from pathlib import Path

import httpx

FOLDER = Path(__file__).resolve().parents[2] / "profile_pictures"
PUBLIC_PREFIX = "/profile-pictures"


def save_profile_picture(key: str, url: str) -> str | None:
    """Download url into profile_pictures/{key}.ext. Returns the public path, or None if the download fails."""
    safe = "".join(char if char.isalnum() or char in "-_" else "_" for char in key).strip("_")[:80]
    if not safe or not url.startswith("https://"):
        return None
    try:
        response = httpx.get(url, timeout=20, follow_redirects=True)
    except httpx.HTTPError:
        return None
    if response.status_code >= 400 or not response.content:
        return None
    content_type = (response.headers.get("content-type") or "").split(";", 1)[0].strip().lower()
    extension = { "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif" }.get(content_type, ".jpg")
    FOLDER.mkdir(parents=True, exist_ok=True)
    filename = f"{safe}{extension}"
    (FOLDER / filename).write_bytes(response.content)
    return f"{PUBLIC_PREFIX}/{filename}"
