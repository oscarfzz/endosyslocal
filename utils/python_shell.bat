@echo off

echo **************************************************  
echo * Endosys App - Shell Command line utility     *
echo **************************************************                                              
echo * This utility is for enter in pylons Shell mode *
echo **************************************************
echo.

SET OLDDIR=%cd%
SET BASE=%~dp0..\
cd %BASE%
for %%F in ("%cd%") do set RUTA_ENDOSYSWEB=%%~dpF

echo .ini files availables:
echo ----------------------
dir /B *.ini | findstr /v "test-endosys-sample.ini"
echo.

SET /P ARCHIVO_INI=Write the name of .ini file:
"%RUTA_ENDOSYSWEB%\PortablePython\App\python.exe" "%RUTA_ENDOSYSWEB%\PortablePython\App\Scripts\paster-script.py" shell "%ARCHIVO_INI%"
pause
