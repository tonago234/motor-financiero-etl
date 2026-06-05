@echo off
echo Iniciando Motor Financiero...

REM 1. Viajamos a la carpeta exacta de tu proyecto
cd C:\ProyectosPersonales\Python\motor-financiero-etl

REM 2. Activamos el entorno virtual
call .venv\Scripts\activate

REM 3. Ejecutamos el motor ETL
python etl_mercadopago.py

echo Proceso finalizado.