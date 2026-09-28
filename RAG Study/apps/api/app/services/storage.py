import logging
from pathlib import Path

from app.config import get_settings

log = logging.getLogger("folio.storage")


class LocalObjectStorage:
    """Filesystem stand-in for object storage.

    Keys are server-generated (`course/{id}/documents/{id}/versions/{id}/original.pdf`).
    The database stores the key; the file bytes never go into PostgreSQL.
    """

    def __init__(self, root: Path) -> None:
        self.root = root

    def put(self, key: str, data: bytes) -> None:
        path = self.path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_bytes(data)
        temporary.replace(path)

    def delete(self, key: str) -> None:
        try:
            path = self.path_for(key)
        except ValueError:
            log.warning("refusing to delete invalid storage key")
            return
        if path.is_file():
            path.unlink()

    def path_for(self, key: str) -> Path:
        parts = Path(key).parts
        if not key or key.startswith("/") or ".." in parts:
            raise ValueError("Invalid storage key")
        root = self.root.resolve()
        path = (root / key).resolve()
        if path != root and root not in path.parents:
            raise ValueError("Invalid storage key")
        return path


def get_storage() -> LocalObjectStorage:
    root = Path(get_settings().storage_root)
    root.mkdir(parents=True, exist_ok=True)
    return LocalObjectStorage(root)
