import requests
import json
import pandas as pd
from datetime import datetime

# Скрипт будет разделен на две части:
# 1. Загрузка данных из API и сохранение в JSON файл с преобразованием дат и удалением ненужных полей
# 2. Чтение данных из JSON файла, запрос параметров у пользователя и формирование Excel отчета

# Часть 1: Загрузка и сохранение данных в JSON
def save_data_to_json(api_url, json_file_path):
    response = requests.get(api_url)
    if response.status_code == 200:
        orders = response.json()
        # Преобразование дат и удаление ненужных полей
        for order in orders:
            # Преобразование даты
            date_iso = order['created_at'].split('T')[0]
            order['created_at'] = datetime.strptime(date_iso, '%Y-%m-%d').strftime('%d.%m.%y')
            # Удаление ненужных полей
            order.pop('user', None)
            order.pop('person', None)
            order.pop('comment', None)
            order.pop('address', None)
        # Сохранение в JSON файл
        with open(json_file_path, 'w', encoding='utf-8') as json_file:
            json.dump(orders, json_file, ensure_ascii=False, indent=4)
        print("Data saved to JSON file successfully.")
    else:
        print("Failed to fetch data from API")

# Часть 2: Фильтрация данных и создание Excel отчета
def filter_orders_and_create_report(json_file_path):
    # Чтение данных из JSON
    with open(json_file_path, 'r', encoding='utf-8') as json_file:
        orders = json.load(json_file)
    
    # Словарь для переименования статусов
    status_rename_map = {
        'succeeded': 'Оплачен',
        'accepted': 'Принят',
        'on_the_way': 'В пути',
        'delivered': 'Доставлен',
        'canceled': 'Отменен'
    }
    
    # Запрос параметров у пользователя
    start_date = datetime.strptime(input("Enter start date (dd.mm.yy): "), '%d.%m.%y').date()
    end_date = datetime.strptime(input("Enter end date (dd.mm.yy): "), '%d.%m.%y').date()
    min_cost = int(input("Enter minimum total cost: "))
    max_cost = int(input("Enter maximum total cost: "))
    status_input = input("Enter the status of the order or 'All' for all statuses: ").lower()

    # Применяем словарь для переименования статусов и фильтруем данные
    filtered_orders = []
    for order in orders:
        order_status = status_rename_map.get(order['status'], order['status'])  # Используем словарь для замены статуса
        if (
            start_date <= datetime.strptime(order['created_at'], '%d.%m.%y').date() <= end_date
            and min_cost <= order['total_cost'] <= max_cost
            and (order_status.lower() == status_input or status_input == 'all')
        ):
            order['status'] = order_status  # Обновляем статус в заказе
            filtered_orders.append(order)
    
    # Создание DataFrame для сохранения в Excel
    df = pd.DataFrame(filtered_orders)
    
    # Переименование столбцов
    df.rename(columns={
        'user_full_name': 'Имя',
        'full_address': 'Адрес',
        'created_at': 'Дата',
        'order_number': 'Номер заказа',
        'status': 'Статус',
        'total_cost': 'Сумма'
    }, inplace=True)
    
    # Сохранение в Excel файл
    excel_file_path = 'orders_report.xlsx'
    df.to_excel(excel_file_path, index=False)
    print("Excel report created successfully.")

    return excel_file_path


# Основная логика
api_url = 'https://api.akulov.net/api/v1/order/list/'
json_file_path = 'data.json'

# Вызов функций
save_data_to_json(api_url, json_file_path)
excel_report_path = filter_orders_and_create_report(json_file_path)
excel_report_path
