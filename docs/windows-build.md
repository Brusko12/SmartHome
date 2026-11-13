# Сборка Windows

Цель: переносимая папка для Windows 10/11 x64. Пользователь запускает EXE без
Python, Node.js, Git, IDE и терминала. Интерфейс открывается в стандартном браузере,
как требует ТЗ. Необходимые компоненты включаются PyInstaller в `resources`.

Собирать и проверять Windows EXE следует на Windows; PyInstaller не выполняет
кросс-компиляцию из Linux. Контрольная Linux-проверка не подтверждает Windows-совместимость.
Текущая Windows-сборка отдельно проверена на Windows Server 2025 runner.
[Сборка и отчёт](https://github.com/Brusko12/SmartHome/actions/runs/43391800673).

## На Windows-сборщике

Нужны Python 3.12 x64 и Node.js 22.12+. Из корня:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -c backend\requirements.lock -e ".\backend[dev,build]"
.\scripts\build_windows.ps1 -PythonExe .\.venv\Scripts\python.exe
```

Скрипт запускает backend-тесты, устанавливает frontend по lockfile, собирает его,
запускает PyInstaller, добавляет пользовательскую инструкцию и проверяет EXE.
При провале любого шага ZIP не считается готовым.

Результат:

```text
release/
├── SmartHome-Release/
│   ├── SmartHome.exe
│   ├── resources/
│   └── README.txt
├── windows-check.json
└── SmartHome-Windows.zip
```

`check_release.py` запускает EXE с PATH без Python/Node, проверяет localhost API,
UI, настройку пользователя, команду, второй запуск без второго сервера, штатное
завершение и восстановление состояния после нового запуска. Часовые пояса
проверяются с отключённой системной базой зон, через включённый tzdata.

## В облаке

В репозитории подготовлен `.github/workflows/windows-release.yml`. После
публикации исходников он запускается на Windows runner вручную или при push в main.
Артефакт `SmartHome-Windows` содержит ZIP и отчёт проверки, если сборка успешна.
Не используйте неуспешный workflow как подтверждение готовности.

## Ручная приёмка

На совместимой Windows без средств разработки: распаковать всю папку,
дважды нажать EXE, пройти настройку и демонстрацию, проверить команды, правило
движения, расписание при открытом приложении, историю, backup/restore,
сохранение после завершения и повторного запуска. Затем повторить без интернета.
Созданный через Проводник ярлык должен указывать на EXE в распакованной папке.
Эта ручная приёмка пока не выполнена в текущей Linux-среде.
