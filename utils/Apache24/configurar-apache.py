#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from os import path
from os import name as osname
from os import listdir
from os import remove
from shutil import copyfile
from fileinput import input
from subprocess import call
import ConfigParser
import sys
import pprint


def copy_file(origen, destino):
    if path.exists(destino):
        print(u"El fichero %s ya existe y si continua se reemplazará," % \
              destino)
        answer = raw_input("realmente desea continuar? (S/n) ")
        if len(answer) > 0 and answer[0].lower() != 's':
            return False
    
    print("Copiando fichero %s" % path.basename(origen))
    try:
        copyfile(origen, destino)
        return True
    except IOError:
        print("Ha ocurrido un error al copiar el fichero.", file=sys.stderr)
        print(IOError, file=sys.stderr)
        if 'mod_wsgi' in origen:
            print("Es posible que el fichero %s este siendo usado," % destino,
                   file=sys.stderr)
            print("Pare todos los servicios de Apache.", file=sys.stderr)
        return False

def configure_file(origen, destino, **data):
    if path.exists(destino):
        print(u"El fichero %s ya existe y si continua se reemplazará," % \
              destino)
        answer = raw_input("realmente desea continuar? (S/n) ")
        if len(answer) > 0 and answer[0].lower() != 's':
            return False
        else:
            remove(destino)

    APACHE_DIR = data['APACHE_DIR']
    NOMBRE = data['NOMBRE']
    ENDOTOOLS = data['ENDOTOOLS']
    PORT = data ['PORT']
    SSL_PORT = data['SSL_PORT']
    ENV_VERSION = data['ENV_VERSION']
    try:
        fichero_origen = open(origen, 'r')
        fichero_destino = open(destino, 'w')
        configuracion = fichero_origen.read()
        fichero_origen.close()
        print(u"Configurando fichero '%s' con los siguientes parámetros:" %
               destino)
        pprint.pprint(data, stream=None, indent=1, width=80, depth=None)
        fichero_destino.write(configuracion.format(ENDOTOOLS=ENDOTOOLS,
                                                   PORT=PORT,
                                                   SSL_PORT=SSL_PORT,
                                                   NOMBRE=NOMBRE,
                                                   APACHE_DIR=APACHE_DIR,
                                                   ENV_VERSION=ENV_VERSION))
        fichero_destino.close()
        return True
    except Exception as inst:
        print("Ha ocurrido un error al configurar el fichero.",
              file=sys.stderr)
        print(inst, file=sys.stderr)
        return False

def configurar_apache():
    base = path.dirname(path.realpath(__file__))
    endotools_base = path.dirname(path.dirname(path.dirname(base)))
    general_config = 'httpd.conf'
    endotools_config = 'httpd-endotools.conf'
    endotools_ssl_config = 'httpd-endotools-ssl.conf'
    module = 'mod_wsgi.so'

    if not path.exists('C:\endosysapp\Apache24'):
        apache_dir = raw_input('Indicar directorio base de Apache: ')
    else:
        answer = raw_input("Desea usar el Apache detectado en" + \
                           " 'C:\endosysapp\Apache24'? (S/n) ")
        if len(answer) < 1 or answer[0].lower() != 'n':
            apache_dir = 'C:\endosysapp\Apache24'
        else:
            apache_dir = raw_input('Indicar directorio base de Apache: ')

    if not path.exists(path.join(apache_dir, 'bin', 'httpd.exe')):
        print("No existe ningún Apache en %s." % apache_dir, file=sys.stderr)
        exit(1)

    # Buscamos si hay un fichero .ini, si no hay o hay multiples preguntamos
    # por el nombre.
    inis = []
    for file in listdir(path.join(endotools_base, 'endosysapp')):
        if file.endswith(".ini") and not 'test-endotools-sample.ini' in file:
            inis.append(file.replace('.ini',''))

    if len(inis) == 1:
        nombre = inis[0]
        print("Usamos %s.ini como fichero de configuración de endotools." %
              nombre)
    else:
        nombre = path.basename(raw_input("Indique el nombre del fichero" + \
                              " ini a usar (dev.ini): " ).replace('.ini',''))
        if len(nombre) == 0:
            nombre = 'dev'

    # Buscamos en la configuración del .ini el puerto a usar.
    port = ''
    if path.exists(path.join(endotools_base, 'endosysapp', '%s.ini' % nombre)):
        config = ConfigParser.RawConfigParser()
        config.read(path.join(endotools_base, 'endosysapp', '%s.ini' % nombre))
        port = config.get('server:main', 'port')

    print("Configuramos el fichero 'endotools.wsgi' para que use '%s.ini'." %
          nombre)
    for line in input(path.join(endotools_base, 'endosysapp', 'endotools.wsgi'),
                      inplace=True):
        if "ini_file =" in line:
            print('ini_file = "%s.ini"' % nombre)
        else:
            print(line, end='')

    # Si no encontramos el puerto en el .ini por defecto lo configuramos en el 80.
    if len(port) == 0:
        port = "80"
        
    # Si no existe instalamos el modulo WSGI.
    copy_file(path.join(base, module), path.join(apache_dir, 'modules', module))

    # Buscamos la version del entorno.
    file = open(path.join(endotools_base, 'endosysapp', 'env_version.txt'), 'r')
    env_version = file.read()
    file.close()

    data = { 'ENDOTOOLS': endotools_base,
             'NOMBRE': nombre,
             'PORT': port,
             'SSL_PORT': "443",
             'APACHE_DIR': apache_dir,
             'ENV_VERSION': env_version}
    # Copiamos la configuración de Apache httpd.conf
    apache_file = path.join(apache_dir, 'conf', general_config)
    configure_file(path.join(base, general_config), apache_file, **data)

    # Copiamos las configuraciones extras
    extras = [endotools_config, endotools_ssl_config]
    for extra in extras:
        extra_file = path.join(apache_dir, 'conf', 'extra', extra)
        configure_file(path.join(base, extra), extra_file, **data)

    # Tratamos de instalar el servicio en Windows
    if osname == 'nt':
        answer = raw_input('Desea instalar el servicio "Apache 2.4"' + \
                           ' (EndoTools: %s)"? (S/n) ' % nombre)
        if len(answer) == 0 or answer[0].lower() == 's':
            call([path.join(apache_dir, 'bin', 'httpd'), '-k', 'install', '-n',
                  'Apache 2.4 (EndoTools: %s)' % nombre])

def main():
    configurar_apache()
	
if __name__ == "__main__":
    main()