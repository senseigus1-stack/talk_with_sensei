
import csv
import json
import os

def csv_to_json_with_field(csv_file_path, json_file_path=None, new_field_name="instruction", new_field_value=None):
    """
    Конвертирует CSV в JSON с добавлением нового поля.

    Args:
        csv_file_path (str): путь к CSV‑файлу.
        json_file_path (str, optional): путь для сохранения JSON (если None, используется имя CSV с расширением .json).
        new_field_name (str): имя добавляемого поля.
        new_field_value: значение добавляемого поля (если None, устанавливается пустая строка).
    """
    # Устанавливаем значение по умолчанию для нового поля
    if new_field_value is None:
        new_field_value = ""

    # Если путь для JSON не указан, создаём его на основе пути CSV
    if json_file_path is None:
        json_file_path = os.path.splitext(csv_file_path)[0] + '.json'

    # Проверяем существование CSV‑файла
    if not os.path.exists(csv_file_path):
        print(f"Ошибка: файл {csv_file_path} не найден.")
        return

    data = []

    # Читаем CSV и преобразуем в список словарей
    with open(csv_file_path, 'r', encoding='utf-8') as csv_file:
        csv_reader = csv.DictReader(csv_file)

        for row in csv_reader:
            # Создаём новый словарь: сначала новое поле, затем — все остальные
            new_row = {new_field_name: new_field_value}
            new_row.update(row)
            data.append(new_row)
            
    # Записываем данные в JSON
    with open(json_file_path, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=2)

    print(f"CSV успешно преобразован в JSON.")
    print(f"Входной файл: {csv_file_path}")
    print(f"Выходной файл: {json_file_path}")
    print(f"Добавлено поле: '{new_field_name}' со значением: '{new_field_value}'")
    print(f"Обработано записей: {len(data)}")

# Пример использования
if __name__ == '__main__':
    # Укажите путь к вашему CSV‑файлу
    input_csv = 'data\my_dialogues.csv'

    # Вызываем функцию конвертации
    csv_to_json_with_field(
        csv_file_path=input_csv,
        new_field_name="instruction",
        new_field_value="Ответь в моем стиле"  # можно задать любое значение, например "значение_по_умолчанию"
    )