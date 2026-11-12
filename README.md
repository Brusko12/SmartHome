# SmartHome

Локальная система управления умным домом для Windows 10/11 по
[ТЗ v1.0](docs/tz-v1.0.md). Реализован **этап 1: архитектура и основа**.

Это исходный проект для разработки, **ещё не готовый Windows-дистрибутив**.
На этапе 7 появится PyInstaller-сборка: запуск EXE без Python, Node.js,
терминала и интернета. Согласно ТЗ интерфейс откроется в стандартном браузере;
Electron и отдельное окно приложения не используются.

## Что работает

- React + TypeScript + Vite, React Router, Tailwind CSS, иконки Lucide.
- Страница проверки состояния с реальным запросом к backend, состояниями
  загрузки, ошибок, недоступной БД и повторной проверкой.
- FastAPI + SQLAlchemy 2 + SQLite; API только на `127.0.0.1`.
- Девять моделей, внешние ключи, ограничения и политика удаления.
- Начальная миграция Alembic и повторная инициализация без потери данных.
- Типизированная конфигурация, постоянное хранилище, базовые тесты.

CRUD устройств и комнат, симулятор, исполнение сценариев, автоматизации,
планировщик, авторизация, резервное копирование и launcher ещё не реализованы.
Для них нет фиктивных API или декоративных элементов управления.

## Структура

```text
SmartHome/
├── frontend/
│   └── src/
│       ├── hooks/             # Состояние загрузки данных
│       ├── pages/             # Страница основы проекта
│       ├── services/          # HTTP-клиент
│       ├── styles/            # Локальные стили и Tailwind
│       └── types/             # Типы ответов API
├── backend/
│   ├── app/
│   │   ├── api/               # Маршруты и зависимости HTTP
│   │   ├── core/              # Конфигурация
│   │   ├── database/          # Подключение, сессии, инициализация
│   │   ├── models/            # Девять моделей SQLAlchemy
│   │   ├── schemas/           # Pydantic и валидация JSON
│   │   ├── services/          # Прикладные проверки
│   │   ├── repositories/      # SQL-запросы
│   │   └── adapters/          # Контракт устройств
│   ├── alembic/versions/      # Версионированная схема
│   ├── tests/
│   ├── pyproject.toml
│   └── requirements.lock      # Зафиксированные проверенные зависимости
├── launcher/                 # Описание границ будущего этапа 7
├── scripts/                  # Описание будущих скриптов сборки
├── docs/                     # ТЗ, архитектура, БД, API, статус и проверки
├── .github/workflows/        # Проверки backend и frontend
├── .env.example
└── .gitignore
```

Пустые каталоги и неиспользуемые сервисы не создаются заранее.
`components` и `layouts` появятся вместе с интерфейсом на этапе 3.

## Разработка на Windows — PowerShell

Только для разработки нужны **Python 3.12** и **Node.js 22.12+** с npm.
Эти требования не распространяются на будущую готовую сборку.
Все команды первого блока выполняются из корня скачанного репозитория.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -c backend\requirements.lock -e ".\backend[dev]"
Copy-Item .env.example .env
```

Копирование `.env` необязательно: значения по умолчанию уже рабочие.
Существующий `.env` сохраняйте; не заменяйте локальную конфигурацию при обновлении.
Активация виртуального окружения и изменение ExecutionPolicy не требуются.

В первом терминале, из корня репозитория:

```powershell
cd backend
..\.venv\Scripts\python.exe -m app --reload
```

При запуске backend создаёт каталог данных и применяет недостающие миграции.
Ошибки миграции останавливают запуск; существующая база не пересоздаётся.

Во втором терминале, из корня репозитория:

```powershell
cd frontend
npm ci
npm run dev
```

Откройте **http://127.0.0.1:5173**. API: **http://127.0.0.1:8000/api/health**,
интерактивная документация FastAPI: **http://127.0.0.1:8000/docs**.
Оба процесса останавливаются через `Ctrl+C` в своих терминалах.

Vite проксирует `/api` в локальный backend. Разрешать произвольные CORS-origin
не требуется. При изменении `.env` перезапустите оба процесса.

## Разработка на Linux

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -c backend/requirements.lock -e './backend[dev]'
cp .env.example .env
cd backend
../.venv/bin/python -m app --reload
```

Во втором терминале из корня репозитория:

```bash
cd frontend
npm ci
npm run dev
```

## Конфигурация и данные

Настройки читаются из корневого `.env` независимо от текущей директории.
Переменные окружения имеют приоритет над `.env`, затем используются дефолты.

| Переменная | По умолчанию | Назначение |
|---|---|---|
| `SMARTHOME_DATA_DIR` | Каталог пользователя, см. ниже | Абсолютный путь к постоянным данным |
| `SMARTHOME_PORT` | `8000` | Порт backend: целое число от 1024 до 65535 |
| `SMARTHOME_LOG_LEVEL` | `info` | Уровень журналирования Uvicorn |

Backend всегда привязан к `127.0.0.1`; переменной для публикации в сети нет.

Путь базы на Windows:

```text
%LOCALAPPDATA%\SmartHome\data\smart_home.db
```

Если `LOCALAPPDATA` отсутствует, используется
`%USERPROFILE%\AppData\Local\SmartHome\data`. На Linux:
`$XDG_DATA_HOME/SmartHome/data/smart_home.db` либо
`~/.local/share/SmartHome/data/smart_home.db`.

Относительные пути данных отклоняются. Не указывайте временный каталог
распаковки PyInstaller. Тесты используют отдельные временные базы и не трогают
пользовательские данные. Файлы SQLite, `.env`, окружения и сборки исключены из Git.

Создание пользователя и предложение демонстрационного дома появятся позднее;
при старте нет стандартных паролей, пользователей или демоданных.

## Миграции

Автоматическая инициализация уже выполняется при старте backend. При необходимости
её можно запустить отдельно из `backend`:

```powershell
..\.venv\Scripts\python.exe -m app.database.initialize
..\.venv\Scripts\alembic.exe current
```

На Linux вместо Windows-пути используйте `../.venv/bin/python` и
`../.venv/bin/alembic`. Для изменения схемы в режиме разработки:

```powershell
..\.venv\Scripts\alembic.exe revision --autogenerate -m "describe_change"
..\.venv\Scripts\alembic.exe upgrade head
..\.venv\Scripts\alembic.exe check
```

Перед применением проверяйте сгенерированный файл: Alembic не обнаруживает все
изменения ограничений автоматически. `create_all()` не используется.

## Проверки

Из корня на Windows:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q
.\.venv\Scripts\ruff.exe check backend
.\.venv\Scripts\ruff.exe format --check backend
cd frontend
npm run build
```

На Linux:

```bash
.venv/bin/python -m pytest backend/tests -q
.venv/bin/ruff check backend
.venv/bin/ruff format --check backend
cd frontend
npm run build
```

`npm run build` выполняет строгую проверку TypeScript и собирает `frontend/dist`.
Обслуживание этого каталога через FastAPI и сборка Windows EXE относятся к этапу 7.
Текущий `npm run preview` показывает собранную статику без прокси к API;
для полной проверки этапа 1 используйте `npm run dev` вместе с backend.

## Документация и следующие этапы

- [Архитектура](docs/architecture.md)
- [Модели, связи и удаление](docs/database.md)
- [Фактическое API](docs/api.md)
- [Статус и ограничения](docs/status.md)
- [Результаты проверки этапа 1](docs/testing-stage-1.md)
- [Исходное ТЗ v1.0](docs/tz-v1.0.md)

Windows EXE, инструкция конечного пользователя и безопасные экспорт/импорт базы
будут подготовлены на соответствующих этапах. Сейчас эти функции не заявляются
готовыми. После этапа 1 разработка останавливается до отдельного задания.
