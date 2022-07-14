# funcion que devuelve la plantilla del signin


#from endotools.lib.base import *

#def signin():
#    return render('/signin.mako')


#
# por lo que he leido no se puede hacer el render() aqui ya que a lo mejor aun
# no se ha inicializado esa funcion, y se ha de hacer a m?s bajo nivel
# adem?s, el %s para que no pasen no s? que cosas, se sustituye en la plantilla por FORM_ACTION
#


import pylons
from pylons.templating import Buffet
from pylons import config
import endotools.lib.helpers as h

class MyBuffet(Buffet):
    def _update_names(self, ns):
        return ns

def_eng = config['buffet.template_engines'][0]
buffet = MyBuffet(
    def_eng['engine'],
    template_root=def_eng['template_root'],
    **def_eng['template_options']
)

for e in config['buffet.template_engines'][1:]:
    buffet.prepare(
        e['engine'],
        template_root=e['template_root'],
        alias=e['alias'],
        **e['template_options']
    )

class State:
    pass

c = State()
c.user = 'None'

def make_template():
    s = buffet.render(
        template_name="/signin.mako",
        namespace=dict(h=h, c=State())
    ).replace("%", "%%").replace("FORM_ACTION", "%s")
    return s