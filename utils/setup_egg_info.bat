@echo off

echo **************************************************  
echo * Endosys App - Setup.py egg_info              *
echo **************************************************                                              
echo.

SET OLDDIR=%cd%
SET BASE=%~dp0..\
cd %BASE%
for %%F in ("%cd%") do set RUTA_ENDOTOOLSWEB=%%~dpF
 
"%RUTA_ENDOTOOLSWEB%PortablePython\App\python.exe" "%OLDDIR%\..\setup.py" egg_info
cd %OLDDIR%
pause
