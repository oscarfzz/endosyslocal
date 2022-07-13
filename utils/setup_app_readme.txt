Si aparece el error:
	"No modules are listed in top_level.txt"

La solución es: 
- ir al directorio del raiz del proyecto
- ejecutar: RUTA_PYTHON\App\python.exe setup.py egg_info
- ejecutar: RUTA_PYTHON\App\python.exe setup.py develop