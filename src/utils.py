"""
Вспомогательные функции
"""
import configparser
import os
from typing import Dict, Any


def load_config(filename: str = 'data/database.ini') -> Dict[str, Any]:
    """
    Загружает конфигурацию базы данных из файла.

    Args:
        filename: Путь к файлу конфигурации

    Returns:
        Dict: Конфигурация подключения к БД

    Raises:
        FileNotFoundError: Если файл конфигурации не найден
    """
    if not os.path.exists(filename):
        raise FileNotFoundError(
            f"Файл конфигурации {filename} не найден.\n"
            f"Создайте его со следующим содержимым:\n"
            f"[postgresql]\n"
            f"host=localhost\n"
            f"database=hh_vacancies\n"
            f"user=postgres\n"
            f"password=ваш_пароль\n"
            f"port=5432"
        )

    config = configparser.ConfigParser()
    config.read(filename)

    return {
        'host': config['postgresql']['host'],
        'database': config['postgresql']['database'],
        'user': config['postgresql']['user'],
        'password': config['postgresql']['password'],
        'port': config['postgresql'].get('port', '5432')
    }


def print_vacancy(vacancy: Dict[str, Any], index: int = None) -> None:
    """
    Печатает информацию о вакансии в читаемом формате.

    Args:
        vacancy: Словарь с данными вакансии
        index: Порядковый номер (опционально)
    """
    if index is not None:
        print(f"\n{index}. ", end="")

    print(f"{vacancy.get('company', 'Неизвестно')}")
    print(f"   Вакансия: {vacancy.get('vacancy', 'Не указано')}")
    print(f"   Зарплата: {vacancy.get('salary', 'Не указана')}")
    print(f"   Ссылка: {vacancy.get('url', 'Нет ссылки')}")
