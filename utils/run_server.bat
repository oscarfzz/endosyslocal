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
for %%F in ("%cd%") do set RUTA_ENDOSYSWEB=%%~dpF

echo .ini files availables:
echo ----------------------
dir /B *.ini | findstr /v "test-endosys-sample.ini"
echo.

SET /P ARCHIVO_INI=Write the name of .ini file:
"%RUTA_ENDOSYSWEB%\PortablePython\App\python.exe" "%RUTA_ENDOSYSWEB%\PortablePython\App\Scripts\paster-script.py" serve --reload "%ARCHIVO_INI%"
pause
