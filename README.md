# SmartHome

Локальная система управления виртуальным умным домом для Windows 10/11 по
[ТЗ v1.0](docs/tz-v1.0.md). React/TypeScript/Vite, Python/FastAPI,
SQLAlchemy/Alembic и SQLite. Интерфейс открывается в стандартном браузере.

**Этапы 1–6 реализованы и проверены. Windows-сборка подготовлена к проверке;
готовность Windows EXE и чистой установки пока не подтверждена.**

## Возможности

- Главная панель с реальными сводными данными и быстрыми сценариями.
- Комнаты, иконки, устройства, поиск, фильтры и перенос при удалении комнаты.
- Шесть типов устройств: лампа, термостат, розетка, движение, температура/влажность, ТВ.
- Команды, типизированные параметры и постоянное сохранение состояний.
- Конструктор сценариев и правил, порядок действий, условия и результаты выполнения.
- Движение, изменение состояния, пересечение порога и время как триггеры.
- Защита от циклов, глубина до 8 и общий бюджет 64 действий на цепочку.
- Расписания по дням недели с вычислением следующего запуска в часовом поясе дома.
- Детерминированная симуляция температуры, мощности, энергии и сброса движения.
- Локальная авторизация, настройка пользователя, смена пароля, CSRF и сессии в SQLite.
- История с фильтрами и пагинацией; диагностика сервера, базы и фоновых задач.
- Настройки, экспорт/импорт SQLite с проверкой и страховочной копией.
- Предлагаемый пользователю демонстрационный дом: 11 устройств, три сценария,
  правило движения и утреннее расписание. Повторно данные не создаются.

Физические устройства, MQTT, Home Assistant и облачные сервисы не подключаются.
Веб-шрифты и CDN не используются. Для работы готовой сборки интернет не нужен;
сеть требуется только при установке инструментов и сборке исходников.

## Запуск разработки — Windows PowerShell

Только разработчику нужны Python 3.12 и Node.js 22.12+ с npm. Из корня проекта:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -c backend\requirements.lock -e ".\backend[dev]"
Copy-Item .env.example .env
```

Копировать `.env` необязательно: дефолты рабочие. Существующую конфигурацию не
перезаписывайте. Активация venv и изменение ExecutionPolicy не требуются.

Первый терминал:

```powershell
cd backend
..\.venv\Scripts\python.exe -m app --reload
```

Второй терминал из корня:

```powershell
cd frontend
npm ci
npm run dev
```

Откройте http://127.0.0.1:5173. Создайте пользователя и дом в интерфейсе, затем
примите или отклоните предложение демонстрации. Стандартного пароля нет.
Backend: http://127.0.0.1:8000. OpenAPI: `/docs`. Для изменяющих API кроме входа
и первоначальной регистрации нужны сессия и CSRF-заголовок; браузерный UI
отправляет их автоматически. Dev-процессы завершаются через `Ctrl+C`.

## Запуск разработки — Linux

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -c backend/requirements.lock -e './backend[dev]'
cd backend
../.venv/bin/python -m app --reload
```

В другом терминале из корня:

```bash
cd frontend
npm ci
npm run dev
```

## Один сервер и launcher из исходников

Сначала соберите frontend:

```bash
cd frontend
npm ci
npm run build
```

Затем из корня проекта на Windows:

```powershell
.\.venv\Scripts\python.exe launcher\main.py
```

На Linux:

```bash
.venv/bin/python launcher/main.py
```

Launcher выбирает свободный порт, проверяет готовность, открывает браузер и
переиспользует существующий экземпляр. Собранные ресурсы обслуживает FastAPI.
Для завершения используйте «Состояние системы → Завершить SmartHome».
Закрытие вкладки не останавливает сервер. `--no-browser` нужен для автоматических
проверок; обычный запуск не требует аргументов.

## База и конфигурация

Основная база Windows:

```text
%LOCALAPPDATA%\SmartHome\data\smart_home.db
```

На Linux: `$XDG_DATA_HOME/SmartHome/data/smart_home.db` или
`~/.local/share/SmartHome/data/smart_home.db`. База не хранится в папке временной
распаковки PyInstaller. Перенос папки программы не переносит пользовательские
данные: используйте экспорт/импорт в настройках.

| Переменная | Дефолт | Назначение |
|---|---|---|
| `SMARTHOME_DATA_DIR` | Каталог профиля пользователя | Абсолютный путь постоянных данных |
| `SMARTHOME_PORT` | `8000` | Порт dev-backend; launcher выбирает свободный автоматически |
| `SMARTHOME_LOG_LEVEL` | `info` | Уровень журналирования |
| `SMARTHOME_BACKGROUND_TASKS` | `true` | `false` — отключение фоновых задач для контролируемых тестов |
| `SMARTHOME_FRONTEND_DIR` | `frontend/dist` в ресурсах проекта/сборки | Переопределение каталога собранного интерфейса |

В разработке `.env` читается из корня репозитория независимо от cwd. В готовой
сборке необязательный `.env` читается рядом с EXE. Переменные окружения имеют
приоритет. API всегда привязан к `127.0.0.1`; публикации во внешнюю сеть нет.
Пользовательские настройки и параметры симуляции сохраняются в SQLite.

## Миграции и первоначальная настройка

При старте применяются только недостающие миграции Alembic. База не пересоздаётся.
Из `backend` на Windows можно выполнить отдельно:

```powershell
..\.venv\Scripts\python.exe -m app.database.initialize
..\.venv\Scripts\alembic.exe current
..\.venv\Scripts\alembic.exe check
```

Linux-пути: `../.venv/bin/python` и `../.venv/bin/alembic`.
Изменения схемы добавляются новыми ревизиями; уже применённые ревизии не редактируют.
Сгенерированные миграции проверяют до применения. `create_all()` не используется.

UI первоначальной настройки является основным способом. Для разработчика
сохранён контролируемый `python -m app.database.setup` из backend: пароль
вводится без отображения; повторная настройка с верным паролем не дублирует дом.

## Проверки

Из корня на Windows:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q
.\.venv\Scripts\ruff.exe check backend launcher scripts
.\.venv\Scripts\ruff.exe format --check backend launcher scripts
.\.venv\Scripts\python.exe scripts\check_release.py launcher\main.py
cd frontend
npm run build
```

На Linux вместо `.venv\Scripts\…` используйте `.venv/bin/…`.
`check_release.py` проверяет настоящий процесс: статический UI, авторизацию,
команду, второй запуск, завершение, повторный запуск и сохранённое состояние.
Для EXE проверка ограничивает PATH дочернего процесса системным каталогом.
Это не заменяет ручную проверку на чистой Windows и без интернета.

## Windows-дистрибутив

Сборка должна выполняться на Windows. Описание и команды:
[docs/windows-build.md](docs/windows-build.md). В GitHub Actions подготовлен
workflow `Windows portable build`: EXE, проверка запуска и ZIP готовой папки.
Наличие workflow в исходниках не означает, что сборка уже прошла.

## Структура

```text
frontend/src/       UI: layouts, pages, components, hooks, services, types, styles
backend/app/api/   Маршруты, HTTP-ошибки и защита запросов
backend/app/services/       Бизнес-логика, автоматизации, runtime, backup
backend/app/repositories/   Запросы к БД
backend/app/models/         Девять основных моделей и служебные сессии
backend/app/schemas/        Pydantic-контракты и валидация
backend/app/database/       SQLite, транзакции, блокировка и миграции
backend/app/adapters/       Контракт, реестр и VirtualDeviceAdapter
backend/alembic/versions/   Версионированная схема
backend/tests/             Автоматизированные проверки
launcher/                  Запуск приложения и управление процессом
packaging/                 PyInstaller spec
scripts/                   Сборка и проверка дистрибутива
.github/workflows/         CI и Windows-сборка
```

Бизнес-логика не находится в React или маршрутах API. Адаптеры не владеют отдельным
хранилищем состояний. SQLite, `.env`, виртуальные окружения, node_modules и
результаты сборки исключены из Git.

Документация: [архитектура](docs/architecture.md), [БД](docs/database.md),
[API](docs/api.md), [резервные копии](docs/backup.md), [статус](docs/status.md),
[отчёт проверки](docs/testing-report.md), [пользовательская инструкция](docs/USER_README.txt).
