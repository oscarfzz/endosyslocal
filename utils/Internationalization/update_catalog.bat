echo ***************************************************  
echo * EndoTools Web - Update Catalog                  *
echo ***************************************************
echo.

SET OLDDIR=%cd%
SET BASE=%~dp0..\..\
cd %BASE%
for %%F in ("%cd%") do set RUTA_ENDOTOOLSWEB=%%~dpF

FOR /f %%i IN (rutabase.txt) DO SET RUTA_ENDOTOOLSWEB=%%i

"%RUTA_ENDOTOOLSWEB%\PortablePython\App\python.exe" setup.py update_catalog

pause