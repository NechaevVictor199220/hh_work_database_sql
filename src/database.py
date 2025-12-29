"""
Модуль для создания и управления базой данных PostgreSQL.
Создание БД, таблиц и выполнение DDL операций.
"""
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from typing import Dict, Any, List


class DatabaseManager:
    """
    Класс для управления базой данных PostgreSQL.
    Создает БД, таблицы и выполняет миграции.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация менеджера БД.

        Args:
            config: Конфигурация подключения к PostgreSQL
                   Должен содержать: host, user, password, port
        """
        self.config = config.copy()  # Копируем конфигурацию
        self.connection = None

    def connect_to_postgres(self) -> psycopg2.extensions.connection:
        """
        Подключается к серверу PostgreSQL (без указания конкретной БД).

        Returns:
            Подключение к PostgreSQL серверу

        Raises:
            psycopg2.OperationalError: Если не удается подключиться
        """
        # Подключаемся к серверу PostgreSQL (к базе 'postgres' по умолчанию)
        pg_config = self.config.copy()
        pg_config['database'] = 'postgres'  # Подключаемся к системной БД

        try:
            conn = psycopg2.connect(**pg_config)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            print("✓ Подключение к PostgreSQL серверу установлено")
            return conn
        except psycopg2.OperationalError as e:
            print(f"✗ Не удалось подключиться к PostgreSQL: {e}")
            raise

    def create_database(self, db_name: str = "hh_vacancies") -> None:
        """
        Создает базу данных, если она не существует.
        Требование: реализовать код автоматического создания БД.

        Args:
            db_name: Название базы данных

        Raises:
            Exception: Если не удается создать БД
        """
        conn = None

        try:
            # Подключаемся к серверу PostgreSQL
            conn = self.connect_to_postgres()
            cursor = conn.cursor()

            # Проверяем, существует ли база данных
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (db_name,)
            )

            if cursor.fetchone():
                print(f"✓ База данных '{db_name}' уже существует")
            else:
                # Создаем новую базу данных
                create_db_query = sql.SQL("CREATE DATABASE {}").format(
                    sql.Identifier(db_name)
                )
                cursor.execute(create_db_query)
                print(f"✓ База данных '{db_name}' успешно создана")

            # Обновляем конфигурацию для использования новой БД
            self.config['database'] = db_name

        except psycopg2.Error as e:
            print(f"✗ Ошибка при создании базы данных: {e}")
            raise
        finally:
            if conn:
                cursor.close()
                conn.close()

    def connect(self) -> psycopg2.extensions.connection:
        """
        Подключается к конкретной базе данных.

        Returns:
            Подключение к базе данных

        Raises:
            psycopg2.OperationalError: Если не удается подключиться
        """
        if not self.connection or self.connection.closed:
            try:
                self.connection = psycopg2.connect(**self.config)
                print(f"✓ Подключение к базе данных '{self.config['database']}' установлено")
            except psycopg2.OperationalError as e:
                print(f"✗ Не удалось подключиться к базе данных: {e}")
                raise

        return self.connection

    def disconnect(self) -> None:
        """Закрывает подключение к базе данных."""
        if self.connection and not self.connection.closed:
            self.connection.close()
            print("✓ Подключение к базе данных закрыто")

    def create_tables(self) -> None:
        """
        Создает таблицы в базе данных.
        Требование: создать таблицы для организаций и вакансий с FK связью.
        """
        conn = None

        try:
            conn = self.connect()
            cursor = conn.cursor()

            print("Создание таблиц...")

            # 1. Таблица работодателей (компаний)
            create_employers_table = """
            CREATE TABLE IF NOT EXISTS employers (
                employer_id INTEGER PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                url VARCHAR(500),
                description TEXT,
                open_vacancies INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """

            # 2. Таблица вакансий
            create_vacancies_table = """
            CREATE TABLE IF NOT EXISTS vacancies (
                vacancy_id VARCHAR(50) PRIMARY KEY,
                employer_id INTEGER NOT NULL,
                title VARCHAR(500) NOT NULL,
                salary_from INTEGER,
                salary_to INTEGER,
                currency VARCHAR(10),
                city VARCHAR(100),
                published_date TIMESTAMP,
                requirement TEXT,
                responsibility TEXT,
                experience VARCHAR(100),
                employment_type VARCHAR(100),
                schedule VARCHAR(100),
                url VARCHAR(500),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employer_id) REFERENCES employers(employer_id) ON DELETE CASCADE
            )
            """

            # 3. Индексы для ускорения поиска
            create_indexes = """
            CREATE INDEX IF NOT EXISTS idx_vacancies_employer_id ON vacancies(employer_id);
            CREATE INDEX IF NOT EXISTS idx_vacancies_salary ON vacancies(salary_from, salary_to);
            CREATE INDEX IF NOT EXISTS idx_vacancies_title ON vacancies USING gin(to_tsvector('russian', title));
            CREATE INDEX IF NOT EXISTS idx_employers_name ON employers(name);
            """

            # Выполняем запросы
            cursor.execute(create_employers_table)
            print("  ✓ Таблица 'employers' создана/проверена")

            cursor.execute(create_vacancies_table)
            print("  ✓ Таблица 'vacancies' создана/проверена")

            cursor.execute(create_indexes)
            print("  ✓ Индексы созданы/проверены")

            # Фиксируем изменения
            conn.commit()
            print("✓ Все таблицы успешно созданы")

        except psycopg2.Error as e:
            if conn:
                conn.rollback()
            print(f"✗ Ошибка при создании таблиц: {e}")
            raise
        finally:
            if conn:
                cursor.close()

    def check_tables_exist(self) -> bool:
        """
        Проверяет, существуют ли необходимые таблицы.

        Returns:
            bool: True если все таблицы существуют
        """
        conn = None

        try:
            conn = self.connect()
            cursor = conn.cursor()

            # Проверяем существование таблиц
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'employers'
                )
            """)
            employers_exists = cursor.fetchone()[0]

            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'vacancies'
                )
            """)
            vacancies_exists = cursor.fetchone()[0]

            return employers_exists and vacancies_exists

        except psycopg2.Error as e:
            print(f"Ошибка при проверке таблиц: {e}")
            return False
        finally:
            if conn:
                cursor.close()

    def clear_all_data(self) -> None:
        """
        Очищает все данные из таблиц (но не удаляет таблицы).
        Используется для тестирования.
        """
        conn = None

        try:
            conn = self.connect()
            cursor = conn.cursor()

            # Отключаем триггеры для ускорения
            cursor.execute("SET session_replication_role = 'replica'")

            # Очищаем таблицы в правильном порядке (из-за FK)
            cursor.execute("TRUNCATE TABLE vacancies CASCADE")
            cursor.execute("TRUNCATE TABLE employers CASCADE")

            # Включаем триггеры обратно
            cursor.execute("SET session_replication_role = 'origin'")

            conn.commit()
            print("✓ Все данные очищены")

        except psycopg2.Error as e:
            if conn:
                conn.rollback()
            print(f"✗ Ошибка при очистке данных: {e}")
            raise
        finally:
            if conn:
                cursor.close()

    def drop_tables(self) -> None:
        """
        Удаляет все таблицы из базы данных.
        Внимание: удаляет все данные!
        """
        conn = None

        confirm = input("Вы уверены, что хотите удалить ВСЕ таблицы? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Отменено")
            return

        try:
            conn = self.connect()
            cursor = conn.cursor()

            # Удаляем таблицы в правильном порядке (из-за FK)
            cursor.execute("DROP TABLE IF EXISTS vacancies CASCADE")
            print("  ✓ Таблица 'vacancies' удалена")

            cursor.execute("DROP TABLE IF EXISTS employers CASCADE")
            print("  ✓ Таблица 'employers' удалена")

            conn.commit()
            print("✓ Все таблицы удалены")

        except psycopg2.Error as e:
            if conn:
                conn.rollback()
            print(f"✗ Ошибка при удалении таблиц: {e}")
            raise
        finally:
            if conn:
                cursor.close()

    def get_table_info(self) -> Dict[str, Any]:
        """
        Получает информацию о таблицах и количестве записей.

        Returns:
            Dict с информацией о таблицах
        """
        conn = None

        try:
            conn = self.connect()
            cursor = conn.cursor()

            info = {}

            # Количество записей в employers
            cursor.execute("SELECT COUNT(*) FROM employers")
            info['employers_count'] = cursor.fetchone()[0]

            # Количество записей в vacancies
            cursor.execute("SELECT COUNT(*) FROM vacancies")
            info['vacancies_count'] = cursor.fetchone()[0]

            # Средняя зарплата
            cursor.execute("""
                SELECT AVG((salary_from + salary_to) / 2) 
                FROM vacancies 
                WHERE salary_from IS NOT NULL AND salary_to IS NOT NULL
            """)
            avg_result = cursor.fetchone()[0]
            info['avg_salary'] = round(float(avg_result), 2) if avg_result else 0

            return info

        except psycopg2.Error as e:
            print(f"Ошибка при получении информации: {e}")
            return {'employers_count': 0, 'vacancies_count': 0, 'avg_salary': 0}
        finally:
            if conn:
                cursor.close()

    def execute_sql_file(self, file_path: str) -> None:
        """
        Выполняет SQL команды из файла.

        Args:
            file_path: Путь к SQL файлу
        """
        if not os.path.exists(file_path):
            print(f"Файл {file_path} не найден")
            return

        conn = None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                sql_commands = f.read()

            conn = self.connect()
            cursor = conn.cursor()

            # Выполняем команды
            cursor.execute(sql_commands)
            conn.commit()

            print(f"✓ SQL команды из {file_path} выполнены успешно")

        except psycopg2.Error as e:
            if conn:
                conn.rollback()
            print(f"✗ Ошибка при выполнении SQL файла: {e}")
        except Exception as e:
            print(f"✗ Ошибка при чтении файла: {e}")
        finally:
            if conn:
                cursor.close()


# Функция для создания и настройки БД одним вызовом
def setup_database(config: Dict[str, Any]) -> DatabaseManager:
    """
    Создает и настраивает базу данных.
    Основная функция для использования в main.py.

    Args:
        config: Конфигурация подключения

    Returns:
        DatabaseManager: Настроенный менеджер БД
    """
    print("\n" + "=" * 60)
    print("НАСТРОЙКА БАЗЫ ДАННЫХ")
    print("=" * 60)

    try:
        # Создаем менеджер БД
        db_manager = DatabaseManager(config)

        # Создаем базу данных (если не существует)
        db_name = config.get('database', 'hh_vacancies')
        db_manager.create_database(db_name)

        # Создаем таблицы
        db_manager.create_tables()

        # Проверяем результат
        if db_manager.check_tables_exist():
            print("\n✓ База данных настроена и готова к работе")

            # Показываем информацию
            info = db_manager.get_table_info()
            print(f"  Компаний в БД: {info['employers_count']}")
            print(f"  Вакансий в БД: {info['vacancies_count']}")

            if info['avg_salary'] > 0:
                print(f"  Средняя зарплата: {info['avg_salary']:,.2f} руб.")
        else:
            print("\n✗ Не удалось создать таблицы")

        return db_manager

    except Exception as e:
        print(f"\n✗ Ошибка при настройке базы данных: {e}")
        raise


# Для корректной работы импортов
import os
