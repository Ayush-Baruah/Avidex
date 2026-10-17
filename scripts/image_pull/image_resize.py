from pathlib import Path
from PIL import Image, ImageOps, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True


PARENT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = Path(PARENT_DIR / "data")

SOURCE = DATA_DIR / "downloaded_bird_photos"
TARGET = DATA_DIR / "resized_images"


def resize_image(source_path: Path, target_path: Path, short_side: int = 256) -> None:
    """Resize one image and save it as a complete JPEG."""
    with Image.open(source_path) as image:
        image = ImageOps.exif_transpose(image)
        image = image.convert("RGB")

        width, height = image.size
        scale = short_side / min(width, height)
        new_size = (round(width * scale), round(height * scale))

        image = image.resize(new_size, Image.Resampling.LANCZOS)

        # Save to a temporary file first; replace the destination only when done.
        temp_path = target_path.with_name(target_path.name + ".tmp")
        image.save(temp_path, format="JPEG", quality=90)
        temp_path.replace(target_path)






def resize_images(source_dir, target_dir):
    source_dir = Path(source_dir)
    target_dir = Path(target_dir)

    for source_folder in sorted(source_dir.iterdir()):
        if not source_folder.is_dir():
            continue

        # Make a matching species folder inside resized_images.
        target_folder = target_dir / source_folder.name
        target_folder.mkdir(parents=True, exist_ok=True)

        images = sorted(
            image for image in source_folder.iterdir()
            if image.is_file() and image.suffix.lower() in {".jpg", ".jpeg"}
        )

        for image in images:
            target_image = target_folder / image.name

            # Skip images already resized, so the script can be rerun.
            if target_image.exists():
                continue

            try:
                resize_image(image, target_image)
            except Exception as error:
                print(f"Could not resize {image}: {error}")






def image_counts(root):
    root = Path(root)
    return {
        folder.name: sum(
            1 for file in folder.iterdir()
            if file.is_file() and file.suffix.lower() in {".jpg", ".jpeg"}
        )
        for folder in root.iterdir()
        if folder.is_dir()
    }

source_counts = image_counts(SOURCE)
target_counts = image_counts(TARGET)

for species in sorted(source_counts.keys() | target_counts.keys()):
    source_count = source_counts.get(species, 0)
    target_count = target_counts.get(species, 0)
    if source_count != target_count:
        print(f"{species}: source={source_count}, resized={target_count}")

resize_images(SOURCE, TARGET)
