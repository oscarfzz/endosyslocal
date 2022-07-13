@echo off

echo **************************************************  
echo * EndoTools Web - Setup App Command line utility *
echo **************************************************                                              
echo * This utility create database tables.           *
echo * To proceed is necessary specify an .ini file   *
echo **************************************************
echo.

SET OLDDIR=%cd%
SET BASE=%~dp0..\
cd %BASE%
mkdir logs
for %%F in ("%cd%") do set RUTA_ENDOTOOLSWEB=%%~dpF

echo .ini files availables:
echo ----------------------
dir /B *.ini | findstr /v "test-endotools-sample.ini"
echo.

SET /P ARCHIVO_INI=Write the name of .ini file to configure EndoTools Web: 
"%RUTA_ENDOTOOLSWEB%PortablePython\App\python.exe" "%RUTA_ENDOTOOLSWEB%PortablePython\App\Scripts\paster-script.py" setup-app %ARCHIVO_INI%
cd %OLDDIR%
pause
