from __future__ import annotations

from dataclasses import dataclass
from typing import Any


VALID_FIELDS = {
    "name",
    "latitude",
    "longitude",
    "description",
    "address",
    "working_hours",
    "yandex_map_link",
    "google_map_link",
    "two_gis_map_link",
    "is_free",
    "level",
    "auto_play_radius_m",
    "imageResourceId",
    "markerResourceId",
    "lockedMarkerResourceId",
    "audioResourceId",
}

REQUIRED_FIELDS = (
    "name",
    "latitude",
    "longitude",
    "yandex_map_link",
    "google_map_link",
    "two_gis_map_link",
    "level",
    "imageResourceId",
    "markerResourceId",
    "lockedMarkerResourceId",
    "audioResourceId",
)


@dataclass(frozen=True)
class ValidationResult:
    is_valid: bool
    errors: list[str]
    unknown_fields: list[str]


def validate_points_json(data: Any) -> ValidationResult:
    errors: list[str] = []
    unknown: set[str] = set()

    if not isinstance(data, list):
        return ValidationResult(False, ["JSON должен быть массивом объектов"], [])

    for index, item in enumerate(data):
        prefix = f"Точка {index + 1}"
        if not isinstance(item, dict):
            errors.append(f"{prefix}: должна быть объектом")
            continue
        for key in item:
            if key not in VALID_FIELDS:
                unknown.add(key)
        for field in REQUIRED_FIELDS:
            if field not in item:
                errors.append(f"{prefix}: отсутствует обязательное поле «{field}»")
        _check_types(item, prefix, errors)

    return ValidationResult(len(errors) == 0, errors, sorted(unknown))


def _check_types(item: dict[str, Any], prefix: str, errors: list[str]) -> None:
    if "name" in item and not isinstance(item["name"], str):
        errors.append(f"{prefix}: поле name должно быть строкой")
    if "latitude" in item and not isinstance(item["latitude"], (int, float)):
        errors.append(f"{prefix}: поле latitude должно быть числом")
    if "longitude" in item and not isinstance(item["longitude"], (int, float)):
        errors.append(f"{prefix}: поле longitude должно быть числом")
    for field in ("yandex_map_link", "google_map_link", "two_gis_map_link"):
        if field in item and not isinstance(item[field], str):
            errors.append(f"{prefix}: поле {field} должно быть строкой")
    if "level" in item and not isinstance(item["level"], int):
        errors.append(f"{prefix}: поле level должно быть целым числом")


def to_import_payload(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": item["name"],
        "latitude": item["latitude"],
        "longitude": item["longitude"],
        "description": item.get("description"),
        "address": item.get("address"),
        "workingHours": item.get("working_hours"),
        "yandexMapLink": item["yandex_map_link"],
        "googleMapLink": item["google_map_link"],
        "twoGisMapLink": item["two_gis_map_link"],
        "isFree": item.get("is_free", True),
        "level": item["level"],
        "audioDuration": 0,
        "autoPlayRadiusM": item.get("auto_play_radius_m", 40),
        "imageResourceId": item.get("imageResourceId"),
        "markerResourceId": item.get("markerResourceId"),
        "lockedMarkerResourceId": item.get("lockedMarkerResourceId"),
        "audioResourceId": item.get("audioResourceId"),
    }
