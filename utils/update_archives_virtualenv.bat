@echo off
SET OLDDIR=%cd%
SET BASE=%~dp0..\
cd %BASE%
for %%F in ("%cd%") do set RUTA_ENDOTOOLSWEB=%%~dpF
FOR /f "tokens=*" %%i IN (env_version.txt) DO SET ENV_VERSION=%%i

start "" "%RUTA_ENDOTOOLSWEB%\virtualenv\env_%ENV_VERSION%\Scripts\python.exe" actualizar_ficheros.py
cd %OLDDIR%
