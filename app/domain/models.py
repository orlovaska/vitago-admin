from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any

from app.domain.enums import AppStore, MimeType, ReviewStatus


def _opt_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _opt_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _opt_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_cues(value: Any) -> tuple[dict[str, Any], ...] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        return None
    cues: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        try:
            cues.append(
                {
                    "start": float(item["start"]),
                    "end": float(item["end"]),
                    "text": str(item["text"]),
                }
            )
        except (KeyError, TypeError, ValueError):
            continue
    return tuple(cues)


@dataclass(frozen=True)
class Resource:
    resource_id: int
    file_path: str
    mime_type: str
    created_at: datetime | None = None
    usages: tuple[str, ...] = ()

    @property
    def is_used(self) -> bool:
        return bool(self.usages)

    @property
    def file_name(self) -> str:
        return self.file_path.replace("\\", "/").split("/")[-1]

    @classmethod
    def from_api(cls, raw: dict[str, Any]) -> Resource:
        created_at = _parse_dt(raw.get("createdAt"))
        return cls(
            resource_id=int(raw.get("resourceId") or 0),
            file_path=str(raw.get("resourceFilePath") or ""),
            mime_type=str(raw.get("mimeType") or ""),
            created_at=created_at,
            usages=tuple(raw.get("usages") or []),
        )


@dataclass(frozen=True)
class AppVersion:
    id: int
    major: int
    minor: int
    patch: int
    store: AppStore
    release_notes: str | None = None
    version_string: str = ""
    created_at: str | None = None
    user_count: int = 0

    @property
    def label(self) -> str:
        return self.version_string or f"{self.major}.{self.minor}.{self.patch}"

    @property
    def store_label(self) -> str:
        return self.store.label

    def as_tuple(self) -> tuple[int, int, int]:
        return self.major, self.minor, self.patch

    @classmethod
    def from_api(cls, raw: dict[str, Any]) -> AppVersion:
        major = int(raw.get("major") or 0)
        minor = int(raw.get("minor") or 0)
        patch = int(raw.get("patch") or 0)
        return cls(
            id=int(raw.get("id") or 0),
            major=major,
            minor=minor,
            patch=patch,
            release_notes=_opt_str(raw.get("releaseNotes")),
            version_string=str(raw.get("versionString") or f"{major}.{minor}.{patch}"),
            created_at=str(raw.get("createdAt") or "") or None,
            user_count=int(raw.get("userCount") or 0),
            store=AppStore.from_api(raw.get("store")),
        )


@dataclass(frozen=True)
class Point:
    id: int | None = None
    travel_route_id: int | None = None
    name: str = ""
    description: str | None = None
    address: str | None = None
    working_hours: str | None = None
    latitude: float = 0.0
    longitude: float = 0.0
    yandex_map_link: str = ""
    google_map_link: str = ""
    two_gis_map_link: str = ""
    is_free: bool = False
    level: int = 1
    auto_play_radius_m: int = 40
    image_resource_id: int | None = None
    marker_resource_id: int | None = None
    locked_marker_resource_id: int | None = None
    audio_resource_id: int | None = None
    transcript: str | None = None
    transcript_cues: tuple[dict[str, Any], ...] | None = None

    def with_updates(self, **kwargs: Any) -> Point:
        return replace(self, **kwargs)

    @classmethod
    def from_api(cls, raw: dict[str, Any]) -> Point:
        cues = _parse_cues(raw.get("transcriptCues"))
        return cls(
            id=_opt_int(raw.get("id")),
            travel_route_id=_opt_int(raw.get("travelRouteId")),
            name=str(raw.get("name") or ""),
            description=_opt_str(raw.get("description")),
            address=_opt_str(raw.get("address")),
            working_hours=_opt_str(raw.get("working_hours") or raw.get("workingHours")),
            latitude=float(raw.get("latitude") or 0),
            longitude=float(raw.get("longitude") or 0),
            yandex_map_link=str(raw.get("yandex_map_link") or raw.get("yandexMapLink") or ""),
            google_map_link=str(raw.get("google_map_link") or raw.get("googleMapLink") or ""),
            two_gis_map_link=str(raw.get("two_gis_map_link") or raw.get("twoGisMapLink") or ""),
            is_free=bool(raw.get("is_free") if "is_free" in raw else raw.get("isFree", False)),
            level=int(raw.get("level") or 1),
            auto_play_radius_m=int(raw.get("auto_play_radius_m") or raw.get("autoPlayRadiusM") or 40),
            image_resource_id=_opt_int(raw.get("imageResourceId")),
            marker_resource_id=_opt_int(raw.get("markerResourceId")),
            locked_marker_resource_id=_opt_int(raw.get("lockedMarkerResourceId")),
            audio_resource_id=_opt_int(raw.get("audioResourceId")),
            transcript=_opt_str(raw.get("transcript")),
            transcript_cues=cues,
        )

    def to_form_dto(self) -> dict[str, Any]:
        basic: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "transcript": self.transcript,
            "transcriptCues": list(self.transcript_cues) if self.transcript_cues is not None else None,
            "address": self.address,
            "workingHours": self.working_hours,
        }
        return {
            "basicInfo": basic,
            "coordinates": {
                "latitude": self.latitude,
                "longitude": self.longitude,
            },
            "mapLinks": {
                "yandexMapLink": self.yandex_map_link,
                "googleMapLink": self.google_map_link,
                "twoGisMapLink": self.two_gis_map_link,
            },
            "settings": {
                "isFree": self.is_free,
                "level": self.level,
                "audioDuration": 0,
                "autoPlayRadiusM": self.auto_play_radius_m,
            },
            "resources": {
                "imageResourceId": self.image_resource_id,
                "markerResourceId": self.marker_resource_id,
                "lockedMarkerResourceId": self.locked_marker_resource_id,
                "audioResourceId": self.audio_resource_id,
            },
        }

    @classmethod
    def from_form_dto(cls, dto: dict[str, Any], point_id: int | None = None, route_id: int | None = None) -> Point:
        basic = dto.get("basicInfo") or {}
        coords = dto.get("coordinates") or {}
        links = dto.get("mapLinks") or {}
        settings = dto.get("settings") or {}
        resources = dto.get("resources") or {}
        cues = _parse_cues(basic.get("transcriptCues"))
        return cls(
            id=point_id,
            travel_route_id=route_id,
            name=str(basic.get("name") or ""),
            description=_opt_str(basic.get("description")),
            address=_opt_str(basic.get("address")),
            working_hours=_opt_str(basic.get("workingHours")),
            latitude=float(coords.get("latitude") or 0),
            longitude=float(coords.get("longitude") or 0),
            yandex_map_link=str(links.get("yandexMapLink") or ""),
            google_map_link=str(links.get("googleMapLink") or ""),
            two_gis_map_link=str(links.get("twoGisMapLink") or ""),
            is_free=bool(settings.get("isFree", False)),
            level=int(settings.get("level") or 1),
            auto_play_radius_m=int(settings.get("autoPlayRadiusM") or 40),
            image_resource_id=_opt_int(resources.get("imageResourceId")),
            marker_resource_id=_opt_int(resources.get("markerResourceId")),
            locked_marker_resource_id=_opt_int(resources.get("lockedMarkerResourceId")),
            audio_resource_id=_opt_int(resources.get("audioResourceId")),
            transcript=_opt_str(basic.get("transcript")),
            transcript_cues=cues,
        )


@dataclass
class RouteForm:
    route_name: str = ""
    description: str = ""
    city: str = ""
    subtitle: str | None = None
    route_description: str | None = None
    amount: int = 0
    distance_text: str | None = None
    distance_description: str | None = None
    route_duration_text: str | None = None
    route_duration_description: str | None = None
    map_initial_latitude: float | None = None
    map_initial_longitude: float | None = None
    map_initial_zoom: float | None = None
    audio_resource_id: int | None = None
    route_path_json_resource_id: int | None = None
    route_image_resource_ids: list[int] = field(default_factory=list)

    def to_api(self) -> dict[str, Any]:
        return {
            "basicInfo": {
                "routeName": self.route_name,
                "description": self.description,
                "city": self.city,
                "subtitle": self.subtitle,
                "routeDescription": self.route_description,
            },
            "pricing": {"amount": self.amount},
            "routeInfo": {
                "audioDuration": 0,
                "distanceText": self.distance_text,
                "distanceDescription": self.distance_description,
                "routeDurationText": self.route_duration_text,
                "routeDurationDescription": self.route_duration_description,
            },
            "mapSettings": {
                "mapInitialLatitude": self.map_initial_latitude,
                "mapInitialLongitude": self.map_initial_longitude,
                "mapInitialZoom": self.map_initial_zoom,
            },
            "resources": {
                "audioResourceId": self.audio_resource_id,
                "routePathJsonResourceId": self.route_path_json_resource_id,
                "backgroundPhotoResourceId": None,
                "routeImageResourceIds": list(self.route_image_resource_ids),
            },
        }

    @classmethod
    def from_api(cls, dto: dict[str, Any]) -> RouteForm:
        basic = dto.get("basicInfo") or {}
        pricing = dto.get("pricing") or {}
        info = dto.get("routeInfo") or {}
        maps = dto.get("mapSettings") or {}
        resources = dto.get("resources") or {}
        return cls(
            route_name=str(basic.get("routeName") or ""),
            description=str(basic.get("description") or ""),
            city=str(basic.get("city") or ""),
            subtitle=_opt_str(basic.get("subtitle")),
            route_description=_opt_str(basic.get("routeDescription")),
            amount=int(pricing.get("amount") or 0),
            distance_text=_opt_str(info.get("distanceText")),
            distance_description=_opt_str(info.get("distanceDescription")),
            route_duration_text=_opt_str(info.get("routeDurationText")),
            route_duration_description=_opt_str(info.get("routeDurationDescription")),
            map_initial_latitude=_opt_float(maps.get("mapInitialLatitude")),
            map_initial_longitude=_opt_float(maps.get("mapInitialLongitude")),
            map_initial_zoom=_opt_float(maps.get("mapInitialZoom")),
            audio_resource_id=_opt_int(resources.get("audioResourceId")),
            route_path_json_resource_id=_opt_int(resources.get("routePathJsonResourceId")),
            route_image_resource_ids=[int(x) for x in (resources.get("routeImageResourceIds") or [])],
        )


@dataclass(frozen=True)
class TravelRoute:
    id: int
    route_name: str
    description: str
    city: str
    amount: int
    points: tuple[Point, ...] = ()

    @property
    def price_rub(self) -> float:
        return self.amount / 100

    @classmethod
    def from_api(cls, raw: dict[str, Any]) -> TravelRoute:
        points = tuple(Point.from_api(item) for item in (raw.get("points") or []))
        return cls(
            id=int(raw.get("id") or 0),
            route_name=str(raw.get("route_name") or raw.get("routeName") or ""),
            description=str(raw.get("description") or ""),
            city=str(raw.get("city") or ""),
            amount=int(raw.get("amount") or 0),
            points=points,
        )


@dataclass(frozen=True)
class RedirectUrls:
    success_url: str = ""
    fail_url: str = ""
    go_to_our_site_url: str = ""

    @classmethod
    def from_api(cls, raw: dict[str, Any] | None) -> RedirectUrls:
        raw = raw or {}
        return cls(
            success_url=str(raw.get("successUrl") or ""),
            fail_url=str(raw.get("failUrl") or ""),
            go_to_our_site_url=str(raw.get("goToOurSiteUrl") or ""),
        )


@dataclass(frozen=True)
class Application:
    id: int
    bundle_id: str
    is_multi_route: bool = False
    payment_service_postfix: str | None = None
    use_payment_google_play: bool = True
    use_payment_app_store: bool = True
    use_payment_ru_store: bool = True
    support_chat_url: str | None = None
    custom_scheme: str = ""
    terms_resource_id: int | None = None
    acc_recovery_image_resource_id: int | None = None
    gif_resource_id: int | None = None
    versions: tuple[AppVersion, ...] = ()
    routes: tuple[TravelRoute, ...] = ()
    redirect_urls: RedirectUrls = field(default_factory=RedirectUrls)

    @property
    def is_clone(self) -> bool:
        return not self.is_multi_route

    @classmethod
    def from_api(cls, raw: dict[str, Any]) -> Application:
        versions = tuple(AppVersion.from_api(item) for item in (raw.get("versions") or []))
        routes = tuple(TravelRoute.from_api(item) for item in (raw.get("routes") or []))
        return cls(
            id=int(raw.get("id") or 0),
            bundle_id=str(raw.get("bundle_id") or raw.get("bundleId") or ""),
            is_multi_route=bool(raw.get("isMultiRoute", False)),
            payment_service_postfix=_opt_str(raw.get("paymentServicePostfix")),
            use_payment_google_play=bool(raw.get("usePaymentGooglePlay", True)),
            use_payment_app_store=bool(raw.get("usePaymentAppStore", True)),
            use_payment_ru_store=bool(raw.get("usePaymentRuStore", True)),
            support_chat_url=_opt_str(raw.get("supportChatUrl")),
            custom_scheme=str(raw.get("customScheme") or ""),
            terms_resource_id=_opt_int(raw.get("termsResourceId")),
            acc_recovery_image_resource_id=_opt_int(raw.get("accRecoveryImageResourceId")),
            gif_resource_id=_opt_int(raw.get("gifResourceId")),
            versions=versions,
            routes=routes,
            redirect_urls=RedirectUrls.from_api(raw.get("redirectUrls")),
        )


@dataclass(frozen=True)
class Review:
    user_id: int
    route_id: int
    user_alias: str | None
    text: str | None
    rating: int
    is_verified: bool | None
    created_at: datetime | None
    route_name: str | None = None
    route_city: str | None = None

    @property
    def row_id(self) -> str:
        return f"{self.user_id}-{self.route_id}"

    @property
    def status(self) -> ReviewStatus:
        if self.is_verified is True:
            return ReviewStatus.APPROVED
        if self.is_verified is False:
            return ReviewStatus.REJECTED
        return ReviewStatus.PENDING

    @classmethod
    def from_api(cls, raw: dict[str, Any]) -> Review:
        created_at = _parse_dt(raw.get("createdAt"))
        verified = raw.get("isVerified")
        return cls(
            user_id=int(raw.get("userId")),
            route_id=int(raw.get("routeId")),
            user_alias=_opt_str(raw.get("userAlias")),
            text=_opt_str(raw.get("text")),
            rating=int(raw.get("rating") or 0),
            is_verified=None if verified is None else bool(verified),
            created_at=created_at,
            route_name=_opt_str(raw.get("routeName")),
            route_city=_opt_str(raw.get("routeCity")),
        )


@dataclass(frozen=True)
class Promocode:
    id: int
    code: str
    discount_percent: int
    is_active: bool
    show_after_payment: bool
    use_custom_scheme: bool
    route_id: int | None
    deeplink_url: str | None

    @classmethod
    def from_api(cls, raw: dict[str, Any]) -> Promocode:
        return cls(
            id=int(raw.get("id") or 0),
            code=str(raw.get("code") or ""),
            discount_percent=int(raw.get("discountPercent") or 0),
            is_active=bool(raw.get("isActive", True)),
            show_after_payment=bool(raw.get("showAfterPayment", False)),
            use_custom_scheme=bool(raw.get("useCustomScheme", False)),
            route_id=_opt_int(raw.get("routeId")),
            deeplink_url=_opt_str(raw.get("deeplinkUrl")),
        )


@dataclass(frozen=True)
class SecretItem:
    key: str
    value: str


@dataclass(frozen=True)
class SecretGroup:
    file: str
    label: str
    services: tuple[str, ...]
    secrets: tuple[SecretItem, ...]
    raw: str = ""

    @classmethod
    def from_api(cls, raw: dict[str, Any]) -> SecretGroup:
        secrets = tuple(
            SecretItem(key=str(item.get("key") or ""), value=str(item.get("value") or ""))
            for item in raw.get("secrets") or []
            if item.get("key")
        )
        services = tuple(str(item) for item in raw.get("services") or [] if item)
        return cls(
            file=str(raw.get("file") or ""),
            label=str(raw.get("label") or raw.get("file") or ""),
            services=services,
            secrets=secrets,
            raw=str(raw.get("raw") or ""),
        )


@dataclass(frozen=True)
class SecretsState:
    writable: bool
    restart_available: bool
    restart_reason: str
    groups: tuple[SecretGroup, ...]


@dataclass(frozen=True)
class ServerResource:
    path: str
    size: int | None
    modified_at: str
    on_disk: bool
    in_db: bool


@dataclass(frozen=True)
class ServerResourcesState:
    folder: str
    reason: str
    items: tuple[ServerResource, ...]
    backup_note: str = ""
    last_archive: str = ""


ALLOWED_MIME_TYPES = frozenset(MimeType.values())
