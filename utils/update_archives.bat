@echo off
SET OLDDIR=%cd%
SET BASE=%~dp0..\
cd %BASE%
FOR /f "tokens=*" %%i IN (rutabase.txt) DO SET RUTA_ENDOTOOLSWEB=%%i

"%RUTA_ENDOTOOLSWEB%\PortablePython\App\python.exe" actualizar_ficheros.py

pause