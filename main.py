import os
import torch
import json
from transformers import AutoModelForCausalLM, AutoTokenizer


def load_trained_model(model_path: str, device: str):
    """
    Загружает обученную модель и токенизатор.
    """
    print(f"Loading model from {model_path}...")
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        torch_dtype=torch.float16
    )
    model.to(device)
    model.eval()  # режим инференса

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    print("Model and tokenizer loaded successfully!")
    return model, tokenizer

def generate_response(
    model,
    tokenizer,
    prompt: str,
    device: str,
    max_new_tokens: int = 1000,
    temperature: float = 0.8,
    do_sample: bool = True
) -> str:
    """
    Генерирует ответ на заданный промпт.
    """
    inputs = tokenizer(prompt, return_tensors="pt").to(device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            do_sample=do_sample,
            pad_token_id=tokenizer.eos_token_id
        )

    generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    # Убираем промпт из начала ответа, если он там дублируется
    if generated_text.startswith(prompt):
        generated_text = generated_text[len(prompt):].strip()
    return generated_text

def interactive_test(model, tokenizer, device: str):
    """
    Интерактивный режим тестирования: пользователь вводит промпт, модель отвечает.
    Выход — по команде 'quit'.
    """
    print("\n" + "=" * 500)
    print("INTERACTIVE TEST MODE (type 'quit' to exit)")
    print("=" * 500)

    while True:
        prompt = input("\nEnter prompt: ").strip()
        if prompt.lower() in ['quit', 'exit', 'q']:
            break

        response = generate_response(model, tokenizer, prompt, device)
        print(f"Response: {response}")

def batch_test(model, tokenizer, device: str, test_prompts: list):
    """
    Пакетное тестирование на списке промптов.
    Возвращает список словарей с промптом, ответом и метриками.
    """
    print("\n" + "=" * 500)
    print("BATCH TEST MODE")
    print("=" * 500)

    results = []
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\nTesting [{i}/{len(test_prompts)}]: {prompt}")
        response = generate_response(model, tokenizer, prompt, device)

        # Простые метрики
        response_length = len(response.split())
        has_keywords = any(kw in response.lower() for kw in ['программист', 'код', 'python', 'ошибка'])

        result = {
            "prompt": prompt,
            "response": response,
            "response_length_words": response_length,
            "contains_keywords": has_keywords
        }
        results.append(result)
        print(f"Generated ({response_length} words): {response[:2000]}...")

    return results

def save_results(results: list, output_file: str):
    """
    Сохраняет результаты тестирования в JSON‑файл.
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nResults saved to {output_file}")

def main():
    # Настройки
  #  MODEL_PATH = "./final_model"  # путь к сохранённой модели
    MODEL_PATH = "./merged_saiga_model"
    OUTPUT_FILE = "test_results.json"

    # Проверка доступности GPU
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    # Загрузка модели и токенизатора
    model, tokenizer = load_trained_model(MODEL_PATH, device)

    # Тестовые промпты для пакетного тестирования
    test_prompts = [
        "<s>[INST] Расскажи шутку про программиста [/INST]",
        "<s>[INST] Объясни, что такое нейронная сеть, простыми словами [/INST]",
        "<s>[INST] Напиши короткий код на Python для сортировки списка [/INST]",
        "<s>[INST] Что такое fine‑tuning? Кратко [/INST]"
    ]

    # Пакетное тестирование
    batch_results = batch_test(model, tokenizer, device, test_prompts)

    # Интерактивное тестирование
    interactive_test(model, tokenizer, device)

    # Сохранение результатов
    save_results(batch_results, OUTPUT_FILE)

if __name__ == "__main__":
    main()