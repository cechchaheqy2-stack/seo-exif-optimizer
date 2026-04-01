import os
from typing import Iterable, List, Tuple

from PIL import Image, PngImagePlugin
import piexif
from piexif import helper

from exif_reader import SUPPORTED_EXTENSIONS, is_supported_image

PNG_TEXT_LIMIT = 7900


def _default_exif_dict():
    return {
        "0th": {},
        "Exif": {},
        "GPS": {},
        "Interop": {},
        "1st": {},
        "thumbnail": None,
    }


def normalize_keywords(keywords: Iterable[str]) -> List[str]:
    return [keyword.strip() for keyword in keywords if keyword and keyword.strip()]


def inject_keywords_into_image(file_path: str, keywords: Iterable[str]) -> None:
    normalized_keywords = normalize_keywords(keywords)
    if not normalized_keywords:
        raise ValueError("No keywords available to inject.")
    if not is_supported_image(file_path):
        raise ValueError(f"Unsupported image format: {file_path}")

    extension = os.path.splitext(file_path)[1].lower()
    keyword_text = ", ".join(normalized_keywords)

    if extension in {".jpg", ".jpeg"}:
        _inject_into_jpeg(file_path, keyword_text)
    else:
        _inject_into_png(file_path, keyword_text)


def _inject_into_jpeg(file_path: str, keyword_text: str) -> None:
    image = Image.open(file_path)
    exif_bytes = image.info.get("exif", b"")
    exif_dict = piexif.load(exif_bytes) if exif_bytes else _default_exif_dict()

    exif_dict["0th"][piexif.ImageIFD.ImageDescription] = keyword_text.encode("utf-8")
    exif_dict["0th"][piexif.ImageIFD.XPKeywords] = keyword_text.encode("utf-16le") + b"\x00\x00"
    exif_dict["Exif"][piexif.ExifIFD.UserComment] = helper.UserComment.dump(keyword_text, encoding="unicode")

    new_exif = piexif.dump(exif_dict)
    image.save(file_path, format=image.format or "JPEG", exif=new_exif, quality="keep")
    image.close()


def _inject_into_png(file_path: str, keyword_text: str) -> None:
    image = Image.open(file_path)
    png_info = PngImagePlugin.PngInfo()

    for key, value in image.info.items():
        if isinstance(value, str):
            png_info.add_text(key, value[:PNG_TEXT_LIMIT])

    png_info.add_text("Description", keyword_text[:PNG_TEXT_LIMIT])
    png_info.add_text("Keywords", keyword_text[:PNG_TEXT_LIMIT])
    png_info.add_text("XPKeywords", keyword_text[:PNG_TEXT_LIMIT])
    png_info.add_text("UserComment", keyword_text[:PNG_TEXT_LIMIT])

    image.save(file_path, format="PNG", pnginfo=png_info)
    image.close()


def process_folder(folder_path: str, keywords: Iterable[str]) -> Tuple[int, List[str]]:
    if not os.path.isdir(folder_path):
        raise NotADirectoryError(f"Folder not found: {folder_path}")

    processed = 0
    failures: List[str] = []

    for entry in sorted(os.listdir(folder_path)):
        file_path = os.path.join(folder_path, entry)
        if not os.path.isfile(file_path):
            continue
        if os.path.splitext(file_path)[1].lower() not in SUPPORTED_EXTENSIONS:
            continue

        try:
            inject_keywords_into_image(file_path, keywords)
            processed += 1
        except Exception as exc:
            failures.append(f"{entry}: {exc}")

    return processed, failures
