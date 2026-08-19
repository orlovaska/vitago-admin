from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RoutePoint:
    latitude: float
    longitude: float
    name: str | None = None


def convert_geojson_to_route(geojson: dict[str, Any]) -> list[RoutePoint]:
    features = geojson.get("features")
    if not isinstance(features, list):
        raise ValueError("Некорректный формат GeoJSON: отсутствует массив features")

    main_points: list[tuple[float, float, str | None]] = []
    for feature in features:
        geometry = feature.get("geometry") or {}
        if geometry.get("type") == "Point":
            lon, lat = geometry["coordinates"]
            props = feature.get("properties") or {}
            name = props.get("iconCaption") or props.get("name")
            main_points.append((lat, lon, name))

    route_points: list[RoutePoint] = []
    processed: set[str] = set()

    for feature in features:
        geometry = feature.get("geometry") or {}
        if geometry.get("type") not in {"LineString", "MultiLineString"}:
            continue
        for lat, lon in _extract_coordinates(geometry):
            key = f"{lat:.6f},{lon:.6f}"
            if key in processed:
                continue
            processed.add(key)
            match = next((item for item in main_points if _points_match(item[0], item[1], lat, lon)), None)
            route_points.append(RoutePoint(latitude=lat, longitude=lon, name=match[2] if match else None))

    return route_points


def _extract_coordinates(geometry: dict[str, Any]) -> list[tuple[float, float]]:
    coords: list[tuple[float, float]] = []
    kind = geometry.get("type")
    if kind == "Point":
        lon, lat = geometry["coordinates"]
        coords.append((lat, lon))
    elif kind == "LineString":
        for lon, lat in geometry.get("coordinates") or []:
            coords.append((lat, lon))
    elif kind == "MultiLineString":
        for line in geometry.get("coordinates") or []:
            for lon, lat in line:
                coords.append((lat, lon))
    return coords


def _points_match(lat1: float, lon1: float, lat2: float, lon2: float, tolerance: float = 0.001) -> bool:
    return abs(lat1 - lat2) < tolerance and abs(lon1 - lon2) < tolerance
