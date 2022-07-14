""" Autenticacion mediante LDAP
    Cuando es por LDAP, no usa la autenticacion por defecto del authkit (usando la BBDD)
"""
import logging
from sqlalchemy.orm import defer

from pylons import config
import ldap

log = logging.getLogger(__name__)

def _validate_ldap(username, password):
    
    # se fija si existe sin posfijo, si no existe
    # empieza por el .1
    posfijo = ""
    if not _existe_cadena_conexion():
        posfijo = ".1"
    
    # itera hasta que no encuentre mas cadenas
    while _existe_cadena_conexion(posfijo):
        try:
            log.debug("LDAP posfijo: "+ posfijo)
            #inicializar
            ldap_url = _crear_ldap_url(posfijo)
            ldap_instance = ldap.initialize(ldap_url)
            #print ldap_url

            # hacer bind con ldap y el user y luego unbind.
            cadena_simple_bind = _generar_cadena_simple_bind(username, posfijo)
            #print cadena_simple_bind
            simple_bind_obj = ldap_instance.simple_bind_s(cadena_simple_bind, password)
            ldap_instance.unbind_s()
            del ldap_instance

            # si no hay fallos es pq es OK
            log.debug("Ok")
            return True

        except ldap.LDAPError, e:
            log.error(e)
            error_str = 'LDAP ERROR: ' 
            if type(e.message) == dict and e.message.has_key('desc'):
                error_str += str(e.message['desc'])
            else:
                error_str += str(e)
            log.error(error_str)
            log.debug(error_str)

        posfijo = _siguiente_cadena(posfijo)

    return False

def _crear_ldap_url(posfijo):
    """
    crea la url del ldap
    """
    ad_dns_name = config.get('LDAP_DNS_NAME'+posfijo, '')
    ad_ldap_port = config.get('LDAP_PORT'+posfijo, '')
    return 'ldap://%s:%s' % (ad_dns_name, ad_ldap_port)


def _generar_cadena_simple_bind(username, posfijo):
    """
    genera la cadena de dn o dmain segun el modo
    """
    modo = config.get('LDAP_MODO_DN'+posfijo, '0')

    if modo == '0':
        domain = config.get('LDAP_DOMAIN'+posfijo, '')
        if domain == '':
            raise Exception("LDAP ERROR: LDAP_DOMAIN"+posfijo+" no esta configurado")
        cadena = "%s@%s"%(username, domain)

    elif modo == '1':
        dn = config.get('LDAP_DN'+posfijo, '')
        uid_or_cn = config.get('LDAP_DN_UID_CN'+posfijo, 'uid')
        if dn == '':
            raise Exception("LDAP ERROR: LDAP_DN"+posfijo+" no esta configurado")
        cadena = "%s=%s,%s"%(uid_or_cn,username, dn)

    else:
        raise Exception("LDAP ERROR: Modo no soportado")
       
    return cadena
        

def _existe_cadena_conexion(posfijo=""):
    """
    verifica si existe cadena de conexion con el posfijo dado por parametro
    """
    # checkea si esta una u otra clave dependendiendo el modo. Si hay alguna de estas, es pq hay configuracion
    if config.get('LDAP_DNS_NAME'+posfijo) is not None or config.get('LDAP_DN'+posfijo) is not None:
        return True
    else:
        return False
    
def _siguiente_cadena(posfijo):
    """
    dado un "posfijo", retorna el siguiente a usar
    """
    if posfijo == "":
        posfijo = ".1"
    else:
        posfijo = "." + str(int(posfijo[1:])+1)
    return posfijo


def valid_password(environ, username, password):
    log.debug("valid_password() username: %s", username)
    if not environ.has_key('authkit.users'):
        raise no_authkit_users_in_environ
    users = environ['authkit.users']
    if not users.user_exists(username):
        return False
    else:
        
        from endosys.model import meta
        from endosys import model

        # segun si el usuario esta marcado como 'ldap' o no, hacer
        # un tipo de autenticacion o otra
        ldap = False
        activo = True
        q = meta.Session.query(model.Usuario).filter_by(username=username.lower()).options(defer('clave'))
        log.debug("registro usuario: %s", str(q.count()))
        if q.count():
            usuario = q.one()
            ldap = usuario.ldap
            activo = usuario.activo
            log.debug("usuario.ldap=%s", str(ldap))

        if not activo:
            log.debug("usuario %s no activo")
            return False
        if ldap and int( config.get('USAR_LDAP', '0') ):
            log.debug("validar por ldap")
            if _validate_ldap(username.lower(), password): return True
        else:
            log.debug(u"validar por método de endotools")
            if users.user_has_password(username.lower(), password): return True
    return False