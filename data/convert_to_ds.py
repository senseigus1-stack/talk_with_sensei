import json

def convert_jsonl(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f_in, \
         open(output_file, 'w', encoding='utf-8') as f_out:
        data = json.load(f_in)
        for item in data:
            instruction = item['instruction']
            context = item['context']
            response = item['response']

            # Формируем единую строку в формате Llama
            prompt = f"<s>[INST] {context} [/INST] {response}</s>"
            f_out.write(json.dumps({"text": prompt}, ensure_ascii=False) + '\n')

# Запуск конвертации
convert_jsonl('data/my_dialogues.json', 'train_data.jsonl')
