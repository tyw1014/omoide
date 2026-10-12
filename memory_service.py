"""Memory CRUD plus private, decoded/re-encoded photograph storage."""
import io
import warnings
from pathlib import Path
from uuid import uuid4

from PIL import Image, UnidentifiedImageError

from ai_service import AIService, ProcessingResult
from models import MemoryInput, Metadata


class MemoryService:
    def __init__(self, db, media_dir, ai=None):
        self.db = db
        self.media_dir = Path(media_dir)
        self.media_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.media_dir.chmod(0o700)
        self.ai = ai or AIService()

    def store_photo(self, data):
        if len(data) > 5 * 1024 * 1024:
            raise ValueError("Photographs must be 5 MB or smaller")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(data)) as image:
                    if image.format not in {"JPEG", "PNG", "WEBP"} or image.width * image.height > 25_000_000:
                        raise ValueError("Use a JPEG, PNG, or WebP photograph up to 25 megapixels")
                    image.load()
                    from PIL import ImageOps
                    image = ImageOps.exif_transpose(image).convert("RGB")
                    image.thumbnail((2400, 2400))
                    name = f"{uuid4().hex}.jpg"
                    path = self.media_dir / name
                    image.save(path, "JPEG", quality=88)
                    path.chmod(0o600)
                    return name
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            raise ValueError("The uploaded file is not a supported photograph") from exc

    def photo_path(self, name):
        if not name or Path(name).name != name:
            return None
        path = self.media_dir / name
        return path if path.is_file() else None

    def remove_photo(self, name):
        path = self.photo_path(name)
        if path:
            path.unlink()

    def create(self, memory: MemoryInput, *, photo=None, synthetic=False, demo_key=None):
        memory = MemoryInput.model_validate(memory)
        result = self.ai.extract(memory.content, memory.location)
        media = self.store_photo(photo) if photo else None
        try:
            return self.db.create_entry(memory, result.value, result.mode, media_path=media, note=result.note, synthetic=synthetic, demo_key=demo_key)
        except Exception:
            self.remove_photo(media)
            raise

    def update(self, entry_id, memory, *, metadata=None, photo=None, remove_photo=False):
        memory = MemoryInput.model_validate(memory)
        old = self.db.get_entry(entry_id)
        if old is None:
            raise ValueError("Memory no longer exists")
        result = ProcessingResult(Metadata.model_validate(metadata), "User edited") if metadata is not None else self.ai.extract(memory.content, memory.location)
        new_media = self.store_photo(photo) if photo else None
        media = new_media or (None if remove_photo else old["media_path"])
        try:
            self.db.update_entry(entry_id, memory, result.value, result.mode, media_path=media, note=result.note)
        except Exception:
            self.remove_photo(new_media)
            raise
        if old["media_path"] != media:
            self.remove_photo(old["media_path"])

    def delete(self, entry_id):
        old = self.db.get_entry(entry_id)
        self.db.delete_entry(entry_id)
        if old:
            self.remove_photo(old["media_path"])
