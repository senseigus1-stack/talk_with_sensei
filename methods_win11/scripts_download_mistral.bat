@echo off
setlocal enabledelayedexpansion

:: ========== Настройки ==========
set "ARIA2_PATH=C:\aria2\aria2-1.37.0-win-64bit-build1\aria2c.exe"
set "MODEL_ID=mistralai/Mistral-7B-Instruct-v0.3"
set "DOWNLOAD_DIR=C:\Users\arsenii\talk_with_sensei\mistral"
set "URL_FILE=urls_mistral.txt"

:: Создаём папку для загрузки
if not exist "%DOWNLOAD_DIR%" mkdir "%DOWNLOAD_DIR%"

:: ========== Формируем список URL ==========
(
    echo https://huggingface.co/%MODEL_ID%/resolve/main/config.json
    echo https://huggingface.co/%MODEL_ID%/resolve/main/generation_config.json
    echo https://huggingface.co/%MODEL_ID%/resolve/main/model.safetensors.index.json
    echo https://huggingface.co/%MODEL_ID%/resolve/main/model-00001-of-00003.safetensors
    echo https://huggingface.co/%MODEL_ID%/resolve/main/model-00002-of-00003.safetensors
    echo https://huggingface.co/%MODEL_ID%/resolve/main/model-00003-of-00003.safetensors
    echo https://huggingface.co/%MODEL_ID%/resolve/main/special_tokens_map.json
    echo https://huggingface.co/%MODEL_ID%/resolve/main/tokenizer.json
    echo https://huggingface.co/%MODEL_ID%/resolve/main/tokenizer_config.json
    echo https://huggingface.co/%MODEL_ID%/resolve/main/tokenizer.model
    echo https://huggingface.co/%MODEL_ID%/resolve/main/tokenizer.model.v3
    echo https://huggingface.co/%MODEL_ID%/resolve/main/consolidated.safetensors
    echo https://huggingface.co/%MODEL_ID%/resolve/main/params.json
) > "%URL_FILE%"

:: ========== Первая попытка загрузки ==========
echo Запуск первичной загрузки...
"%ARIA2_PATH%" ^
    -i "%URL_FILE%" ^
    -d "%DOWNLOAD_DIR%" ^
    -x 4 ^
    -s 4 ^
    --max-connection-per-server=4 ^
    --min-split-size=1M ^
    --continue=true ^
    --retry-wait=20 ^
    --max-tries=10 ^
    --async-dns=false ^
    --content-disposition=true ^
    --check-certificate=false ^
    --remote-time=true ^
    --user-agent="aria2"

:: ========== Проверка недостающих файлов ==========
echo Проверка загруженных файлов...
set "missing_files="
for %%F in (
    "config.json"
    "generation_config.json"
    "model.safetensors.index.json"
    "model-00001-of-00003.safetensors"
    "model-00002-of-00003.safetensors"
    "model-00003-of-00003.safetensors"
    "special_tokens_map.json"
    "tokenizer.json"
    "tokenizer_config.json"
    "tokenizer.model"
    "tokenizer.model.v3"
    "consolidated.safetensors"
    "params.json"
) do (
    if not exist "%DOWNLOAD_DIR%\%%~F" (
        echo Отсутствует: %%F
        set "missing_files=!missing_files!%%F "
    )
)

:: ========== Докачка недостающих файлов ==========
if not "!missing_files!"=="" (
    echo Начинаю докачку недостающих файлов...
    :: Создаём временный список URL для отсутствующих файлов
    set "tmp_urls=%TEMP%\urls_missing_%RANDOM%.txt"
    >"!tmp_urls!" (
        for %%F in (!missing_files!) do (
            echo https://huggingface.co/%MODEL_ID%/resolve/main/%%F
        )
    )
    "%ARIA2_PATH%" ^
        -i "!tmp_urls!" ^
        -d "%DOWNLOAD_DIR%" ^
        -x 4 ^
        -s 4 ^
        --max-connection-per-server=4 ^
        --min-split-size=1M ^
        --continue=true ^
        --retry-wait=20 ^
        --max-tries=10 ^
        --async-dns=false ^
        --content-disposition=true ^
        --check-certificate=false ^
        --remote-time=true ^
        --user-agent="aria2"
    del "!tmp_urls!" 2>nul

    :: Повторная проверка
    set "still_missing=0"
    for %%F in (!missing_files!) do (
        if not exist "%DOWNLOAD_DIR%\%%F" set "still_missing=1"
    )
    if "!still_missing!"=="1" (
        echo !!! Некоторые файлы всё ещё отсутствуют. Проверьте интернет-соединение или DNS.
        exit /b 1
    )
)

echo Загрузка завершена успешно! Все файлы в папке: %DOWNLOAD_DIR%
endlocal
exit /b 0