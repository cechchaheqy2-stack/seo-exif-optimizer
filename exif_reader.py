import os
from typing import Dict, List

from PIL import Image
import piexif
from piexif import helper

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def is_supported_image(file_path: str) -> bool:
    return os.path.splitext(file_path)[1].lower() in SUPPORTED_EXTENSIONS


def _decode_bytes(value):
    if isinstance(value, bytes):
        for encoding in ("utf-8", "utf-16le", "latin-1"):
            try:
                return value.decode(encoding).rstrip("\x00")
            except UnicodeDecodeError:
                continue
        return value.decode("utf-8", errors="replace").rstrip("\x00")
    return value


def _format_gps_coordinate(values, ref):
    if not values:
        return "Not available"

    def rational_to_float(rational):
        if hasattr(rational, "numerator") and hasattr(rational, "denominator"):
            denominator = rational.denominator or 1
            return rational.numerator / denominator
        numerator, denominator = rational
        return numerator / (denominator or 1)

    degrees = rational_to_float(values[0])
    minutes = rational_to_float(values[1])
    seconds = rational_to_float(values[2])
    coordinate = degrees + (minutes / 60.0) + (seconds / 3600.0)

    if ref in (b"S", b"W", "S", "W"):
        coordinate *= -1
    return coordinate


def _empty_exif_dict():
    return {
        "0th": {},
        "Exif": {},
        "GPS": {},
        "Interop": {},
        "1st": {},
        "thumbnail": None,
    }


def _load_jpeg_metadata(file_path: str) -> Dict[str, str]:
    image = Image.open(file_path)
    exif_bytes = image.info.get("exif", b"")
    exif_dict = piexif.load(exif_bytes) if exif_bytes else _empty_exif_dict()

    metadata = {
        "File": os.path.basename(file_path),
        "Format": image.format or "Unknown",
        "Size": f"{image.width} x {image.height}",
        "Camera model": _decode_bytes(exif_dict["0th"].get(piexif.ImageIFD.Model, b"")) or "Not available",
        "Date taken": _decode_bytes(exif_dict["Exif"].get(piexif.ExifIFD.DateTimeOriginal, b"")) or "Not available",
        "Image description": _decode_bytes(exif_dict["0th"].get(piexif.ImageIFD.ImageDescription, b"")) or "Not available",
        "Keywords": "Not available",
        "User comment": "Not available",
        "GPS location": "Not available",
    }

    xp_keywords = exif_dict["0th"].get(piexif.ImageIFD.XPKeywords)
    if xp_keywords:
        metadata["Keywords"] = _decode_bytes(xp_keywords) or "Not available"
    elif metadata["Image description"] != "Not available":
        metadata["Keywords"] = metadata["Image description"]

    user_comment = exif_dict["Exif"].get(piexif.ExifIFD.UserComment)
    if user_comment:
        try:
            metadata["User comment"] = helper.UserComment.load(user_comment)
        except Exception:
            metadata["User comment"] = _decode_bytes(user_comment) or "Not available"

    gps_data = exif_dict.get("GPS", {})
    latitude = _format_gps_coordinate(
        gps_data.get(piexif.GPSIFD.GPSLatitude),
        gps_data.get(piexif.GPSIFD.GPSLatitudeRef),
    )
    longitude = _format_gps_coordinate(
        gps_data.get(piexif.GPSIFD.GPSLongitude),
        gps_data.get(piexif.GPSIFD.GPSLongitudeRef),
    )
    if isinstance(latitude, float) and isinstance(longitude, float):
        metadata["GPS location"] = f"{latitude:.6f}, {longitude:.6f}"

    image.close()
    return metadata


def _load_png_metadata(file_path: str) -> Dict[str, str]:
    image = Image.open(file_path)
    info = image.info
    metadata = {
        "File": os.path.basename(file_path),
        "Format": image.format or "Unknown",
        "Size": f"{image.width} x {image.height}",
        "Camera model": info.get("Camera model", "Not available"),
        "Date taken": info.get("Date taken", "Not available"),
        "Image description": info.get("Description", info.get("ImageDescription", "Not available")),
        "Keywords": info.get("Keywords", info.get("XPKeywords", "Not available")),
        "User comment": info.get("UserComment", "Not available"),
        "GPS location": info.get("GPS location", "Not available"),
    }
    image.close()
    return metadata


def extract_metadata(file_path: str) -> Dict[str, str]:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    if not is_supported_image(file_path):
        raise ValueError("Unsupported image format. Please use JPG, JPEG, or PNG.")

    extension = os.path.splitext(file_path)[1].lower()
    if extension in {".jpg", ".jpeg"}:
        return _load_jpeg_metadata(file_path)
    return _load_png_metadata(file_path)


def format_metadata_for_display(metadata: Dict[str, str]) -> str:
    return "\n".join(f"{key}: {value}" for key, value in metadata.items())


def load_keywords(keyword_file: str) -> List[str]:
    if not os.path.exists(keyword_file):
        raise FileNotFoundError(f"Keyword file not found: {keyword_file}")

    with open(keyword_file, "r", encoding="utf-8") as handle:
        keywords = [line.strip() for line in handle if line.strip()]

    if not keywords:
        raise ValueError("No keywords were found in the text file.")
    return keywords
