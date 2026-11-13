from getpass import getpass

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings
from app.core.errors import DomainError
from app.database.initialize import initialize_database
from app.database.session import Database
from app.services.setup import SetupInput, setup_home


def main() -> int:
    database = None
    try:
        username = input("Имя локального пользователя: ")
        password = getpass("Пароль (не менее 8 символов): ")
        if password != getpass("Повторите пароль: "):
            print("Пароли не совпадают. Данные не изменены.")
            return 1
        home_name = input("Название дома: ")
        payload = SetupInput(username=username, password=password, home_name=home_name)
        settings = Settings()
        database = Database(settings.database_path)
        initialize_database(settings, database)
        with database.sessions() as session:
            home_id = setup_home(session, payload)
        print(f"Дом готов. home_id={home_id}. Комнаты доступны через /api/rooms.")
        return 0
    except (ValidationError, ValueError):
        print("Проверьте поля: имя пользователя, пароль от 8 символов и название дома.")
        return 1
    except DomainError as error:
        print(str(error))
        return 1
    except (SQLAlchemyError, OSError):
        print("Не удалось открыть или обновить базу. Проверьте путь данных и права записи.")
        return 1
    except (EOFError, KeyboardInterrupt):
        print("Первоначальная настройка отменена.")
        return 1
    finally:
        if database is not None:
            database.close()


if __name__ == "__main__":
    raise SystemExit(main())
