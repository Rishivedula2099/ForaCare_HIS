import io
import uuid
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from app.core.config import get_settings
from app.core.exceptions import AppError

ALLOWED_CONTENT_TYPES: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


class UnsupportedFileTypeError(AppError):
    status_code = 415
    code = "UNSUPPORTED_FILE_TYPE"


class FileTooLargeError(AppError):
    status_code = 413
    code = "FILE_TOO_LARGE"


class InvalidFileContentError(AppError):
    status_code = 422
    code = "INVALID_FILE_CONTENT"


def _storage_root() -> Path:
    return Path(get_settings().file_storage_root).resolve()


def _patient_dir(tenant_id: uuid.UUID, facility_id: uuid.UUID, patient_id: uuid.UUID) -> Path:
    return _storage_root() / str(tenant_id) / str(facility_id) / "patients" / str(patient_id)


def validate_and_store_photo(
    *,
    tenant_id: uuid.UUID,
    facility_id: uuid.UUID,
    patient_id: uuid.UUID,
    content_type: str | None,
    raw_bytes: bytes,
) -> tuple[str, str]:
    """Validates an uploaded patient photo and writes it to disk.

    Returns (storage_path, content_type). `storage_path` is relative to the
    configured storage root, not an absolute filesystem path, so it is safe
    to persist on `PatientPhoto.storage_path` without leaking the deployment
    layout.
    """
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise UnsupportedFileTypeError(
            f"Unsupported file type '{content_type}'. Allowed: {', '.join(ALLOWED_CONTENT_TYPES)}."
        )

    max_bytes = get_settings().file_upload_max_bytes
    if len(raw_bytes) > max_bytes:
        raise FileTooLargeError(f"File exceeds the {max_bytes // (1024 * 1024)}MB upload limit.")

    # Decode the actual bytes (not just the declared content-type) so a
    # renamed/spoofed file is rejected rather than trusted.
    try:
        image = Image.open(io.BytesIO(raw_bytes))
        image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise InvalidFileContentError("The uploaded file is not a valid image.") from exc

    extension = ALLOWED_CONTENT_TYPES[content_type]
    directory = _patient_dir(tenant_id, facility_id, patient_id)
    directory.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid.uuid4()}.{extension}"
    absolute_path = directory / filename
    absolute_path.write_bytes(raw_bytes)

    storage_path = str(absolute_path.relative_to(_storage_root()))
    return storage_path, content_type


def resolve_absolute_path(storage_path: str) -> Path:
    """Resolves a stored relative path back to an absolute filesystem path.

    Rejects any path that would escape the storage root (defense in depth -
    `storage_path` values are only ever written by `validate_and_store_photo`
    above, never taken from user input directly).
    """
    root = _storage_root()
    absolute_path = (root / storage_path).resolve()
    if root not in absolute_path.parents and absolute_path != root:
        raise InvalidFileContentError("Invalid stored file path.")
    return absolute_path
