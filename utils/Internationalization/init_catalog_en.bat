FOR /f %%i IN (rutabase.txt) DO SET RUTA_ENDOTOOLSWEB=%%i

%RUTA_ENDOTOOLSWEB%\PortablePython2.7.2.1\App\python.exe setup.py init_catalog -l en

pause