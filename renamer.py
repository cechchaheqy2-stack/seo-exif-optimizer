import os
from typing import List, Tuple

from exif_reader import SUPPORTED_EXTENSIONS


def _slugify(value: str) -> str:
    cleaned = []
    for character in value.strip().lower():
        if character.isalnum():
            cleaned.append(character)
        elif character in {" ", "-", "_"}:
            cleaned.append("-")
    slug = "".join(cleaned)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


def _unique_destination(folder_path: str, filename: str, source_path: str) -> str:
    candidate = os.path.join(folder_path, filename)
    if os.path.abspath(candidate) == os.path.abspath(source_path) or not os.path.exists(candidate):
        return candidate

    name, extension = os.path.splitext(filename)
    index = 2
    while True:
        candidate = os.path.join(folder_path, f"{name}-{index}{extension}")
        if os.path.abspath(candidate) == os.path.abspath(source_path) or not os.path.exists(candidate):
            return candidate
        index += 1


def rename_images(folder_path: str, main_keyword: str) -> List[Tuple[str, str]]:
    if not os.path.isdir(folder_path):
        raise NotADirectoryError(f"Folder not found: {folder_path}")

    slug = _slugify(main_keyword)
    if not slug:
        raise ValueError("Please enter a valid main keyword for renaming.")

    image_files = [
        os.path.join(folder_path, name)
        for name in sorted(os.listdir(folder_path))
        if os.path.isfile(os.path.join(folder_path, name))
        and os.path.splitext(name)[1].lower() in SUPPORTED_EXTENSIONS
    ]

    if not image_files:
        raise ValueError("No supported images were found in the selected folder.")

    renamed_files: List[Tuple[str, str]] = []
    for index, old_path in enumerate(image_files, start=1):
        extension = os.path.splitext(old_path)[1].lower()
        target_name = f"{slug}{extension}" if index == 1 else f"{slug}-{index}{extension}"
        new_path = _unique_destination(folder_path, target_name, old_path)
        if os.path.abspath(new_path) != os.path.abspath(old_path):
            os.rename(old_path, new_path)
        renamed_files.append((os.path.basename(old_path), os.path.basename(new_path)))

    return renamed_files
