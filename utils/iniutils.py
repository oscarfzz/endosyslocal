'''
Utilidades parar manipular el archivo INI
'''

import sys, os, glob, ConfigParser, collections
from configobj import ConfigObj

scriptpath = os.path.dirname(os.path.abspath(__file__))
rootpath = os.path.abspath(os.path.join(scriptpath, '..'))

TEMPLATEINI_FILENAME = "endosysapp-sample.ini"
TESTINI_FILENAME = "test-endosys-sample.ini"

####################
# test
ini = ConfigObj("endosysapp-sample.ini", list_values = False, interpolation = False)
f = open("endosysapp-sample.xxx.ini", 'wb')
ini.write(f)
f.close()

####################

def _proc_params(infile, outfile, outfileext = "output.ini"):
    if not infile:
        # Buscar si hay un solo INI
        # (omitir test-endosys-sample.ini)
        inis = glob.glob(os.path.join(rootpath, '*.ini'))
        if TESTINI_FILENAME in inis:
            inis.remove(TESTINI_FILENAME)
        if len(inis) == 1:
            infile = inis[0]
        else:
            raise Exception("Se ha encontrado mas de un archivo INI. Por favor, indique el archivo a utilizar.")

    if not outfile:
        # el INI formateado se escribe por defecto en la misma ubicación del script,
        # con el mismo nombre que el de entrada pero distinta extensión.
        outfile = os.path.join(scriptpath, os.path.splitext(os.path.split(infile)[1])[0] + '.' + outfileext)
        
    return infile, outfile

    
def simplify(infile = "", outfile = ""):
    """
    Esta función formatea el archivo INI de la siguiente manera:
    - Todas las claves en minúsculas
    - Las secciones ordenadas alfabéticamente, excepto [DEFAULT] que siempre es la primera
    - Las claves de cada sección ordenadas alfabéticamente
    - Se omiten todos los comentarios

    Esto permite comparar de forma precisa dos archivos INI con herramientas tipo
    winmerge.
    El primer argumento es el nombre del archivo INI, sin ruta (siempre se busca en la raiz)
    Si se omite, si solo hay un archivo INI en la raíz se usará ése, si no se
    deberá intrdocir.
    El segundo argumento es el nombre de destino - si se omite se ubicará en la misma
    carpeta que el script, con el nombre "nombre.formatted.ini".

    Referencia:
    https://docs.python.org/2/library/configparser.html
    https://stackoverflow.com/questions/1134071/keep-configparser-output-files-sorted#answer-41243181
    """

    # trabajar en la raiz, donde está el INI
    os.chdir( os.path.join(scriptpath , '..') )

    infile, outfile = _proc_params(infile, outfile, "simplified.ini")

    config = ConfigParser.RawConfigParser(dict_type = collections.OrderedDict)
    config.read(infile)

    # ordenar el contenido de cada sección alfabéticamente
    for section in config._sections:
        config._sections[section] = collections.OrderedDict(sorted(config._sections[section].items(), key=lambda t: t[0]))

    # ordenar el contenido de la sección DEFAULT alfabéticamente
    # (no está incluida en config._sections)
    config._defaults = collections.OrderedDict(sorted(config._defaults.items(), key=lambda t: t[0]))

    # ordenar todas las secciones alfabéticamente
    config._sections = collections.OrderedDict(sorted(config._sections.items(), key=lambda t: t[0] ))

    # escribir el archivo
    f = open(outfile, 'wb')
    config.write(f)
    f.close()

def format(infile = "", outfile = ""):
    """
    Esta función crea un nuevo INI utilizando template "endosysapp-sample.ini"
    y rellenando los valores obtenidos de otro archivo INI.
    Si se omite infile, se usará el archivo INI de la raiz, a no ser que haya
    más de uno.
    
    La forma de hacerlo es, leer todas las claves del archivo de entrada,
    escribirlas en el de salida, y guardarlo con el nombre indicado.
    
    TODO
    -claves en el ini de entrada que no existen en el template? añadirlas?
    -claves del template que no están en el ini de entrada... dejarlas tal cual
    y loggearlo?
    """
    # trabajar en la raiz, donde está el INI
    os.chdir( os.path.join(scriptpath , '..') )

    infile, outfile = _proc_params(infile, outfile, "formatted.ini")
    
    config = ConfigParser.RawConfigParser(dict_type = collections.OrderedDict)
    config.read(infile)
    templateini = ConfigObj(os.path.join(rootpath, TEMPLATEINI_FILENAME), list_values = False, interpolation = False)
    
    # recorrer todas las claves del INI de entrada y asignar su valor al de salida.
    #TODO!
    
    f = open(outfile, 'wb')
    templateini.write(f)
    f.close()
