# Vitago Admin

Десктопная админ-панель для гидов-клонов на **PyQt5**. Страницы ИИ-гида не входят в продукт: работаем только с приложениями `isMultiRoute = false`.

## Запуск

1. Скопируйте `.env.example` в `.env` и укажите `API_BASE_URL`.
2. Запустите скрипт:

```bash
python run.py
```

Скрипт создаст `.venv`, поставит зависимости, при необходимости скопирует `.env` и откроет GUI.

Либо вручную:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Переменные окружения

| Ключ | Назначение |
| --- | --- |
| `API_BASE_URL` | Базовый URL бэкенда, без завершающего слэша |
| `DEFAULT_SUPPORT_CHAT_URL` | Значение по умолчанию для чата поддержки в визарде |
| `API_TIMEOUT_SECONDS` | Таймаут HTTP-запросов |

## Возможности

- вход администратора
- список и карточки гидов-клонов
- визард создания клона (приложение → маршрут → точка)
- версии, маршрут, точки, промокоды
- ресурсы: загрузка, фильтр неиспользуемых, массовое удаление, CSV
- модерация отзывов
- генерация JSON маршрута из GeoJSON
- светлая и тёмная тема

## Архитектура

Слои: `presentation` → `services` → `infrastructure` → `domain`.

Паттерны: Factory (`ApplicationFactory`, `Container`), Singleton (`Settings`), Facade (`ApiClient`), Chain of Responsibility (интерцепторы), Repository, Mediator (навигация), Observer (сессия), Template Method (страницы), Strategy (темы).
