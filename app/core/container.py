from __future__ import annotations

import os
from dataclasses import dataclass

from app.core.config import Settings
from app.core.env_file import read_env, write_env
from app.core.session import AuthSession
from app.infrastructure.http.client import ApiClient
from app.infrastructure.repositories.applications import ApplicationRepository
from app.infrastructure.repositories.auth import AuthRepository
from app.infrastructure.repositories.points import PointRepository
from app.infrastructure.repositories.promocodes import PromocodeRepository
from app.infrastructure.repositories.resources import ResourceRepository
from app.infrastructure.repositories.reviews import ReviewRepository
from app.infrastructure.repositories.routes import RouteRepository
from app.infrastructure.repositories.secrets import SecretsRepository
from app.infrastructure.repositories.server_resources import ServerResourcesRepository


@dataclass
class Container:
    """Композиция сервисов. Единая точка внедрения зависимостей."""

    settings: Settings
    session: AuthSession
    client: ApiClient
    auth: AuthRepository
    applications: ApplicationRepository
    routes: RouteRepository
    points: PointRepository
    resources: ResourceRepository
    reviews: ReviewRepository
    promocodes: PromocodeRepository
    secrets: SecretsRepository
    server_resources: ServerResourcesRepository

    @classmethod
    def build(cls) -> Container:
        settings = Settings.load()
        session = AuthSession()
        client = ApiClient(settings, session)
        return cls(
            settings=settings,
            session=session,
            client=client,
            auth=AuthRepository(client),
            applications=ApplicationRepository(client),
            routes=RouteRepository(client),
            points=PointRepository(client),
            resources=ResourceRepository(client),
            reviews=ReviewRepository(client),
            promocodes=PromocodeRepository(client),
            secrets=SecretsRepository(settings),
            server_resources=ServerResourcesRepository(settings),
        )

    def apply_env(self, values: dict[str, str]) -> Settings:
        previous = read_env()
        write_env(values)
        for key in previous:
            if key not in values:
                os.environ.pop(key, None)
        for key, value in values.items():
            os.environ[key] = value
        Settings.reset()
        settings = Settings.load()
        self.settings = settings
        self.client.update_settings(settings)
        self.secrets.update_settings(settings)
        self.server_resources.update_settings(settings)
        return settings
