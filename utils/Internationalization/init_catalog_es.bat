FOR /f %%i IN (rutabase.txt) DO SET RUTA_ENDOSYSWEB=%%i

%RUTA_ENDOSYSWEB%\PortablePython2.7.2.1\App\python.exe setup.py init_catalog -l es

pause