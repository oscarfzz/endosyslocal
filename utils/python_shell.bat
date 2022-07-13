@echo off

echo **************************************************  
echo * EndoTools Web - Shell Command line utility     *
echo **************************************************                                              
echo * This utility is for enter in pylons Shell mode *
echo **************************************************
echo.

SET OLDDIR=%cd%
SET BASE=%~dp0..\
cd %BASE%
for %%F in ("%cd%") do set RUTA_ENDOTOOLSWEB=%%~dpF

echo .ini files availables:
echo ----------------------
dir /B *.ini | findstr /v "test-endotools-sample.ini"
echo.

SET /P ARCHIVO_INI=Write the name of .ini file:
"%RUTA_ENDOTOOLSWEB%\PortablePython\App\python.exe" "%RUTA_ENDOTOOLSWEB%\PortablePython\App\Scripts\paster-script.py" shell "%ARCHIVO_INI%"
pause
