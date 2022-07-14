@echo off

echo **************************************************  
echo * Endosys App - Setup.py egg_info              *
echo **************************************************                                              
echo.

SET OLDDIR=%cd%
SET BASE=%~dp0..\
cd %BASE%
for %%F in ("%cd%") do set RUTA_ENDOSYSWEB=%%~dpF
 
"%RUTA_ENDOSYSWEB%PortablePython\App\python.exe" "%OLDDIR%\..\setup.py" egg_info
cd %OLDDIR%
pause
