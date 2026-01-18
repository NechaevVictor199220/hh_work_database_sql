"""
Модуль для работы с API HeadHunter.
Получение данных о компаниях и их вакансиях.
"""
import requests
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class Employer:
    """Класс для представления работодателя."""
    employer_id: int
    name: str
    url: Optional[str] = None
    description: Optional[str] = None
    open_vacancies: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь для сохранения в БД."""
        return {
            'employer_id': self.employer_id,
            'name': self.name,
            'url': self.url,
            'description': self.description,
            'open_vacancies': self.open_vacancies
        }


@dataclass
class Vacancy:
    """Класс для представления вакансии."""
    vacancy_id: str
    employer_id: int
    title: str
    salary_from: Optional[int] = None
    salary_to: Optional[int] = None
    currency: Optional[str] = None
    city: Optional[str] = None
    published_date: Optional[str] = None
    requirement: Optional[str] = None
    responsibility: Optional[str] = None
    experience: Optional[str] = None
    employment_type: Optional[str] = None
    schedule: Optional[str] = None
    url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь для сохранения в БД."""
        return {
            'vacancy_id': self.vacancy_id,
            'employer_id': self.employer_id,
            'title': self.title,
            'salary_from': self.salary_from,
            'salary_to': self.salary_to,
            'currency': self.currency,
            'city': self.city,
            'published_date': self.published_date,
            'requirement': self.requirement,
            'responsibility': self.responsibility,
            'experience': self.experience,
            'employment_type': self.employment_type,
            'schedule': self.schedule,
            'url': self.url
        }

    @property
    def avg_salary(self) -> Optional[float]:
        """Вычисляет среднюю зарплату."""
        if self.salary_from and self.salary_to:
            return (self.salary_from + self.salary_to) / 2
        elif self.salary_from:
            return float(self.salary_from)
        elif self.salary_to:
            return float(self.salary_to)
        return None


class HeadHunterAPI:
    """
    Класс для работы с API HeadHunter.
    Получает данные о компаниях и вакансиях.
    """

    BASE_URL = "https://api.hh.ru"

    def __init__(self, delay: float = 0.2):
        """
        Инициализация API клиента.

        Args:
            delay: Задержка между запросами (в секундах) для соблюдения лимитов API
        """
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
        })
        self.delay = delay

    def get_employer(self, employer_id: int) -> Optional[Employer]:
        """
        Получает информацию о компании по ID.

        Args:
            employer_id: ID компании на HH

        Returns:
            Employer: Объект компании или None при ошибке
        """
        try:
            url = f"{self.BASE_URL}/employers/{employer_id}"
            response = self.session.get(url, timeout=10)

            # Проверяем статус код
            if response.status_code == 404:
                print(f"  Компания с ID {employer_id} не найдена")
                return None
            elif response.status_code == 400:
                print(f"  Неверный запрос для компании {employer_id}")
                return None

            response.raise_for_status()

            data = response.json()

            # Проверяем, что данные корректны
            if 'id' not in data or 'name' not in data:
                print(f"  Некорректные данные для компании {employer_id}")
                return None

            return Employer(
                employer_id=data.get('id'),
                name=data.get('name'),
                url=data.get('alternate_url'),
                description=data.get('description'),
                open_vacancies=data.get('open_vacancies', 0)
            )

        except requests.RequestException as e:
            print(f"  Ошибка при получении компании {employer_id}: {e}")
            return None
        finally:
            time.sleep(self.delay)

    def get_vacancies_by_employer(self, employer_id: int,
                                 only_with_salary: bool = True) -> List[Vacancy]:
        """
        Получает все вакансии компании.

        Args:
            employer_id: ID компании
            only_with_salary: Только вакансии с указанной зарплатой

        Returns:
            List[Vacancy]: Список объектов вакансий
        """
        vacancies = []
        page = 0
        per_page = 50  # Уменьшим для надежности

        while True:
            try:
                params = {
                    'employer_id': employer_id,
                    'page': page,
                    'per_page': per_page,
                    'only_with_salary': only_with_salary
                }

                response = self.session.get(
                    f"{self.BASE_URL}/vacancies",
                    params=params,
                    timeout=15
                )

                # Проверяем статус код
                if response.status_code == 400:
                    print(f"  Неверный запрос для вакансий компании {employer_id}")
                    break

                response.raise_for_status()
                data = response.json()

                # Проверяем наличие данных
                if 'items' not in data:
                    print(f"  Некорректный ответ для компании {employer_id}")
                    break

                # Обрабатываем вакансии текущей страницы
                items = data.get('items', [])
                for item in items:
                    vacancy = self._parse_vacancy_item(item, employer_id)
                    if vacancy:
                        vacancies.append(vacancy)

                # Проверяем, есть ли следующая страница
                pages = data.get('pages', 0)
                found = data.get('found', 0)

                # Если вакансий нет или просмотрели все страницы
                page += 1
                if page >= pages or found == 0 or page >= 10:  # Ограничим 10 страницами
                    break

                # Отображаем прогресс
                if page % 2 == 0:
                    print(f"    Страница {page}, вакансий: {len(vacancies)}")

            except requests.RequestException as e:
                print(f"  Ошибка при получении вакансий компании {employer_id}: {e}")
                break
            except Exception as e:
                print(f"  Неожиданная ошибка: {e}")
                break
            finally:
                time.sleep(self.delay)

        return vacancies

    def _parse_vacancy_item(self, item: Dict[str, Any], employer_id: int) -> Optional[Vacancy]:
        """
        Парсит данные вакансии из API ответа.

        Args:
            item: Словарь с данными вакансии от API
            employer_id: ID работодателя

        Returns:
            Vacancy: Объект вакансии
        """
        try:
            # Проверяем обязательные поля
            if not item.get('id') or not item.get('name'):
                return None

            # Обработка зарплаты
            salary_data = item.get('salary')
            salary_from = salary_data.get('from') if salary_data else None
            salary_to = salary_data.get('to') if salary_data else None
            currency = salary_data.get('currency') if salary_data else None

            # Обработка требований и обязанностей
            snippet = item.get('snippet', {})

            return Vacancy(
                vacancy_id=str(item.get('id')),
                employer_id=employer_id,
                title=item.get('name', ''),
                salary_from=salary_from,
                salary_to=salary_to,
                currency=currency,
                city=item.get('area', {}).get('name'),
                published_date=item.get('published_at'),
                requirement=snippet.get('requirement'),
                responsibility=snippet.get('responsibility'),
                experience=item.get('experience', {}).get('name'),
                employment_type=item.get('employment', {}).get('name'),
                schedule=item.get('schedule', {}).get('name'),
                url=item.get('alternate_url')
            )
        except Exception as e:
            print(f"  Ошибка при парсинге вакансии: {e}")
            return None

    def get_all_employers(self, company_ids: List[int]) -> List[Employer]:
        """
        Получает информацию о нескольких компаниях.

        Args:
            company_ids: Список ID компаний

        Returns:
            List[Employer]: Список объектов компаний
        """
        employers = []
        successful = 0

        print(f"Получение информации о {len(company_ids)} компаниях...")
        print("=" * 50)

        for i, company_id in enumerate(company_ids, 1):
            print(f"[{i}/{len(company_ids)}] Компания ID: {company_id}", end="")

            employer = self.get_employer(company_id)
            if employer:
                employers.append(employer)
                successful += 1
                print(f" ✓ {employer.name}")
            else:
                print(f" ✗ Не удалось загрузить")

            # Пауза между запросами
            time.sleep(0.3)

        print("=" * 50)
        print(f"✓ Успешно загружено: {successful}/{len(company_ids)} компаний")

        return employers

    def get_all_vacancies(self, company_ids: List[int]) -> List[Vacancy]:
        """
        Получает все вакансии для списка компаний.

        Args:
            company_ids: Список ID компаний

        Returns:
            List[Vacancy]: Список всех вакансий
        """
        all_vacancies = []
        total_companies = len(company_ids)

        print(f"\nЗагрузка вакансий для {total_companies} компаний...")
        print("=" * 50)

        for i, company_id in enumerate(company_ids, 1):
            print(f"\n[{i}/{total_companies}] Компания ID: {company_id}")

            vacancies = self.get_vacancies_by_employer(company_id)

            if vacancies:
                all_vacancies.extend(vacancies)
                print(f"  ✓ Загружено вакансий: {len(vacancies)}")
            else:
                print(f"  ⚠ Вакансий не найдено")

            # Увеличиваем задержку между компаниями
            time.sleep(0.5)

        print("=" * 50)
        print(f"\n✓ Всего загружено вакансий: {len(all_vacancies)}")

        return all_vacancies


# Добавим в конец файла src/api.py

def test_api_connection():
    """Тестирование подключения к API HH.ru"""
    print("Тестирование подключения к API HH.ru...")
    print("=" * 50)

    api = HeadHunterAPI()

    # Тестовые ID компаний, которые точно работают
    test_ids = [15478, 3529, 78638]

    for test_id in test_ids:
        print(f"\nТест компании ID: {test_id}")

        employer = api.get_employer(test_id)
        if employer:
            print(f"✓ Успешно: {employer.name}")
            print(f"  Открытых вакансий: {employer.open_vacancies}")

            # Тест вакансий (только 1 страница для теста)
            print("  Тест загрузки вакансий...")
            vacancies = api.get_vacancies_by_employer(test_id)
            print(f"  Загружено вакансий: {len(vacancies)}")
        else:
            print(f"✗ Не удалось загрузить")

    print("\n" + "=" * 50)
    print("Тестирование завершено.")


if __name__ == "__main__":
    test_api_connection()
