from __future__ import annotations

import re
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path

from packages.python.common.errors import ValidationError

_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")


def safe_filename(value: str, fallback: str) -> str:
    """Normalize an untrusted display/download filename."""

    name = Path(value).name.strip().replace("\x00", "")
    sanitized = _SAFE_FILENAME.sub("-", name).strip(".-")
    return (sanitized or fallback)[:255]


@dataclass(frozen=True, slots=True)
class ValidatedUpload:
    content: bytes
    media_type: str
    extension: str
    width: int | None = None
    height: int | None = None
    duration_seconds: int | None = None
    page_count: int | None = None


_IMAGE_SIGNATURES: dict[str, tuple[bytes, str]] = {
    "image/jpeg": (b"\xff\xd8\xff", ".jpg"),
    "image/png": (b"\x89PNG\r\n\x1a\n", ".png"),
    "image/webp": (b"RIFF", ".webp"),
    "image/avif": (b"", ".avif"),
}


def _is_webp(content: bytes) -> bool:
    return len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP"


def _is_avif(content: bytes) -> bool:
    return (
        len(content) >= 12
        and content[4:8] == b"ftyp"
        and content[8:12]
        in {
            b"avif",
            b"avis",
        }
    )


def _image_dimensions(content: bytes, media_type: str) -> tuple[int, int] | None:
    if media_type == "image/png" and len(content) >= 24 and content[12:16] == b"IHDR":
        return struct.unpack(">II", content[16:24])
    if media_type == "image/jpeg":
        offset = 2
        while offset + 9 <= len(content):
            if content[offset] != 0xFF:
                offset += 1
                continue
            marker = content[offset + 1]
            offset += 2
            if marker in {0xD8, 0xD9}:
                continue
            if offset + 2 > len(content):
                break
            length = int.from_bytes(content[offset : offset + 2], "big")
            if length < 2 or offset + length > len(content):
                break
            if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB}:
                height = int.from_bytes(content[offset + 3 : offset + 5], "big")
                width = int.from_bytes(content[offset + 5 : offset + 7], "big")
                return width, height
            offset += length
    if media_type == "image/webp" and len(content) >= 30:
        kind = content[12:16]
        if kind == b"VP8X":
            return (
                int.from_bytes(content[24:27], "little") + 1,
                int.from_bytes(content[27:30], "little") + 1,
            )
        if kind == b"VP8L" and len(content) >= 25:
            bits = int.from_bytes(content[21:25], "little")
            return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
        frame = content.find(b"\x9d\x01\x2a")
        if frame >= 0 and frame + 7 <= len(content):
            return (
                int.from_bytes(content[frame + 3 : frame + 5], "little") & 0x3FFF,
                int.from_bytes(content[frame + 5 : frame + 7], "little") & 0x3FFF,
            )
    if media_type == "image/avif":
        marker = content.find(b"ispe")
        if marker >= 4 and marker + 16 <= len(content):
            return struct.unpack(">II", content[marker + 8 : marker + 16])
    return None


def _image_container_is_complete(content: bytes, media_type: str) -> bool:
    """Validate the bounded container structure needed for trustworthy metadata."""

    if media_type == "image/png":
        offset = 8
        saw_header = False
        while offset + 12 <= len(content):
            length = int.from_bytes(content[offset : offset + 4], "big")
            kind = content[offset + 4 : offset + 8]
            end = offset + 12 + length
            if end > len(content):
                return False
            payload = content[offset + 8 : offset + 8 + length]
            checksum = int.from_bytes(content[offset + 8 + length : end], "big")
            if zlib.crc32(kind + payload) & 0xFFFFFFFF != checksum:
                return False
            if kind == b"IHDR":
                if saw_header or length != 13 or offset != 8:
                    return False
                saw_header = True
            if kind == b"IEND":
                return saw_header and length == 0 and end == len(content)
            offset = end
        return False
    if media_type == "image/jpeg":
        return content.endswith(b"\xff\xd9")
    if media_type == "image/webp":
        return len(content) >= 20 and int.from_bytes(content[4:8], "little") + 8 == len(content)
    if media_type == "image/avif":
        return b"meta" in content and b"ispe" in content and b"mdat" in content
    return False


def _mp4_metadata(content: bytes) -> tuple[int | None, int | None, int | None]:
    duration: int | None = None
    marker = content.find(b"mvhd")
    if marker >= 4:
        version = content[marker + 4] if marker + 5 <= len(content) else 0
        time_offset = marker + (24 if version == 1 else 16)
        duration_offset = marker + (28 if version == 1 else 20)
        duration_size = 8 if version == 1 else 4
        if duration_offset + duration_size <= len(content):
            timescale = int.from_bytes(content[time_offset : time_offset + 4], "big")
            units = int.from_bytes(
                content[duration_offset : duration_offset + duration_size], "big"
            )
            if timescale > 0:
                duration = max(0, round(units / timescale))
    width: int | None = None
    height: int | None = None
    marker = content.find(b"tkhd")
    if marker >= 4:
        box_start = marker - 4
        size = int.from_bytes(content[box_start:marker], "big")
        box_end = box_start + size
        if size >= 16 and box_end <= len(content):
            width = int.from_bytes(content[box_end - 8 : box_end - 4], "big") >> 16
            height = int.from_bytes(content[box_end - 4 : box_end], "big") >> 16
    return width or None, height or None, duration


def _ebml_value(content: bytes, marker: bytes) -> bytes | None:
    offset = content.find(marker)
    if offset < 0 or offset + len(marker) >= len(content):
        return None
    offset += len(marker)
    first = content[offset]
    mask = 0x80
    length = 1
    while length <= 8 and not first & mask:
        mask >>= 1
        length += 1
    if length > 8 or offset + length > len(content):
        return None
    size = first & (mask - 1)
    for value in content[offset + 1 : offset + length]:
        size = (size << 8) | value
    start = offset + length
    return content[start : start + size] if start + size <= len(content) else None


def _webm_duration(content: bytes) -> int | None:
    scale_raw = _ebml_value(content, b"\x2a\xd7\xb1")
    duration_raw = _ebml_value(content, b"\x44\x89")
    if not duration_raw or len(duration_raw) not in {4, 8}:
        return None
    scale = int.from_bytes(scale_raw, "big") if scale_raw else 1_000_000
    duration = float(struct.unpack(">f" if len(duration_raw) == 4 else ">d", duration_raw)[0])
    if duration < 0 or not duration < float("inf"):
        return None
    return round(duration * scale / 1_000_000_000)


def _webm_dimensions(content: bytes) -> tuple[int | None, int | None]:
    width_raw = _ebml_value(content, b"\xb0")
    height_raw = _ebml_value(content, b"\xba")
    width = int.from_bytes(width_raw, "big") if width_raw else None
    height = int.from_bytes(height_raw, "big") if height_raw else None
    return width or None, height or None


def _pdf_page_count(content: bytes) -> int | None:
    pages = re.findall(rb"/Type\s*/Page(?!s)\b", content)
    return len(pages) or None


def validate_declared_metadata(
    upload: ValidatedUpload,
    *,
    width: int | None,
    height: int | None,
    duration_seconds: int | None,
) -> None:
    """Reject client metadata that conflicts with bytes; bytes remain authoritative."""

    for label, declared, actual in (
        ("width", width, upload.width),
        ("height", height, upload.height),
        ("duration_seconds", duration_seconds, upload.duration_seconds),
    ):
        if declared is not None and actual is not None and declared != actual:
            raise ValidationError(f"Declared {label} does not match the uploaded media.")


def validate_image(content: bytes, declared_type: str | None, max_bytes: int) -> ValidatedUpload:
    if not content:
        raise ValidationError("Uploaded image is empty.")
    if len(content) > max_bytes:
        raise ValidationError("Uploaded image exceeds the configured size limit.")
    media_type = (declared_type or "").lower().split(";", 1)[0]
    if media_type not in _IMAGE_SIGNATURES:
        raise ValidationError("Only JPEG, PNG, WebP, and AVIF images are allowed.")
    if media_type == "image/webp":
        valid = _is_webp(content)
    elif media_type == "image/avif":
        valid = _is_avif(content)
    else:
        valid = content.startswith(_IMAGE_SIGNATURES[media_type][0])
    if not valid:
        raise ValidationError("The uploaded image content does not match its media type.")
    dimensions = _image_dimensions(content, media_type)
    if (
        dimensions is None
        or dimensions[0] <= 0
        or dimensions[1] <= 0
        or dimensions[0] > 50_000
        or dimensions[1] > 50_000
        or not _image_container_is_complete(content, media_type)
    ):
        raise ValidationError("The uploaded image has invalid or unreadable dimensions.")
    return ValidatedUpload(
        content,
        media_type,
        _IMAGE_SIGNATURES[media_type][1],
        width=dimensions[0],
        height=dimensions[1],
    )


def validate_pdf(content: bytes, declared_type: str | None, max_bytes: int) -> ValidatedUpload:
    if not content:
        raise ValidationError("Uploaded résumé is empty.")
    if len(content) > max_bytes:
        raise ValidationError("Uploaded résumé exceeds the configured size limit.")
    media_type = (declared_type or "").lower().split(";", 1)[0]
    if media_type != "application/pdf" or not content.startswith(b"%PDF-"):
        raise ValidationError("Résumé versions must be valid PDF files.")
    if b"%%EOF" not in content[-2048:]:
        raise ValidationError("The uploaded PDF is incomplete or invalid.")
    return ValidatedUpload(content, media_type, ".pdf", page_count=_pdf_page_count(content))


def validate_generic_media(
    content: bytes, declared_type: str | None, max_bytes: int
) -> ValidatedUpload:
    media_type = (declared_type or "").lower().split(";", 1)[0]
    if media_type.startswith("image/"):
        return validate_image(content, media_type, max_bytes)
    if media_type == "application/pdf":
        return validate_pdf(content, media_type, max_bytes)
    if not content:
        raise ValidationError("Uploaded media is empty.")
    if len(content) > max_bytes:
        raise ValidationError("Uploaded media exceeds the configured size limit.")
    if media_type == "video/mp4" and len(content) >= 12 and content[4:8] == b"ftyp":
        width, height, duration = _mp4_metadata(content)
        if not width or not height or duration is None or duration <= 0:
            raise ValidationError("The uploaded MP4 has invalid or unreadable metadata.")
        return ValidatedUpload(
            content, media_type, ".mp4", width=width, height=height, duration_seconds=duration
        )
    if media_type == "video/webm" and content.startswith(b"\x1aE\xdf\xa3"):
        width, height = _webm_dimensions(content)
        duration = _webm_duration(content)
        if not width or not height or duration is None or duration <= 0:
            raise ValidationError("The uploaded WebM has invalid or unreadable metadata.")
        return ValidatedUpload(
            content,
            media_type,
            ".webm",
            width=width,
            height=height,
            duration_seconds=duration,
        )
    raise ValidationError("Unsupported or invalid media type.")
