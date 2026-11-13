# REST API SmartHome

Префикс `/api`, адрес разработки `http://127.0.0.1:8000`. Launcher выбирает
свободный порт. Актуальные схемы запросов и ответов: `/docs` и `/openapi.json`.
API принимает JSON, кроме двоичного импорта резервной копии.

## Доступ и ошибки

Публичны только `/api/health`, `/api/auth/status`, `/api/auth/register` и
`/api/auth/login`. Остальные маршруты требуют cookie `smarthome_session`.
Для изменяющих защищённых запросов нужен заголовок `X-CSRF-Token` со значением
cookie `smarthome_csrf`. Origin, если передан, должен совпадать с адресом сервера.
Работайте через один адрес: `127.0.0.1`. Cookie сессии HttpOnly, SameSite=Strict;
соединение HTTP допустимо только на loopback. Сессия хранится в SQLite в виде
хеша токена и действует не более 12 часов.

Коды: 401 — требуется вход, 403 — отклонён CSRF/Origin, 404 — объект отсутствует,
409 — конфликт, 422 — невалидные поля/команда, 503 — недоступно хранилище/адаптер.
Доменные ошибки: `{"detail":{"code":"conflict","message":"…"}}`.
Валидация FastAPI возвращает массив `detail`. Внутренние SQL-ошибки не раскрываются.

## Основные маршруты

| Метод и путь | Назначение |
|---|---|
| GET `/health` | Соединение с БД и ревизия миграций; 200 или 503 |
| GET `/auth/status` | Нужна ли первоначальная настройка |
| POST `/auth/register` | Создать первого пользователя, дом и четыре комнаты |
| POST `/auth/login` | Вход и выдача cookie |
| GET `/auth/me` | Текущий пользователь |
| POST `/auth/logout` | Завершить текущую сессию |
| POST `/auth/password` | Сменить пароль, отозвать все сессии |
| GET `/homes` | Дома пользователя |
| GET `/dashboard?home_id=1` | Сводка, климат, события и сценарии |
| GET/POST `/rooms` | Список / создание комнаты |
| GET/PATCH/DELETE `/rooms/{id}` | Просмотр / изменение / удаление |
| GET/POST `/devices` | Список / создание устройства |
| GET/PATCH/DELETE `/devices/{id}` | Просмотр / изменение / удаление |
| GET `/devices/{id}/state` | Сохранённое состояние |
| POST `/devices/{id}/command` | Проверенная команда |
| GET/POST `/automations` | Список / создание сценария или правила |
| GET/PATCH/DELETE `/automations/{id}` | Просмотр / изменение / удаление |
| POST `/automations/{id}/execute` | Запуск сценария или ручное тестирование правила |
| GET/POST `/schedules` | Список / создание расписания |
| GET/PATCH/DELETE `/schedules/{id}` | Просмотр / изменение / удаление |
| GET `/events?home_id=1` | История с фильтрами и пагинацией |
| GET `/events/{id}` | Детали события, включая before/after |
| GET `/event-types?home_id=1` | Доступные типы событий |
| GET `/event-devices?home_id=1` | Устройства, включая удалённые из истории |
| GET/PATCH `/settings?home_id=1` | Настройки дома, часового пояса и симуляции |
| POST `/demo?home_id=1` | Однократно создать демоданные; `{"confirm":true}` |
| POST `/demo/skip?home_id=1` | Отказаться от демоданных |
| GET `/system/status` | Реальная диагностика приложения |
| GET `/system/database` | Путь, ревизия, целостность и счётчики БД |
| GET `/system/backup` | Скачать согласованную SQLite-копию |
| POST `/system/restore` | Проверить и восстановить копию |
| POST `/system/shutdown` | Корректно остановить launcher; в dev-режиме 409 |

Первоначальная настройка:

```json
{"username":"owner","password":"your-unique-password","home_name":"Мой дом","timezone":"Asia/Yakutsk"}
```

Повторная регистрация после настройки отклоняется с 409. Пароль по умолчанию
отсутствует; ограничения полей описаны в OpenAPI. Смена пароля принимает
`current_password`, `new_password`.

## Комнаты и устройства

Списки: `{"items":[],"total":0,"limit":50,"offset":0}`; limit 1–100.
Комнаты фильтруются по home_id; устройства — home_id, room_id, device_type.
Удаление непустой комнаты требует `?move_devices_to=<id>` другой комнаты того же
дома. Удаление устройства сохраняет его историю и снимок названия.

```json
{"home_id":1,"name":"Кабинет","icon":"house"}
```

```json
{"room_id":1,"name":"Лампа","device_type":"light","parameters":{}}
```

Тип и адаптер после создания не меняются; используется только `virtual`.
Параметры PATCH заменяются целиком с проверкой значений. Прямое редактирование
состояния отсутствует. Команда:

```json
{"command":"set_brightness","params":{"brightness":60}}
```

| Тип | Команды и параметры |
|---|---|
| light, outlet, tv | turn_on / turn_off, `{}` |
| light | set_brightness: brightness 0–100; set_color: color #RRGGBB |
| thermostat | set_target_temperature: temperature 5–35; set_mode: mode Off/Heating/Cooling/Auto/Eco |
| motion_sensor | simulate_motion / reset_motion, `{}` |
| climate_sensor | simulate_reading: temperature −40–125, humidity 0–100 |
| tv | set_volume: volume 0–100; mute: muted true/false |

Числовые строки и лишние поля отклоняются. Розетка принимает
`parameters.nominal_power_w` (0 < значение ≤ 10000, по умолчанию 60 Вт),
датчик движения — `reset_after_seconds` (1–3600, по умолчанию 30).
Энергия рассчитывается по мощности и времени; температура и климат обновляются
фоновым симулятором. Изменение состояния и его событие фиксируются транзакцией.
Ответ команды содержит окончательное состояние после запущенных правил.

## Сценарии, правила и расписания

Списки требуют home_id. Сценарий: kind=scenario, trigger=null; правило:
kind=rule с trigger. Действие команды:
`{"type":"command","device_id":1,"command":"turn_on","params":{},"optional":false}`.
Вложенный сценарий: `{"type":"scenario","automation_id":1,"optional":false}`.
Триггеры: motion, state_changed, threshold и time. Условия: eq/ne/gt/lt/between.
Точные варианты полей дискриминированных структур описаны в OpenAPI.

Действия выполняются по порядку. Обязательная ошибка останавливает оставшиеся
действия; необязательное отсутствующее устройство пропускается. Результат
содержит статусы шагов. Глубина цепочки ограничена восемью, бюджет — 64 действия,
повторное срабатывание правила ограничено интервалом в одну секунду.

Расписание задаёт hour, minute, weekdays (0 = понедельник), enabled и либо
сценарий automation_id, либо actions. Время трактуется в часовом поясе дома.
При запуске приложения вычисляется следующее событие; пропущенные при выключенном
приложении события не воспроизводятся. Подробности надёжности: [архитектура](architecture.md).

## История и резервные копии

Фильтры истории: home_id, device_id, event_type, status success/info/error,
date_from, date_to в формате YYYY-MM-DD, order asc/desc, limit (по умолчанию 25),
offset. Границы дат трактуются в часовом поясе дома.

Импорт: двоичное тело SQLite, `Content-Type: application/octet-stream`,
`X-Confirm-Restore: true`, cookie и CSRF как у других защищённых операций.
Лимит 2 ГБ, проверка до замены, автоматическая страховочная копия.
Успешный импорт отзывает сессии: войдите с паролем из импортированной базы.
[Полная инструкция](backup.md).
