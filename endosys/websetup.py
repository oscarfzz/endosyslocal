"""Setup the endotools application"""
def __(msg):
    """ Para que al importar modulos que usen i18n._ no den error, ya que en
        websetup no está inicializado esto.
    """
    return msg

import pylons.i18n
pylons.i18n._ = __

import logging
import __builtin__

from paste.deploy import appconfig
from pylons import config
from authkit.users.sqlalchemy_driver import UsersFromDatabase

from endosys.config.environment import load_environment
from endosys.lib.usuarios.seguridad import delete_deprecated_roles_BBDD, crear_roles_BBDD, roles
from endosys.model.medicos import Medico
from endosys.model.usuarios import Usuario, t_usuarios
from endosys.model import Centro
from endosys.tests.fixtures import create_basic_data
from endosys.lib.misc import get_version_txt, update_version_number_db
from endosys.lib.db import nombre_tabla

log = logging.getLogger(__name__)

def setup_config(command, filename, section, vars):

    """Place any commands to setup endotools here"""
    conf = appconfig('config:' + filename)
    load_environment(conf.global_conf, conf.local_conf)

    import os
    from endosys import model
    from endosys.model import meta

    # Si el INI utilizado es "test-endotools-sample.ini",
    # se está haciendo el testing.
    testing = (os.path.basename(filename) == "test-endotools-sample.ini")
    
    users = UsersFromDatabase(model)
    if testing:
        log.info('Dropping existing tables...')
        meta.metadata.drop_all(bind=meta.engine, checkfirst=True)
        meta.Session.commit()

    log.info("Creating tables")
    meta.metadata.create_all(bind=meta.engine)
    log.info("Successfully setup")

    # Eliminar los roles deprecados
    delete_deprecated_roles_BBDD(users)

    # Crear los roles
    crear_roles_BBDD(users)

    # Crear los usuarios por defecto y asignarle roles
    if not users.user_exists('admin'):
        users.user_create('admin', password='endotools')
        meta.Session.flush()

        #  Crear un medico vinculado al user admin
        medico = Medico()
        medico.username = 'admin'
        medico.nombre = 'Administrator'#IDIOMA
        meta.Session.save(medico)

        # se hace un insert lo mas simple posible para que sea compatible con todas las base de datos.
        # No testeado en oracle
        meta.Session.execute("INSERT INTO %s (username) VALUES ('%s')" % (nombre_tabla(meta.engine, 'Usuarios'),'admin'))
        
        try:
            # Si no se hace esto no puede iniciar sesion
            meta.Session.execute("UPDATE %s SET activo=1, tipo=1 WHERE username='%s'" % (nombre_tabla(meta.engine, 'Usuarios'),'admin'))
        except Exception, e:
            log.warning(str(e))

    if not users.user_exists('sysadmin'):
        users.user_create('sysadmin', password='endotools')
        meta.Session.flush()
        
        #  Crear un medico vinculado al user sysadmin
        medico = Medico()
        medico.username = 'sysadmin'
        medico.nombre = 'System administrator'#IDIOMA
        meta.Session.save(medico)

        # se hace un insert lo mas simple posible para que sea compatible con todas las base de datos.
        # No testeado en oracle
        meta.Session.execute("INSERT INTO %s (username) VALUES ('%s')" % (nombre_tabla(meta.engine, 'Usuarios'),'sysadmin'))
        try:
            # Si no se hace esto no puede iniciar sesion
            meta.Session.execute("UPDATE %s SET activo=1, tipo=1 WHERE username='%s'" % (nombre_tabla(meta.engine, 'Usuarios'),'sysadmin'))
        except Exception, e:
            log.warning(str(e))

    #  Asignar todos los roles al usario admin (para pruebas!)
    for role in filter(lambda r: not r.startswith('__') , __builtin__.vars(roles)):
        if not users.user_has_role('admin', role):
            users.user_add_role('admin', role)

        if not users.user_has_role('sysadmin', role):
            users.user_add_role('sysadmin', role)

    # Crear centro por defecto
    if not testing and meta.Session.query(Centro).count() == 0:
        centro = Centro()
        centro.codigo = 'FACILITY'#IDIOMA
        centro.nombre = u'Facility'#IDIOMA
        meta.Session.save(centro)
        meta.Session.flush()

    if testing:
        create_basic_data()

    # actualiza la version del endotools
    update_version_number_db(meta.Session)

    meta.Session.commit()
