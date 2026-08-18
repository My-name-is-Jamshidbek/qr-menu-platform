"""Upload validation and WebP derivative generation.

Uploads are validated by decoding them with Pillow rather than by trusting the file
extension, and every stored variant is WebP at a fixed set of widths so the frontend
can ship a `srcset` and reserve layout space before the bytes arrive.
"""

from io import BytesIO

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

# Widths the API exposes in `srcset`. Narrow originals are never upscaled, but they
# keep the labelled name so the srcset dict always has the same three keys.
DERIVATIVE_WIDTHS: tuple[int, ...] = (400, 800, 1600)

WEBP_QUALITY = 82

# Pillow refuses absurd pixel counts by default; keep that guard explicit.
MAX_PIXELS = 50_000_000


def validate_upload_size(size: int) -> None:
    """Reject uploads larger than the configured cap."""
    limit = settings.MAX_UPLOAD_SIZE_BYTES
    if size > limit:
        raise ValidationError(
            f"Image is {size} bytes; the limit is {limit} bytes.",
            code="image_too_large",
        )


def open_image(raw: bytes) -> Image.Image:
    """Decode `raw` as an image or raise `ValidationError`.

    Content sniffing, not extension checking: a `.png` full of shell script fails here.
    """
    try:
        probe = Image.open(BytesIO(raw))
        probe.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValidationError("File is not a readable image.", code="invalid_image") from exc

    # `verify()` leaves the object unusable, so decode again for real work.
    image = Image.open(BytesIO(raw))
    if image.width * image.height > MAX_PIXELS:
        raise ValidationError("Image resolution is too large.", code="image_too_large")
    return ImageOps.exif_transpose(image) or image


def derivative_name(base_key: str, width: int) -> str:
    """Storage key of one WebP variant, e.g. `products/2026/08/abc` + 800."""
    return f"{base_key}-{width}.webp"


def to_webp(image: Image.Image, width: int) -> ContentFile:
    """Resize (never upscale) and encode a single WebP variant."""
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA" if "A" in image.getbands() else "RGB")

    target_width = min(width, image.width)
    target_height = max(1, round(image.height * target_width / image.width))
    resized = image.resize((target_width, target_height), Image.Resampling.LANCZOS)

    buffer = BytesIO()
    resized.save(buffer, format="WEBP", quality=WEBP_QUALITY, method=6)
    return ContentFile(buffer.getvalue())


def build_derivatives(image: Image.Image) -> dict[int, ContentFile]:
    """One WebP `ContentFile` per configured width."""
    return {width: to_webp(image, width) for width in DERIVATIVE_WIDTHS}
