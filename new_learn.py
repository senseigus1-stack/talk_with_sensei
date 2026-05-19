import os
import torch
import time
import psutil
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
    DataCollatorForLanguageModeling,
    TrainerCallback,
    Trainer,
)
from peft import PeftModel, LoraConfig, get_peft_model

start_time = time.time()

# ============================================================
# 1. SYSTEM DIAGNOSTICS
# ============================================================
def print_memory_usage():
    process = psutil.Process(os.getpid())
    mem = process.memory_info()
    print(f"Memory usage: {mem.rss / 1024 / 1024:.2f} MB")

def check_cuda():
    if torch.cuda.is_available():
        print(f"CUDA available, using GPU: {torch.cuda.get_device_name()}")
        print(f"Number of GPUs: {torch.cuda.device_count()}")
    else:
        print("CUDA not available, training will be slow")

print("=" * 60)
print("SYSTEM DIAGNOSTICS")
print("=" * 60)
check_cuda()
print_memory_usage()

# ============================================================
# 2. DATA LOADING
# ============================================================
print("\n" + "=" * 60)
print("LOADING DATA")
print("=" * 60)
dataset = load_dataset('json', data_files='train_data.jsonl', split='train')
print(f"Loaded {len(dataset)} examples")
print(f"Columns: {dataset.column_names}")
print("First 3 samples:")
for i in range(min(3, len(dataset))):
    print(f"  {i}: {dataset[i]}")

# ============================================================
# 3. MODEL AND TOKENIZER (8-bit через BitsAndBytes)
# ============================================================
mistral_path = r"C:/Users/arsenii/talk_with_sensei/mistral"
saiga_lora_path = r"C:/Users/arsenii/talk_with_sensei/saiga_lora"

print("\nLoading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(mistral_path, trust_remote_code=True)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token
    print("pad_token set to eos_token")

print("Loading base Mistral model in 8-bit...")
quantization_config = BitsAndBytesConfig(load_in_8bit=True)

model = AutoModelForCausalLM.from_pretrained(
    mistral_path,
    quantization_config=quantization_config,
    device_map="auto",
)

print("Loading Saiga LoRA adapter...")
model = PeftModel.from_pretrained(model, saiga_lora_path)

# ---------- СОЗДАЁМ НОВЫЙ LORA АДАПТЕР ПОВЕРХ SAIGA ----------
print("Creating a new LoRA adapter on top of Saiga...")
peft_config = LoraConfig(
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
    bias="none",
    task_type="CAUSAL_LM"
)

base_model = model.base_model
model = get_peft_model(base_model, peft_config)

model.train()
print("New LoRA adapter added and set to training mode.")
print("Trainable parameters:")
model.print_trainable_parameters()

# ============================================================
# 4. DATA TOKENIZATION
# ============================================================
print("\nTokenizing dataset...")

def tokenize_function(examples):
    return tokenizer(
        examples["text"],
        truncation=True,
        max_length=512,
        padding=False,
    )

tokenized_dataset = dataset.map(
    tokenize_function,
    batched=True,
    remove_columns=dataset.column_names,
)

# ============================================================
# 5. TRAINING ARGUMENTS
# ============================================================
training_args = TrainingArguments(
    output_dir="./results_fine_tuned",
    num_train_epochs=3,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=4,
    learning_rate=2e-4,
    logging_steps=50,
    save_steps=500,
    warmup_steps=100,
    lr_scheduler_type="cosine",
    report_to="none",
    fp16=True,
    dataloader_num_workers=0,
    remove_unused_columns=False,
    save_total_limit=2,
    save_strategy="steps",
    load_best_model_at_end=False,
)

# ============================================================
# 6. PAUSE CALLBACK
# ============================================================
class PauseCallback(TrainerCallback):
    """Checks for 'pause.flag' file at the beginning of each step.
    If the file exists, training is suspended until the file is removed."""
    def __init__(self, pause_file="pause.flag"):
        self.pause_file = pause_file
        self.is_paused = False

    def on_step_begin(self, args, state, control, **kwargs):
        while os.path.exists(self.pause_file):
            if not self.is_paused:
                print("\n=== PAUSE SIGNAL DETECTED ===")
                print("Training suspended. Remove 'pause.flag' to resume.")
                self.is_paused = True
            time.sleep(5)
        if self.is_paused and not os.path.exists(self.pause_file):
            print("\n=== RESUME SIGNAL DETECTED ===")
            self.is_paused = False
        return control

# ============================================================
# 7. DATA COLLATOR
# ============================================================
data_collator = DataCollatorForLanguageModeling(
    tokenizer=tokenizer,
    mlm=False,
)

# ============================================================
# 8. TRAINER INITIALIZATION
# ============================================================
print("\nInitializing Trainer...")

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset,
    data_collator=data_collator,
)

trainer.add_callback(PauseCallback())

print("Trainer initialized successfully!")
print(f"Model type: {type(model)}")
print(f"Train dataset size: {len(tokenized_dataset)}")

# ============================================================
# 9. TRAINING
# ============================================================
print("\n" + "=" * 60)
print("STARTING TRAINING")
print("=" * 60)
print("To pause: create empty file 'pause.flag' in the script directory.")
print("To resume: delete that file.")

try:
    trainer.train()
    print("\nTraining completed successfully!")
except KeyboardInterrupt:
    print("\nTraining interrupted by user. Current state saved automatically.")
except Exception as e:
    print(f"\nError during training: {e}")
    raise

# ============================================================
# 10. SAVING FINAL MODEL (LoRA adapter)
# ============================================================
print("\n" + "=" * 60)
print("SAVING FINAL MODEL")
print("=" * 60)

output_dir = "./final_saiga_model"
trainer.save_model(output_dir)
tokenizer.save_pretrained(output_dir)
print(f"Final model (trainer) saved to {output_dir}")

adapter_dir = "./updated_lora_adapter"
model.save_pretrained(adapter_dir)
tokenizer.save_pretrained(adapter_dir)
print(f"Updated LoRA adapter saved to {adapter_dir}")

# ============================================================
# 11. MERGE ADAPTER INTO FULL MODEL (optional)
# ============================================================
print("\nMerging adapter into full model...")
try:
    # Для слияния нужно отключить 8-бит (иначе ошибка) — временно переводим в float16
    model = model.merge_and_unload()
    merged_output = "./merged_saiga_model"
    model.save_pretrained(merged_output)
    tokenizer.save_pretrained(merged_output)
    print(f"Merged model saved to {merged_output}")
except Exception as e:
    print(f"Merging failed: {e}")
    print("You can use the LoRA adapter separately with the base Mistral model.")

# ============================================================
# 12. TEST GENERATION
# ============================================================
print("\n" + "=" * 60)
print("TEST GENERATION")
print("=" * 60)

# Переводим модель обратно в eval (если она была в train)
model.eval()

test_prompts = [
    "<s>[INST] How was your day? [/INST]",
    "<s>[INST] Tell me something funny [/INST]",
    "<s>[INST] What do you think about studying? [/INST]"
]

for prompt in test_prompts:
    with torch.no_grad():
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        outputs = model.generate(
            **inputs,
            max_new_tokens=150,
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
            repetition_penalty=1.1
        )
        generated = tokenizer.decode(outputs[0], skip_special_tokens=False)
        print(f"\nPrompt: {prompt}")
        print(f"Generated: {generated}")
        if "[/INST]" in generated:
            response = generated.split("[/INST]")[-1].strip()
            print(f"Response only: {response}")

# ============================================================
# 13. CLEANUP & FINAL REPORT
# ============================================================
print("\nCleaning up temporary files...")
for f in ["pause.flag", "training_checkpoint.tmp"]:
    if os.path.exists(f):
        os.remove(f)
        print(f"Removed {f}")

print_memory_usage()
if torch.cuda.is_available():
    print(f"Final GPU memory: {torch.cuda.memory_allocated()/1024**2:.2f} MB")
    print(f"Peak GPU memory: {torch.cuda.max_memory_allocated()/1024**2:.2f} MB")

end_time = time.time()
hours = (end_time - start_time) / 3600
print(f"Total training time: {hours:.2f} hours")

print("\n" + "=" * 60)
print("ALL OPERATIONS COMPLETED")
print("=" * 60)
print("Your model is ready. Check the output directories.")