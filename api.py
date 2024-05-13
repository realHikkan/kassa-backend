from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
import os
import json
import pandas as pd
from datetime import datetime
import requests

# Инициализация Flask приложения
app = Flask(__name__)
CORS(app)  # Включение CORS для всех роутов и методов

# Папка для хранения отчетов
REPORT_FOLDER = 'reports'
app.config['REPORT_FOLDER'] = REPORT_FOLDER

# Проверяем и создаем папку для отчетов, если она не существует
if not os.path.exists(REPORT_FOLDER):
    os.makedirs(REPORT_FOLDER)

# API URL
api_url = 'https://api.akulov.net/api/v1/order/list/'

# Функция сохранения данных в JSON с форматированием даты и удалением полей
def save_data_to_json(orders, json_file_path):
    for order in orders:
        # Разделяем ISO 8601 строку даты и времени и отбрасываем микросекунды
        date_iso, time_iso = order['created_at'].split('T')
        time_iso = time_iso.split('.')[0]  # Удаление микросекунд

        # Форматирование даты и времени в соответствии с новым форматом
        order['created_at'] = datetime.strptime(f'{date_iso} {time_iso}', '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%y %H:%M:%S')
        
        # Удаление ненужных полей
        for field in ['user', 'person', 'comment', 'address']:
            order.pop(field, None)
    
    # Сохранение в JSON файл
    with open(json_file_path, 'w', encoding='utf-8') as json_file:
        json.dump(orders, json_file, ensure_ascii=False, indent=4)


# Функция фильтрации заказов и создания Excel отчета
def filter_orders_and_create_report(json_file_path, start_date, end_date, min_cost, max_cost, status_input):
    with open(json_file_path, 'r', encoding='utf-8') as json_file:
        orders = json.load(json_file)
    
    # Словарь переименования статусов
    status_rename_map = {
        'succeeded': 'Оплачен',
        'accepted': 'Принят',
        'on_the_way': 'В пути',
        'delivered': 'Доставлен',
        'canceled': 'Отменен'
    }
    
    # Фильтрация заказов
    filtered_orders = []
    for order in orders:
        order_date = datetime.strptime(order['created_at'], '%d.%m.%y %H:%M:%S')
        if start_date <= order_date <= end_date and min_cost <= order['total_cost'] <= max_cost:
            if status_input == 'all' or order['status'].lower() == status_input:
                # Преобразование статуса только после прохождения фильтра
                order['status'] = status_rename_map.get(order['status'], order['status'])
                filtered_orders.append(order)
                order['code'] = order['code']['code']
    
    # Создание DataFrame
    df = pd.DataFrame(filtered_orders)
    df.rename(columns={
        'user_full_name': 'Имя',
        'full_address': 'Адрес',
        'created_at': 'Дата',
        'order_number': 'Номер заказа',
        'status': 'Статус',
        'total_cost': 'Сумма',
        'code': 'Промокод'
    }, inplace=True)
    
    # Формирование названия файла отчета
    current_time = datetime.now().strftime('%d.%m.%y %H.%M.%S')
    excel_file_name = f"report_{current_time}.xlsx"
    excel_file_path = os.path.join(app.config['REPORT_FOLDER'], excel_file_name)
    df.to_excel(excel_file_path, index=False)
    
    return excel_file_name


@app.route('/generate-report', methods=['POST'])
def generate_report():
    # Получение данных из POST запроса
    data = request.json
    orders = requests.get(api_url).json()
    
    # Форматирование и сохранение данных в JSON
    json_file_path = os.path.join(app.config['REPORT_FOLDER'], 'data.json')
    save_data_to_json(orders, json_file_path)
    
    # Формирование отчета на основе данных запроса
    excel_file_name = filter_orders_and_create_report(
        json_file_path,
        datetime.fromisoformat(data['start_date']),
        datetime.fromisoformat(data['end_date']),
        data['min_cost'],
        data['max_cost'],
        data['status'].lower()
    )
    
    # Возвращение ссылки на скачивание отчета
    download_url = request.host_url + 'download-report/' + excel_file_name
    return jsonify({'download_url': download_url})


@app.route('/download-report/<filename>', methods=['GET'])
def download_report(filename):
    # Отправка файла для скачивания
    return send_from_directory(app.config['REPORT_FOLDER'], filename, as_attachment=True)


@app.route('/list-reports', methods=['GET'])
def list_reports():
    files = os.listdir(app.config['REPORT_FOLDER'])
    # Отфильтруем список файлов, чтобы возвращать только файлы отчетов
    report_files = [f for f in files if f.endswith('.xlsx')]
    return jsonify(report_files)

if __name__ == '__main__':
    app.run(debug=True)
