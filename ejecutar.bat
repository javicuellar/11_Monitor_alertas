echo off

:: Autor: Javier C.
:: Fecha: 2026-03-14
:: entrypoint.bat – Iniciar BD y ejecutar el monitor de acciones

:: Definición de variables de entorno
SET RUTA_BD=.\data\monitor.db

SET DIA=%DATE:~0,2%
SET MES=%DATE:~3,2%
SET ANO=%DATE:~6,4%
SET FECHA=%ANO%%MES%%DIA%

:: Forzar UTF-8 en la consola
:: CHCP 65001 > nul
:: SET PYTHONUTF8=1

echo "=== Stock Monitor arrancando el %date% ==="
python -X utf8 .\stock_monitor\main.py   > .\log\monitor_%FECHA%.log 2>&1
