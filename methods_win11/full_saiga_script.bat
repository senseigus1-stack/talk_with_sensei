@echo off
setlocal enabledelayedexpansion

:: ===== НАСТРОЙКИ =====
set "ARIA2_PATH=C:\aria2\aria2-1.37.0-win-64bit-build1\aria2c.exe"
set "MODEL_ID=IlyaGusev/saiga_mistral_7b_lora"
set "DOWNLOAD_DIR=C:\Users\arsenii\talk_with_sensei\saiga_mistral_7b_lora"
set "URL_FILE=urls_saiga.txt"
set "MAX_RETRIES=5"

:: Список файлов, которые должны быть после успешной загрузки
set "REQUIRED_FILES=adapter_config.json adapter_model.safetensors added_tokens.json generation_config.json special_tokens_map.json tokenizer.model tokenizer_config.json"

echo =====================================================
echo SAIGA-MISTRAL-7B-LORA DOWNLOADER (IMPROVED)
echo =====================================================
echo.

:: Создаём папку, если её нет
if not exist "%DOWNLOAD_DIR%" mkdir "%DOWNLOAD_DIR%"

:: Генерируем список URL
echo Generating URL list...
(
    echo https://huggingface.co/%MODEL_ID%/resolve/main/adapter_config.json
    echo https://huggingface.co/%MODEL_ID%/resolve/main/generation_config.json
    echo https://huggingface.co/%MODEL_ID%/resolve/main/special_tokens_map.json
    echo https://huggingface.co/%MODEL_ID%/resolve/main/tokenizer_config.json
    echo https://huggingface.co/%MODEL_ID%/resolve/main/adapter_model.safetensors
    echo https://huggingface.co/%MODEL_ID%/resolve/main/tokenizer.model
    echo https://huggingface.co/%MODEL_ID%/resolve/main/added_tokens.json
) > "%URL_FILE%"

:: ===== ОСНОВНОЙ ЦИКЛ ЗАГРУЗКИ =====
set "RETRY_COUNT=0"
:DOWNLOAD_LOOP
echo.
echo Download attempt %RETRY_COUNT%...
echo.

:: Очищаем DNS-кэш (может помочь при Name resolution failed)
ipconfig /flushdns >nul 2>&1

:: Запускаем aria2c с улучшенными параметрами
"%ARIA2_PATH%" ^
    -i "%URL_FILE%" ^
    -d "%DOWNLOAD_DIR%" ^
    -x 16 ^
    -s 16 ^
    --max-connection-per-server=16 ^
    --min-split-size=1M ^
    --continue=true ^
    --retry-wait=15 ^
    --max-tries=10 ^
    --check-certificate=false ^
    --remote-time=true ^
    --async-dns=false ^
    --log="aria2_download.log" ^
    --log-level="warn"

set "ARIA2_EXIT=%ERRORLEVEL%"

:: ===== ПЕРЕИМЕНОВАНИЕ ХЕШ-ФАЙЛОВ =====
echo.
echo Checking for hash-named files...
call :RenameHashFiles

:: ===== ПРОВЕРКА НАЛИЧИЯ ВСЕХ ФАЙЛОВ =====
set "MISSING=0"
for %%F in (%REQUIRED_FILES%) do (
    if not exist "%DOWNLOAD_DIR%\%%~F" (
        echo MISSING: %%~F
        set "MISSING=1"
    )
)

if "!MISSING!"=="0" (
    echo.
    echo =====================================================
    echo ALL FILES DOWNLOADED SUCCESSFULLY!
    echo Model is ready for training.
    echo =====================================================
    del "%URL_FILE%" 2>nul
    pause
    exit /b 0
)

:: Если файлов не хватает, пробуем ещё (до MAX_RETRIES)
set /a RETRY_COUNT+=1
if !RETRY_COUNT! LSS %MAX_RETRIES% (
    echo.
    echo Some files are missing. Retrying in 10 seconds...
    timeout /t 10 >nul
    goto DOWNLOAD_LOOP
)

echo.
echo =====================================================
echo DOWNLOAD FAILED AFTER %MAX_RETRIES% ATTEMPTS.
echo Please check your internet connection or use huggingface-cli.
echo =====================================================
pause
exit /b 1

:: ================================================================
:: Функция переименования файлов, сохранённых с SHA256-именами
:: ================================================================
:RenameHashFiles
setlocal enabledelayedexpansion
pushd "%DOWNLOAD_DIR%"
for %%F in (*) do (
    set "name=%%~nxF"
    set "ext=%%~xF"
    :: если имя ровно 64 символа и нет расширения – это хеш
    if "!name:~64!"=="" if "!name:~63!" neq "" if "!ext!"=="" (
        if %%~zF gtr 104857600 (
            ren "%%F" "adapter_model.safetensors"
            echo Renamed %%F to adapter_model.safetensors
        ) else (
            ren "%%F" "tokenizer.model"
            echo Renamed %%F to tokenizer.model
        )
    )
)
popd
endlocal
goto :eof

:: Определяем оригинальное имя по размеру файла
:RenameBySize
set "hashfile=%1"
set "size=%~z1"

:: Пороги: adapter_model.safetensors > 100 МБ, tokenizer.model < 10 МБ
if %size% gtr 104857600 (
    set "newname=adapter_model.safetensors"
) else (
    set "newname=tokenizer.model"
)

echo Renaming %hashfile% to %newname% (size: %size% bytes)
ren "%hashfile%" "%newname%"
goto :eof