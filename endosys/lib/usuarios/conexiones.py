_usuarios_conectados = []

def intentar_conexion(username):
    """ comprueba si el usuario esta en la lista de usuarios conectados. Si
    no es asi lo anade y devuelve True. Si ya estaba devuelve False.
    """
##    print "intentar_conexion:", username
##    print "lista:", _usuarios_conectados
    if username in _usuarios_conectados:
##        print "  el usuario ya esta en la lista"
##        print "lista:", _usuarios_conectados
        return False
    _usuarios_conectados.append(username)
##    print "  el usuario se ha anadido a la lista"
##    print "lista:", _usuarios_conectados
    return True

def desconectar_usuario(username):
    """ quita al usuario de la lista de usuarios conectados. Si ya no estaba no hace nada. """
##    print "desconectar_usuario:", username
##    print "lista:", _usuarios_conectados
    if username in _usuarios_conectados:
        _usuarios_conectados.remove(username)
##        print "  el usuario se ha quitado de la lista"
##    else:
##        print "  el usuario no estaba en la lista"
##    print "lista:", _usuarios_conectados
