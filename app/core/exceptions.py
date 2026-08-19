class AppError(Exception):
    """Базовое исключение приложения."""


class ApiError(AppError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class AuthError(ApiError):
    """Ошибка авторизации (401)."""


class ValidationError(AppError):
    def __init__(self, message: str, field_errors: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.field_errors = field_errors or {}
