echo off

:: Autor: Javier C.
:: Fecha: 2026-03-14
:: entrypoint.bat – Iniciar BD y ejecutar el monitor de acciones

:: Definición de variables de entorno
SET RUTA_BD=.\data\monitor.db
SET ADMIN_PUERTO=8501

SET DIA=%DATE:~0,2%
SET MES=%DATE:~3,2%
SET ANO=%DATE:~6,4%
SET FECHA=%ANO%%MES%%DIA%

:: Forzar UTF-8 en la consola
:: CHCP 65001 > nul
:: SET PYTHONUTF8=1

echo "=== Stock Monitor arrancando el %date% ==="
python .\monitor_acciones\arrancar.py
:: python -X utf8 .\monitor_acciones\arrancar.py   > .\log\monitor_%FECHA%.log 2>&1



:: Modo completo: monitor + panel web (lo más habitual)
REM python arrancar.py

:: Solo el panel de administración (sin el monitor)
REM python arrancar.py --solo-admin

:: Solo el monitor (sin UI)
REM python arrancar.py --solo-monitor

:: Un solo ciclo de comprobación y salir
REM python arrancar.py --una-vez

:: Puerto personalizado para Streamlit
REM python arrancar.py --puerto 8080