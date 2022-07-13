import endotools.tests as ET
from routes import url_for
import json
from endotools.controllers.rest.exploraciones import ExploracionesController
from nose.tools import set_trace

class TestExploracionesController(ET.TestController):

    def __init__(self, *args, **kwargs):
        ET.TestController.__init__(self,  *args, **kwargs)
       	controller = ExploracionesController()
        self.nombre_recursos = controller.nombre_recursos
        self.campos_index = controller.campos_index
        self.campos_show = controller.campos_show