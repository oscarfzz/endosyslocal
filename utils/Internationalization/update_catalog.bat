echo ***************************************************  
echo * Endosys App - Update Catalog                  *
echo ***************************************************
echo.

SET OLDDIR=%cd%
SET BASE=%~dp0..\..\
cd %BASE%
for %%F in ("%cd%") do set RUTA_ENDOSYSWEB=%%~dpF

FOR /f %%i IN (rutabase.txt) DO SET RUTA_ENDOSYSWEB=%%i

"%RUTA_ENDOSYSWEB%\PortablePython\App\python.exe" setup.py update_catalog

pause