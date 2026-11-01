import os
from werkzeug.utils import secure_filename
from PIL import Image


def allowed_file(filename, allowed_extensions):
    return (
        "." in filename
        and filename.rsplit(".", 1)[-1].lower() in allowed_extensions
    )#first find . then split the filename by . and take the last part, then compare it with allowed_extensions 
    #rsplit(".", 1): split the filename by . at most 1 time from the right side. for example: "image.jpg".rsplit(".", 1) -> ["image", "jpg"]
    


def save_user_image(
    file,
    user_id,
    upload_folder,
    allowed_extensions,
    scale=0.8
):
    """
    Saves user image in two versions within the user folder:
      1. Original: {user_id}_org_{filename}
      2. Compressed: {user_id}_thum_{filename} (80% dimension size by Pillow)
    Returns a dict with versioned filenames and the base filename for DB storage.
    """
    if not file or not file.filename:
        return None
    if not allowed_file(file.filename, allowed_extensions):
        return None

    filename = secure_filename(file.filename)
    os.makedirs(upload_folder, exist_ok=True)

    original_filename = f"{user_id}_org_{filename}"
    thumb_filename = f"{user_id}_thum_{filename}"

    original_path = os.path.join(upload_folder, original_filename)
    thumb_path = os.path.join(upload_folder, thumb_filename)

    # Save original image file
    file.save(original_path)

    # Generate compressed thumbnail (80% size) with Pillow
    with Image.open(original_path) as image:
        new_width = max(1, int(image.width * scale))
        new_height = max(1, int(image.height * scale))
        thumb = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        thumb.save(thumb_path)

    return {
        "original": original_filename,
        "thumbnail": thumb_filename,
        "filename": filename,
    }


def save_uploaded_image(file, upload_folder, allowed_extensions, prefix=None):
    """
    Saves an uploaded image into upload_folder, generating a clean safe filename.
    Returns the saved filename.
    """
    if not file or not file.filename:
        return None
    if not allowed_file(file.filename, allowed_extensions):
        return None

    import time
    filename = secure_filename(file.filename)
    timestamp = int(time.time())
    saved_filename = f"{prefix}_{timestamp}_{filename}" if prefix else f"{timestamp}_{filename}"

    os.makedirs(upload_folder, exist_ok=True)
    file_path = os.path.join(upload_folder, saved_filename)
    file.save(file_path)

    return saved_filename


def save_product_image(file, upload_folder, allowed_extensions, prefix="prod", max_thumb_size=(450, 600), quality=75):
    """
    Saves a product image in two versions:
      1. Original (Full Quality): {prefix}_{timestamp}_{filename}
      2. Thumbnail (Low Quality / Fast Load): thum_{prefix}_{timestamp}_{filename}
    Returns a dict with URLs and filenames.
    """
    if not file or not file.filename:
        return None
    if not allowed_file(file.filename, allowed_extensions):
        return None

    import time
    clean_name = secure_filename(file.filename)
    timestamp = int(time.time())
    base_name = f"{prefix}_{timestamp}_{clean_name}" if prefix else f"{timestamp}_{clean_name}"
    thumb_name = f"thum_{base_name}"

    os.makedirs(upload_folder, exist_ok=True)
    orig_path = os.path.join(upload_folder, base_name)
    thumb_path = os.path.join(upload_folder, thumb_name)

    # Save original high-resolution
    file.save(orig_path)

    # Generate compressed thumbnail with Pillow
    try:
        with Image.open(orig_path) as img:
            if img.mode in ("RGBA", "P"):
                img_to_save = img.convert("RGB")
            else:
                img_to_save = img.copy()

            img_to_save.thumbnail(max_thumb_size, Image.Resampling.LANCZOS)
            img_to_save.save(thumb_path, "JPEG", quality=quality, optimize=True)
    except Exception:
        import shutil
        shutil.copyfile(orig_path, thumb_path)

    return {
        "original_filename": base_name,
        "thumbnail_filename": thumb_name,
        "original_url": f"/static/image/product/{base_name}",
        "thumbnail_url": f"/static/image/product/{thumb_name}",
    }


def generate_thumbnail_for_file(filepath, max_thumb_size=(450, 600), quality=75):
    """Generates thum_{basename} next to filepath if it does not exist already."""
    dirname = os.path.dirname(filepath)
    basename = os.path.basename(filepath)
    if basename.startswith("thum_"):
        return None

    thumb_name = f"thum_{basename}"
    thumb_path = os.path.join(dirname, thumb_name)

    try:
        with Image.open(filepath) as img:
            if img.mode in ("RGBA", "P"):
                img_to_save = img.convert("RGB")
            else:
                img_to_save = img.copy()

            img_to_save.thumbnail(max_thumb_size, Image.Resampling.LANCZOS)
            img_to_save.save(thumb_path, "JPEG", quality=quality, optimize=True)
            return thumb_path
    except Exception:
        return None
