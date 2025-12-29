"""
Основной модуль программы - точка входа.
Соответствует требованиям задания.
"""
import sys
import os
from typing import List, Dict, Any

# Добавляем папку src в путь Python для корректного импорта
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from src.api import HeadHunterAPI, Employer, Vacancy
    from src.config import get_company_ids
    from src.database import setup_database
    from src.db_manager import DBManager
    from src.utils import load_config, print_vacancy

    print("✓ Все модули успешно импортированы")
except ImportError as e:
    print(f"✗ Ошибка импорта: {e}")
    print("Проверьте структуру проекта и наличие всех файлов")
    sys.exit(1)


def print_header(text: str) -> None:
    """Печатает заголовок с рамкой."""
    print("\n" + "=" * 60)
    print(text.center(60))
    print("=" * 60)


def print_menu(title: str, items: List[str]) -> None:
    """Печатает меню."""
    print_header(title)
    for i, item in enumerate(items, 1):
        print(f"{i}. {item}")


def load_data_from_hh(db_manager: DBManager) -> None:
    """
    Загружает данные с HH.ru и сохраняет их в базу данных.
    Требование: заполнить таблицы данными о 10 компаниях и их вакансиях.
    """
    print_header("ЗАГРУЗКА ДАННЫХ С HH.RU")

    # Получаем список ID компаний из конфигурации
    company_ids = get_company_ids()

    if not company_ids:
        print("Не найдены ID компаний для загрузки.")
        print("Проверьте функцию get_company_ids() в src/config.py")
        return

    print(f"Найдено {len(company_ids)} компаний для загрузки")

    # Создаем API клиент
    hh_api = HeadHunterAPI(delay=0.3)

    try:
        # 1. Загружаем информацию о компаниях
        print("\n📋 Загрузка информации о компаниях...")
        employers = hh_api.get_all_employers(company_ids)

        if not employers:
            print("✗ Не удалось загрузить информацию о компаниях")
            return

        print(f"✓ Успешно загружено {len(employers)} компаний")

        # Сохраняем компании в БД
        saved_companies = 0
        for employer in employers:
            if db_manager.save_employer(employer.to_dict()):
                saved_companies += 1

        print(f"✓ Сохранено компаний в БД: {saved_companies}/{len(employers)}")

        # 2. Загружаем вакансии
        print("\n💼 Загрузка вакансий...")
        vacancies = hh_api.get_all_vacancies(company_ids)

        if not vacancies:
            print("✗ Не удалось загрузить вакансии")
            return

        print(f"✓ Успешно загружено {len(vacancies)} вакансий")

        # Сохраняем вакансии в БД
        saved_vacancies = 0
        for vacancy in vacancies:
            if db_manager.save_vacancy(vacancy.to_dict()):
                saved_vacancies += 1

            # Показываем прогресс каждые 50 вакансий
            if saved_vacancies % 50 == 0:
                print(f"  Сохранено {saved_vacancies}/{len(vacancies)} вакансий")

        print(f"✓ Сохранено вакансий в БД: {saved_vacancies}/{len(vacancies)}")

        # 3. Показываем итоговую статистику
        print_header("ИТОГИ ЗАГРУЗКИ")
        print(f"• Компаний загружено: {saved_companies}")
        print(f"• Вакансий загружено: {saved_vacancies}")

        if saved_companies > 0 and saved_vacancies > 0:
            print("✓ Данные успешно загружены и сохранены в базу данных")
        else:
            print("⚠ Загружено мало данных. Проверьте подключение к API")

    except Exception as e:
        print(f"✗ Ошибка при загрузке данных: {e}")
        import traceback
        traceback.print_exc()


def show_companies_and_vacancies_count(db_manager: DBManager) -> None:
    """
    Показывает список компаний и количество вакансий.
    Соответствует методу get_companies_and_vacancies_count().
    """
    print_header("КОМПАНИИ И КОЛИЧЕСТВО ВАКАНСИЙ")

    companies = db_manager.get_companies_and_vacancies_count()

    if not companies:
        print("В базе данных нет компаний.")
        return

    print(f"Всего компаний: {len(companies)}\n")

    for i, company in enumerate(companies, 1):
        company_name = company.get('company', 'Неизвестная компания')
        vacancies_count = company.get('vacancies_count', 0)

        # Индикатор количества вакансий
        if vacancies_count == 0:
            indicator = "⚪"
        elif vacancies_count < 5:
            indicator = "🟡"
        elif vacancies_count < 20:
            indicator = "🟠"
        else:
            indicator = "🔴"

        print(f"{i:3}. {indicator} {company_name[:40]:40} | Вакансий: {vacancies_count:4}")

    print(f"\n📊 Всего вакансий: {sum(c['vacancies_count'] for c in companies)}")


def show_all_vacancies(db_manager: DBManager) -> None:
    """
    Показывает все вакансии.
    Соответствует методу get_all_vacancies().
    """
    print_header("ВСЕ ВАКАНСИИ")

    vacancies = db_manager.get_all_vacancies()

    if not vacancies:
        print("В базе данных нет вакансий.")
        return

    print(f"Всего вакансий в базе: {len(vacancies)}")

    # Ограничиваем вывод
    try:
        limit_input = input("\nСколько вакансий показать? (Enter - все, 20): ").strip()
        if limit_input:
            limit = int(limit_input)
        else:
            limit = 20
    except ValueError:
        limit = 20

    if limit > 0:
        vacancies_to_show = vacancies[:limit]
    else:
        vacancies_to_show = vacancies

    print(f"\nПоказано вакансий: {len(vacancies_to_show)}\n")

    for i, vacancy in enumerate(vacancies_to_show, 1):
        print(f"{i}. ", end="")
        print_vacancy(vacancy)

    if len(vacancies_to_show) < len(vacancies):
        print(f"\n... и ещё {len(vacancies) - len(vacancies_to_show)} вакансий")


def show_average_salary(db_manager: DBManager) -> None:
    """
    Показывает среднюю зарплату по вакансиям.
    Соответствует методу get_avg_salary().
    """
    print_header("СРЕДНЯЯ ЗАРПЛАТА")

    avg_salary = db_manager.get_avg_salary()

    if avg_salary > 0:
        print(f"💰 Средняя зарплата по всем вакансиям: {avg_salary:,.2f} руб.")

        # Дополнительная статистика
        stats = db_manager.get_statistics()

        if stats:
            print("\n📊 Общая статистика:")
            print(f"• Компаний в базе: {stats.get('companies_count', 0)}")
            print(f"• Всего вакансий: {stats.get('vacancies_count', 0)}")
            print(f"• Вакансий с указанной зарплатой: {stats.get('vacancies_with_salary', 0)}")
            print(f"• Вакансий без зарплаты: {stats.get('vacancies_count', 0) - stats.get('vacancies_with_salary', 0)}")

            # Топ компаний
            top_companies = stats.get('top_companies', [])
            if top_companies:
                print("\n🏆 Топ компаний по количеству вакансий:")
                for i, company in enumerate(top_companies[:5], 1):
                    print(f"  {i}. {company['company'][:30]:30} | {company['vacancies']} вакансий")
    else:
        print("Недостаточно данных для расчета средней зарплаты.")
        print("Убедитесь, что в базе есть вакансии с указанной зарплатой.")


def show_vacancies_above_average(db_manager: DBManager) -> None:
    """
    Показывает вакансии с зарплатой выше средней.
    Соответствует методу get_vacancies_with_higher_salary().
    """
    print_header("ВАКАНСИИ С ЗАРПЛАТОЙ ВЫШЕ СРЕДНЕЙ")

    # Сначала получаем среднюю зарплату
    avg_salary = db_manager.get_avg_salary()

    if avg_salary <= 0:
        print("Недостаточно данных для расчета средней зарплаты.")
        return

    print(f"📈 Средняя зарплата: {avg_salary:,.2f} руб.")

    # Получаем вакансии с зарплатой выше средней
    vacancies = db_manager.get_vacancies_with_higher_salary()

    if not vacancies:
        print(f"\n😔 Нет вакансий с зарплатой выше {avg_salary:,.2f} руб.")
        return

    print(f"\n🎯 Найдено вакансий с зарплатой выше средней: {len(vacancies)}\n")

    # Ограничиваем вывод
    limit = min(15, len(vacancies))

    for i, vacancy in enumerate(vacancies[:limit], 1):
        print(f"{i}. ", end="")
        print_vacancy(vacancy)

    if len(vacancies) > limit:
        print(f"\n... и ещё {len(vacancies) - limit} вакансий")


def search_vacancies_by_keyword(db_manager: DBManager) -> None:
    """
    Ищет вакансии по ключевому слову.
    Соответствует методу get_vacancies_with_keyword().
    """
    print_header("ПОИСК ВАКАНСИЙ ПО КЛЮЧЕВОМУ СЛОВУ")

    keyword = input("Введите ключевое слово для поиска: ").strip()

    if not keyword:
        print("Ключевое слово не может быть пустым.")
        return

    print(f"\n🔍 Поиск вакансий по ключевому слову: '{keyword}'")

    vacancies = db_manager.get_vacancies_with_keyword(keyword)

    if not vacancies:
        print(f"\n😔 По запросу '{keyword}' вакансий не найдено.")

        # Предлагаем похожие варианты поиска
        suggestions = ["Python", "Java", "JavaScript", "Аналитик", "Менеджер", "Разработчик"]
        print("Попробуйте поискать по одному из этих слов:")
        for suggestion in suggestions:
            print(f"  • {suggestion}")
        return

    print(f"\n✅ Найдено вакансий: {len(vacancies)}\n")

    # Группируем по компаниям
    companies_dict = {}
    for vacancy in vacancies:
        company = vacancy.get('company', 'Неизвестная компания')
        if company not in companies_dict:
            companies_dict[company] = []
        companies_dict[company].append(vacancy)

    # Выводим результаты
    for i, (company, company_vacancies) in enumerate(companies_dict.items(), 1):
        print(f"\n🏢 {company} ({len(company_vacancies)} вакансий):")

        for j, vacancy in enumerate(company_vacancies[:5], 1):
            print(f"  {j}. {vacancy.get('vacancy', '')}")
            print(f"     💰 {vacancy.get('salary', 'Зарплата не указана')}")
            if j < len(company_vacancies[:5]):
                print()

        if len(company_vacancies) > 5:
            print(f"  ... и ещё {len(company_vacancies) - 5} вакансий")

    print(f"\n📊 Всего найдено: {len(vacancies)} вакансий в {len(companies_dict)} компаниях")


def show_database_statistics(db_manager: DBManager) -> None:
    """Показывает общую статистику по базе данных."""
    print_header("СТАТИСТИКА БАЗЫ ДАННЫХ")

    stats = db_manager.get_statistics()

    if not stats:
        print("Не удалось получить статистику.")
        return

    print("📊 ОБЩАЯ СТАТИСТИКА:")
    print(f"• Компаний в базе: {stats.get('companies_count', 0)}")
    print(f"• Всего вакансий: {stats.get('vacancies_count', 0)}")
    print(f"• Вакансий с зарплатой: {stats.get('vacancies_with_salary', 0)}")
    print(f"• Средняя зарплата: {stats.get('avg_salary', 0):,.2f} руб.")

    # Статистика по зарплатам
    if stats.get('avg_salary', 0) > 0:
        print("\n💰 СТАТИСТИКА ПО ЗАРПЛАТАМ:")

        # Вакансии с зарплатой выше средней
        high_salary_count = len(db_manager.get_vacancies_with_higher_salary())
        print(f"• Вакансий с зарплатой выше средней: {high_salary_count}")

        # Процент вакансий с зарплатой
        total_vacancies = stats.get('vacancies_count', 1)
        with_salary = stats.get('vacancies_with_salary', 0)
        if total_vacancies > 0:
            percentage = (with_salary / total_vacancies) * 100
            print(f"• Процент вакансий с указанной зарплатой: {percentage:.1f}%")

    # Топ компаний
    top_companies = stats.get('top_companies', [])
    if top_companies:
        print("\n🏆 ТОП-5 КОМПАНИЙ ПО КОЛИЧЕСТВУ ВАКАНСИЙ:")
        for i, company in enumerate(top_companies[:5], 1):
            name = company['company'][:35]
            if len(company['company']) > 35:
                name += "..."
            print(f"  {i}. {name:38} | {company['vacancies']:3} вакансий")


def database_menu(db_manager: DBManager) -> None:
    """
    Главное меню работы с базой данных.
    Соответствует всем требованиям по взаимодействию с пользователем.
    """
    while True:
        print_menu("РАБОТА С БАЗОЙ ДАННЫХ", [
            "📊 Компании и количество вакансий",
            "📋 Все вакансии",
            "💰 Средняя зарплата",
            "⬆️ Вакансии с зарплатой выше средней",
            "🔍 Поиск вакансий по ключевому слову",
            "📈 Статистика базы данных",
            "🔄 Загрузить новые данные с HH.ru",
            "🏠 Вернуться в главное меню"
        ])

        try:
            choice = input("\nВаш выбор (1-8): ").strip()

            if choice == "1":
                show_companies_and_vacancies_count(db_manager)
                input("\nНажмите Enter для продолжения...")

            elif choice == "2":
                show_all_vacancies(db_manager)
                input("\nНажмите Enter для продолжения...")

            elif choice == "3":
                show_average_salary(db_manager)
                input("\nНажмите Enter для продолжения...")

            elif choice == "4":
                show_vacancies_above_average(db_manager)
                input("\nНажмите Enter для продолжения...")

            elif choice == "5":
                search_vacancies_by_keyword(db_manager)
                input("\nНажмите Enter для продолжения...")

            elif choice == "6":
                show_database_statistics(db_manager)
                input("\nНажмите Enter для продолжения...")

            elif choice == "7":
                load_data_from_hh(db_manager)
                input("\nНажмите Enter для продолжения...")

            elif choice == "8":
                break

            else:
                print("Неверный выбор. Попробуйте снова.")

        except KeyboardInterrupt:
            print("\n\nВозвращаемся в главное меню...")
            break
        except Exception as e:
            print(f"Ошибка: {e}")
            input("Нажмите Enter для продолжения...")


def show_project_info() -> None:
    """Показывает информацию о проекте."""
    print_header("ИНФОРМАЦИЯ О ПРОЕКТЕ")

    print("🎯 ЦЕЛЬ ПРОЕКТА:")
    print("Получение данных о вакансиях с HH.ru, их сохранение в БД PostgreSQL")
    print("и предоставление аналитических функций для пользователя.")

    print("\n📋 ТРЕБОВАНИЯ К ПРОЕКТУ:")
    print("✓ Получение данных через API HH.ru")
    print("✓ Работа с 10+ компаниями")
    print("✓ Создание БД PostgreSQL с таблицами employers и vacancies")
    print("✓ Реализация класса DBManager с 5 методами")
    print("✓ Текстовый интерфейс для пользователя")

    print("\n🔧 ТЕХНОЛОГИИ:")
    print("• Python 3.9+")
    print("• PostgreSQL")
    print("• Библиотеки: requests, psycopg2-binary")

    print("\n📁 СТРУКТУРА ПРОЕКТА:")
    print("src/api.py         - работа с API HH.ru")
    print("src/database.py    - создание БД и таблиц")
    print("src/db_manager.py  - класс DBManager")
    print("src/config.py      - настройки и ID компаний")
    print("src/utils.py       - вспомогательные функции")
    print("main.py           - точка входа")

    print("\n👨‍💻 АВТОР:")
    print("Студент курса Python-разработки")

    input("\nНажмите Enter для возврата в меню...")


def main() -> None:
    """
    Главная функция программы - точка входа.
    """
    print_header("ПРОГРАММА ДЛЯ РАБОТЫ С ВАКАНСИЯМИ HH.RU")

    try:
        # Загружаем конфигурацию БД
        config = load_config()

        # Создаем и настраиваем базу данных
        print("\n🔧 Настройка базы данных...")
        setup_database(config)

        # Создаем менеджер для работы с БД
        db_manager = DBManager(config)

        # Проверяем, есть ли данные в БД
        stats = db_manager.get_statistics()

        if stats.get('vacancies_count', 0) == 0:
            print("\n⚠ База данных пустая.")
            load_option = input("Загрузить данные с HH.ru сейчас? (да/нет): ").strip().lower()

            if load_option in ['да', 'yes', 'y', 'д']:
                load_data_from_hh(db_manager)

        print("\n✅ Система готова к работе!")

        # Главный цикл программы
        while True:
            print_menu("ГЛАВНОЕ МЕНЮ", [
                "💼 Работа с базой данных вакансий",
                "ℹ️ Информация о проекте",
                "🚪 Выход"
            ])

            try:
                choice = input("\nВаш выбор (1-3): ").strip()

                if choice == "1":
                    database_menu(db_manager)

                elif choice == "2":
                    show_project_info()

                elif choice == "3":
                    print("\n" + "=" * 60)
                    print("Спасибо за использование программы!".center(60))
                    print("=" * 60)
                    sys.exit(0)

                else:
                    print("Неверный выбор. Попробуйте снова.")

            except KeyboardInterrupt:
                print("\n\nПрограмма завершена.")
                sys.exit(0)
            except Exception as e:
                print(f"Ошибка: {e}")
                input("Нажмите Enter для продолжения...")

    except FileNotFoundError as e:
        print(f"\n✗ Ошибка: {e}")
        print("\nСоздайте файл data/database.ini со следующими настройками:")
        print("[postgresql]")
        print("host=localhost")
        print("database=hh_vacancies")
        print("user=postgres")
        print("password=ваш_пароль")
        print("port=5432")
        input("\nНажмите Enter для выхода...")
        sys.exit(1)

    except Exception as e:
        print(f"\n✗ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        input("\nНажмите Enter для выхода...")
        sys.exit(1)


if __name__ == "__main__":
    main()
