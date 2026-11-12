"""Atomic local storage for saved itinerary snapshots in one process."""

from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Lock
from uuid import UUID

from pydantic import TypeAdapter

from app.config import get_settings
from app.contracts import SavedTrip
from app.errors import NotFoundError, StorageError

_trips = TypeAdapter(list[SavedTrip])
_lock = Lock()


def _path() -> Path:
    settings = get_settings()
    return settings.resolve_data_path(settings.trips_path)


def _read(path: Path) -> dict[str, SavedTrip]:
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return {}
    except OSError as exc:
        raise StorageError("无法读取本地行程记录。") from exc
    try:
        trips = _trips.validate_json(raw)
        by_id = {str(UUID(trip.trip_id)): trip for trip in trips}
        if len(by_id) != len(trips):
            raise ValueError("duplicate trip IDs")
        return by_id
    except ValueError as exc:
        raise StorageError("本地行程文件已损坏，原记录已保留。") from exc


def _write(path: Path, trips: dict[str, SavedTrip]) -> None:
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            dir=path.parent, prefix=f"{path.name}.", suffix=".tmp", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(_trips.dump_json(list(trips.values()), indent=2))
        temporary.replace(path)
    except OSError as exc:
        raise StorageError("无法写入本地行程记录。") from exc
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def add_trip(trip: SavedTrip) -> None:
    with _lock:
        path = _path()
        trips = _read(path)
        if trip.trip_id in trips:
            raise StorageError("行程编号已存在，请重新保存。")
        trips[trip.trip_id] = trip
        _write(path, trips)


def list_trips() -> list[SavedTrip]:
    with _lock:
        trips = _read(_path())
    # Stable secondary order for timestamps representing the same UTC instant.
    return sorted(
        sorted(trips.values(), key=lambda trip: trip.trip_id),
        key=lambda trip: datetime.fromisoformat(trip.created_at),
        reverse=True,
    )


def get_trip(trip_id: str) -> SavedTrip:
    with _lock:
        trip = _read(_path()).get(_canonical_id(trip_id))
    if trip is None:
        raise NotFoundError("该行程记录不存在。")
    return trip


def delete_trip(trip_id: str) -> None:
    with _lock:
        path = _path()
        trips = _read(path)
        if trips.pop(_canonical_id(trip_id), None) is None:
            raise NotFoundError("该行程记录不存在。")
        _write(path, trips)


def _canonical_id(trip_id: str) -> str:
    try:
        return str(UUID(trip_id))
    except ValueError:
        return trip_id
