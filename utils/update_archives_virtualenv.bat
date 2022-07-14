@echo off
SET OLDDIR=%cd%
SET BASE=%~dp0..\
cd %BASE%
for %%F in ("%cd%") do set RUTA_ENDOSYSWEB=%%~dpF
FOR /f "tokens=*" %%i IN (env_version.txt) DO SET ENV_VERSION=%%i

start "" "%RUTA_ENDOSYSWEB%\virtualenv\env_%ENV_VERSION%\Scripts\python.exe" actualizar_ficheros.py
cd %OLDDIR%
