@echo off
REM GVAdictos Launcher - Seleccionar interfaz
REM Actualizado para Ola D, E, F con toda la funcionalidad

cls
echo.
echo ========================================
echo     GVAdictos - Oposiciones GVA
echo ========================================
echo.
echo Opciones:
echo.
echo 1) Interfaz Streamlit (Estudio Local)
echo 2) API REST FastAPI (Desarrollo/Testing)
echo 3) Ambas (Streamlit + API en puertos diferentes)
echo 4) Reconstruir ranking de examenes oficiales
echo 5) Salir
echo.

set /p choice="Selecciona una opcion (1-5): "

if "%choice%"=="1" goto streamlit
if "%choice%"=="2" goto api
if "%choice%"=="3" goto both
if "%choice%"=="4" goto rebuild_exams
if "%choice%"=="5" goto exit
goto invalid

:rebuild_exams
cls
echo.
echo Reconstruyendo ranking de examenes oficiales...
echo (parseo + OCR + inferencia + barrida global)
echo.
python scripts\run_exam_pipeline.py
goto end

:streamlit
cls
echo.
echo Iniciando GVAdictos Streamlit...
echo.
python -m streamlit run app.py --logger.level=info
goto end

:api
cls
echo.
echo Instalando dependencias de API...
pip install -q -r requirements-api.txt
echo.
echo Iniciando API FastAPI en puerto 8000...
echo Documentacion: http://localhost:8000/docs
echo.
python -m uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
goto end

:both
cls
echo.
echo Instalando dependencias de API...
pip install -q -r requirements-api.txt
echo.
echo ========================================
echo Streamlit estara en: http://localhost:8501
echo API estara en:       http://localhost:8000
echo Documentacion:       http://localhost:8000/docs
echo ========================================
echo.
echo Abre dos terminales:
echo Terminal 1 (Streamlit):
echo   python -m streamlit run app.py
echo.
echo Terminal 2 (API):
echo   python -m uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
echo.
echo Presiona Enter para abrir Terminal 1...
pause
start python -m streamlit run app.py
echo.
echo Presiona Enter para abrir Terminal 2...
pause
start python -m uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
goto end

:invalid
cls
echo.
echo Opcion invalida. Intenta de nuevo.
echo.
timeout /t 2
goto launcher

:exit
cls
echo.
echo Saliendo...
timeout /t 1
exit

:end
echo.
pause
