@echo off

echo ***************************************************  
echo * Endosys App - RUN SERVER Command line utility *
echo ***************************************************                                              
echo * This utility is for execute an instance of      *
echo * Endosys App Server                            *
echo * (not suitable for production)                   *
echo ***************************************************
echo.

SET OLDDIR=%cd%
SET BASE=%~dp0..\
cd %BASE%
for %%F in ("%cd%") do set RUTA_ENDOTOOLSWEB=%%~dpF
FOR /f "tokens=*" %%i IN (env_version.txt) DO SET ENV_VERSION=%%i

echo .ini files availables:
echo ----------------------
dir /B *.ini | findstr /v "test-endotools-sample.ini"
echo.
echo.

SET /P ARCHIVO_INI=Write the name of .ini file:
%RUTA_ENDOTOOLSWEB%\virtualenv\env_%ENV_VERSION%\Scripts\paster.exe serve --reload "%ARCHIVO_INI%"

cd %OLDDIR%
pause
