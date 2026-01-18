"""
Модуль с классом DBManager для работы с данными в БД.
Соответствует требованиям задания.
"""
import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional


class DBManager:
    """
    Класс для управления базой данных вакансий.
    Реализует все методы, требуемые в задании.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация менеджера базы данных.

        Args:
            config (Dict[str, Any]): Конфигурация подключения к БД
        """
        self.config = config
        self.connection = None

    def connect(self) -> None:
        """
        Устанавливает соединение с базой данных.
        """
        try:
            self.connection = psycopg2.connect(**self.config)
        except psycopg2.Error as e:
            print(f"✗ Ошибка подключения к БД: {e}")
            raise

    def disconnect(self) -> None:
        """
        Закрывает соединение с базой данных.
        """
        if self.connection and not self.connection.closed:
            self.connection.close()

    def get_companies_and_vacancies_count(self) -> List[Dict[str, Any]]:
        """
        Получает список всех компаний и количество вакансий у каждой компании.
        Требование: использовать SQL-запрос с JOIN.

        Returns:
            List[Dict[str, Any]]: Список словарей с названием компании и количеством вакансий

        Пример возвращаемых данных:
            [
                {'company': 'Яндекс', 'vacancies_count': 25},
                {'company': 'Сбербанк', 'vacancies_count': 18},
                ...
            ]
        """
        self.connect()

        query = """
            SELECT 
                e.name as company,
                COUNT(v.vacancy_id) as vacancies_count
            FROM employers e
            LEFT JOIN vacancies v ON e.employer_id = v.employer_id
            GROUP BY e.employer_id, e.name
            ORDER BY vacancies_count DESC, e.name
        """

        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query)
                result = cursor.fetchall()
                return [dict(row) for row in result]
        except psycopg2.Error as e:
            print(f"Ошибка при получении компаний и количества вакансий: {e}")
            return []
        finally:
            self.disconnect()

    def get_all_vacancies(self) -> List[Dict[str, Any]]:
        """
        Получает список всех вакансий с указанием названия компании,
        названия вакансии, зарплаты и ссылки на вакансию.
        Требование: использовать SQL-запрос с JOIN.

        Returns:
            List[Dict[str, Any]]: Список словарей с информацией о вакансиях

        Пример возвращаемых данных:
            [
                {
                    'company': 'Яндекс',
                    'vacancy': 'Python разработчик',
                    'salary': '150000 - 250000 руб.',
                    'url': 'https://hh.ru/vacancy/12345'
                },
                ...
            ]
        """
        self.connect()

        query = """
            SELECT 
                e.name as company,
                v.title as vacancy,
                CASE 
                    WHEN v.salary_from IS NOT NULL AND v.salary_to IS NOT NULL 
                        THEN v.salary_from || ' - ' || v.salary_to || ' ' || v.currency
                    WHEN v.salary_from IS NOT NULL 
                        THEN 'от ' || v.salary_from || ' ' || v.currency
                    WHEN v.salary_to IS NOT NULL 
                        THEN 'до ' || v.salary_to || ' ' || v.currency
                    ELSE 'Зарплата не указана'
                END as salary,
                v.url
            FROM vacancies v
            JOIN employers e ON v.employer_id = e.employer_id
            ORDER BY e.name, v.title
        """

        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query)
                result = cursor.fetchall()
                return [dict(row) for row in result]
        except psycopg2.Error as e:
            print(f"Ошибка при получении всех вакансий: {e}")
            return []
        finally:
            self.disconnect()

    def get_avg_salary(self) -> float:
        """
        Получает среднюю зарплату по вакансиям.
        Требование: использовать SQL-запрос с функцией AVG.

        Returns:
            float: Средняя зарплата (округляется до 2 знаков)
                   Возвращает 0.0 если нет данных
        """
        self.connect()

        # Используем среднее между from и to, если оба указаны
        # Или одно из значений, если указано только одно
        query = """
            SELECT ROUND(AVG(
                CASE 
                    WHEN salary_from IS NOT NULL AND salary_to IS NOT NULL 
                        THEN (salary_from + salary_to) / 2.0
                    WHEN salary_from IS NOT NULL 
                        THEN salary_from::float
                    WHEN salary_to IS NOT NULL 
                        THEN salary_to::float
                    ELSE NULL
                END
            ), 2) as avg_salary
            FROM vacancies
            WHERE salary_from IS NOT NULL OR salary_to IS NOT NULL
        """

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query)
                result = cursor.fetchone()
                return float(result[0]) if result and result[0] else 0.0
        except psycopg2.Error as e:
            print(f"Ошибка при расчете средней зарплаты: {e}")
            return 0.0
        finally:
            self.disconnect()

    def get_vacancies_with_higher_salary(self) -> List[Dict[str, Any]]:
        """
        Получает список всех вакансий, у которых зарплата выше средней по всем вакансиям.
        Требование: использовать SQL-запрос с фильтрацией WHERE.

        Returns:
            List[Dict[str, Any]]: Список вакансий с зарплатой выше средней
        """
        self.connect()

        # Подзапрос для вычисления средней зарплаты
        query = """
            SELECT 
                e.name as company,
                v.title as vacancy,
                CASE 
                    WHEN v.salary_from IS NOT NULL AND v.salary_to IS NOT NULL 
                        THEN v.salary_from || ' - ' || v.salary_to || ' ' || v.currency
                    WHEN v.salary_from IS NOT NULL 
                        THEN 'от ' || v.salary_from || ' ' || v.currency
                    WHEN v.salary_to IS NOT NULL 
                        THEN 'до ' || v.salary_to || ' ' || v.currency
                    ELSE 'Зарплата не указана'
                END as salary,
                v.url
            FROM vacancies v
            JOIN employers e ON v.employer_id = e.employer_id
            WHERE (
                CASE 
                    WHEN v.salary_from IS NOT NULL AND v.salary_to IS NOT NULL 
                        THEN (v.salary_from + v.salary_to) / 2.0
                    WHEN v.salary_from IS NOT NULL 
                        THEN v.salary_from::float
                    WHEN v.salary_to IS NOT NULL 
                        THEN v.salary_to::float
                    ELSE NULL
                END
            ) > (
                SELECT AVG(
                    CASE 
                        WHEN salary_from IS NOT NULL AND salary_to IS NOT NULL 
                            THEN (salary_from + salary_to) / 2.0
                        WHEN salary_from IS NOT NULL 
                            THEN salary_from::float
                        WHEN salary_to IS NOT NULL 
                            THEN salary_to::float
                        ELSE NULL
                    END
                )
                FROM vacancies
                WHERE salary_from IS NOT NULL OR salary_to IS NOT NULL
            )
            ORDER BY 
                CASE 
                    WHEN v.salary_from IS NOT NULL AND v.salary_to IS NOT NULL 
                        THEN (v.salary_from + v.salary_to) / 2.0
                    WHEN v.salary_from IS NOT NULL 
                        THEN v.salary_from::float
                    WHEN v.salary_to IS NOT NULL 
                        THEN v.salary_to::float
                END DESC
        """

        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query)
                result = cursor.fetchall()
                return [dict(row) for row in result]
        except psycopg2.Error as e:
            print(f"Ошибка при получении вакансий с зарплатой выше средней: {e}")
            return []
        finally:
            self.disconnect()

    def get_vacancies_with_keyword(self, keyword: str) -> List[Dict[str, Any]]:
        """
        Получает список всех вакансий, в названии которых содержатся переданные слова.
        Требование: использовать SQL-запрос с оператором LIKE.

        Args:
            keyword (str): Ключевое слово для поиска

        Returns:
            List[Dict[str, Any]]: Список вакансий, содержащих ключевое слово в названии
        """
        self.connect()

        # Используем ILIKE для регистронезависимого поиска
        query = sql.SQL("""
            SELECT 
                e.name as company,
                v.title as vacancy,
                CASE 
                    WHEN v.salary_from IS NOT NULL AND v.salary_to IS NOT NULL 
                        THEN v.salary_from || ' - ' || v.salary_to || ' ' || v.currency
                    WHEN v.salary_from IS NOT NULL 
                        THEN 'от ' || v.salary_from || ' ' || v.currency
                    WHEN v.salary_to IS NOT NULL 
                        THEN 'до ' || v.salary_to || ' ' || v.currency
                    ELSE 'Зарплата не указана'
                END as salary,
                v.url
            FROM vacancies v
            JOIN employers e ON v.employer_id = e.employer_id
            WHERE v.title ILIKE %s
            ORDER BY e.name, v.title
        """)

        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, [f'%{keyword}%'])
                result = cursor.fetchall()
                return [dict(row) for row in result]
        except psycopg2.Error as e:
            print(f"Ошибка при поиске вакансий по ключевому слову '{keyword}': {e}")
            return []
        finally:
            self.disconnect()

    def get_vacancies_by_salary_range(self, min_salary: int, max_salary: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Дополнительный метод: получает вакансии по диапазону зарплат.
        Не требуется в задании, но полезно для пользователя.

        Args:
            min_salary: Минимальная зарплата
            max_salary: Максимальная зарплата (опционально)

        Returns:
            List[Dict[str, Any]]: Список вакансий в указанном диапазоне зарплат
        """
        self.connect()

        if max_salary:
            query = """
                SELECT 
                    e.name as company,
                    v.title as vacancy,
                    CASE 
                        WHEN v.salary_from IS NOT NULL AND v.salary_to IS NOT NULL 
                            THEN v.salary_from || ' - ' || v.salary_to || ' ' || v.currency
                        WHEN v.salary_from IS NOT NULL 
                            THEN 'от ' || v.salary_from || ' ' || v.currency
                        WHEN v.salary_to IS NOT NULL 
                            THEN 'до ' || v.salary_to || ' ' || v.currency
                        ELSE 'Зарплата не указана'
                    END as salary,
                    v.url
                FROM vacancies v
                JOIN employers e ON v.employer_id = e.employer_id
                WHERE (
                    v.salary_from >= %s OR v.salary_to >= %s
                ) AND (
                    v.salary_from <= %s OR v.salary_to <= %s OR
                    (v.salary_from IS NULL AND v.salary_to IS NULL)
                )
                ORDER BY 
                    CASE 
                        WHEN v.salary_from IS NOT NULL AND v.salary_to IS NOT NULL 
                            THEN (v.salary_from + v.salary_to) / 2.0
                        WHEN v.salary_from IS NOT NULL 
                            THEN v.salary_from::float
                        WHEN v.salary_to IS NOT NULL 
                            THEN v.salary_to::float
                    END DESC NULLS LAST
            """
            params = [min_salary, min_salary, max_salary, max_salary]
        else:
            query = """
                SELECT 
                    e.name as company,
                    v.title as vacancy,
                    CASE 
                        WHEN v.salary_from IS NOT NULL AND v.salary_to IS NOT NULL 
                            THEN v.salary_from || ' - ' || v.salary_to || ' ' || v.currency
                        WHEN v.salary_from IS NOT NULL 
                            THEN 'от ' || v.salary_from || ' ' || v.currency
                        WHEN v.salary_to IS NOT NULL 
                            THEN 'до ' || v.salary_to || ' ' || v.currency
                        ELSE 'Зарплата не указана'
                    END as salary,
                    v.url
                FROM vacancies v
                JOIN employers e ON v.employer_id = e.employer_id
                WHERE v.salary_from >= %s OR v.salary_to >= %s
                ORDER BY 
                    CASE 
                        WHEN v.salary_from IS NOT NULL AND v.salary_to IS NOT NULL 
                            THEN (v.salary_from + v.salary_to) / 2.0
                        WHEN v.salary_from IS NOT NULL 
                            THEN v.salary_from::float
                        WHEN v.salary_to IS NOT NULL 
                            THEN v.salary_to::float
                    END DESC NULLS LAST
            """
            params = [min_salary, min_salary]

        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                result = cursor.fetchall()
                return [dict(row) for row in result]
        except psycopg2.Error as e:
            print(f"Ошибка при поиске вакансий по зарплате: {e}")
            return []
        finally:
            self.disconnect()

    def get_statistics(self) -> Dict[str, Any]:
        """
        Дополнительный метод: получает общую статистику по базе данных.

        Returns:
            Dict[str, Any]: Статистика по вакансиям и компаниям
        """
        self.connect()

        try:
            with self.connection.cursor() as cursor:
                # Общее количество компаний
                cursor.execute("SELECT COUNT(*) FROM employers")
                companies_count = cursor.fetchone()[0]

                # Общее количество вакансий
                cursor.execute("SELECT COUNT(*) FROM vacancies")
                vacancies_count = cursor.fetchone()[0]

                # Количество вакансий с зарплатой
                cursor.execute("""
                    SELECT COUNT(*) FROM vacancies 
                    WHERE salary_from IS NOT NULL OR salary_to IS NOT NULL
                """)
                vacancies_with_salary = cursor.fetchone()[0]

                # Средняя зарплата (используем уже готовый метод)
                avg_salary = self.get_avg_salary()

                # Самые популярные компании по количеству вакансий
                cursor.execute("""
                    SELECT e.name, COUNT(v.vacancy_id) as count
                    FROM employers e
                    JOIN vacancies v ON e.employer_id = v.employer_id
                    GROUP BY e.employer_id, e.name
                    ORDER BY count DESC
                    LIMIT 5
                """)
                top_companies = cursor.fetchall()

                return {
                    'companies_count': companies_count,
                    'vacancies_count': vacancies_count,
                    'vacancies_with_salary': vacancies_with_salary,
                    'avg_salary': avg_salary,
                    'top_companies': [
                        {'company': row[0], 'vacancies': row[1]}
                        for row in top_companies
                    ]
                }
        except psycopg2.Error as e:
            print(f"Ошибка при получении статистики: {e}")
            return {}
        finally:
            self.disconnect()

    def save_employer(self, employer_data: Dict[str, Any]) -> bool:
        """
        Сохраняет или обновляет информацию о компании в БД.

        Args:
            employer_data: Данные компании

        Returns:
            bool: True если успешно
        """
        self.connect()

        query = """
            INSERT INTO employers (employer_id, name, url, description, open_vacancies)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (employer_id) DO UPDATE SET
                name = EXCLUDED.name,
                url = EXCLUDED.url,
                description = EXCLUDED.description,
                open_vacancies = EXCLUDED.open_vacancies
        """

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, (
                    employer_data['employer_id'],
                    employer_data['name'],
                    employer_data.get('url'),
                    employer_data.get('description'),
                    employer_data.get('open_vacancies', 0)
                ))
                self.connection.commit()
                return True
        except psycopg2.Error as e:
            print(f"Ошибка при сохранении компании: {e}")
            self.connection.rollback()
            return False
        finally:
            self.disconnect()

    def save_vacancy(self, vacancy_data: Dict[str, Any]) -> bool:
        """
        Сохраняет или обновляет информацию о вакансии в БД.

        Args:
            vacancy_data: Данные вакансии

        Returns:
            bool: True если успешно
        """
        self.connect()

        query = """
            INSERT INTO vacancies (
                vacancy_id, employer_id, title, salary_from, salary_to, currency,
                city, published_date, requirement, responsibility, experience,
                employment_type, schedule, url
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (vacancy_id) DO UPDATE SET
                title = EXCLUDED.title,
                salary_from = EXCLUDED.salary_from,
                salary_to = EXCLUDED.salary_to,
                currency = EXCLUDED.currency,
                city = EXCLUDED.city,
                published_date = EXCLUDED.published_date,
                requirement = EXCLUDED.requirement,
                responsibility = EXCLUDED.responsibility,
                experience = EXCLUDED.experience,
                employment_type = EXCLUDED.employment_type,
                schedule = EXCLUDED.schedule
        """

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, (
                    vacancy_data['vacancy_id'],
                    vacancy_data['employer_id'],
                    vacancy_data['title'],
                    vacancy_data.get('salary_from'),
                    vacancy_data.get('salary_to'),
                    vacancy_data.get('currency'),
                    vacancy_data.get('city'),
                    vacancy_data.get('published_date'),
                    vacancy_data.get('requirement'),
                    vacancy_data.get('responsibility'),
                    vacancy_data.get('experience'),
                    vacancy_data.get('employment_type'),
                    vacancy_data.get('schedule'),
                    vacancy_data.get('url')
                ))
                self.connection.commit()
                return True
        except psycopg2.Error as e:
            print(f"Ошибка при сохранении вакансии: {e}")
            self.connection.rollback()
            return False
        finally:
            self.disconnect()
