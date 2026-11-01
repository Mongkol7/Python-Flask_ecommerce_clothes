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
