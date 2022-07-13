import endotools.tests as ET
from routes import url_for
import json
from endotools.controllers.rest.agendas import AgendasController
from nose.tools import set_trace

class TestAgendasController(ET.TestController):
    def __init__(self, *args, **kwargs):
        ET.TestController.__init__(self,  *args, **kwargs)
        agendas_controller = AgendasController()
        self.nombre_recursos = agendas_controller.nombre_recursos
        self.campos_index = agendas_controller.campos_index
        self.campos_show = agendas_controller.campos_show

    def test_agendas_create_allowed(self):
        """ Test de crear una agenda con usuario sysadmin """
        data = {"nombre": "testing_created",
                "codigo": "testing_code",
                "servicio_id": 1}
        response = self.app.post(url_for(controller='/rest/agendas', format='json', action='create'),
                        params=data, extra_environ={'REMOTE_USER': 'sysadmin'}, status=201)
        id_agenda_creada = json.loads(response.body)["id"]
        response = self.app.get(url_for(controller='/rest/agendas', id=id_agenda_creada,
                action='show', format='json'),
                extra_environ={'REMOTE_USER': 'sysadmin'}, status=200)
        agenda = json.loads(response.body)
        self.assertEqual(agenda[u"codigo"], u"testing_code")
        self.assertEqual(agenda[u'nombre'], u"testing_created")
        self.assertEqual(agenda[u'servicio'][u'id'], u"1")
    
    def test_agendas_create_not_allowed(self):
        """ Test de no dejar crear una agenda con otro usuario que no sea sysadmin """
        data = {"nombre": "testing_created",
                "codigo": "testing_code",
                "servicio_id": 1}
        response = self.app.post(url_for(controller='/rest/agendas', format='json', action='create'),
                    params=data, extra_environ={'REMOTE_USER': 'normaluser'}, status=403)

    def test_agendas_create_without_nombre(self):
        """ Error al crear una agenda sin nombre """
        data = {"codigo": "testing_code",
                "servicio_id": 1}
        response = self.app.post(url_for(controller='/rest/agendas', format='json', action='create'),
                        params=data, extra_environ={'REMOTE_USER': 'sysadmin'}, status=400)
        response_json = json.loads(response.body)
        self.assertEqual(response_json['data'], u"El campo 'nombre' es obligatorio")

    def test_agendas_create_without_servicio(self):
        """ Error al crear una agenda sin servicio_id """
        data = {"codigo": "testing_code",
                "nombre": "testing_nombre",}
        response = self.app.post(url_for(controller='/rest/agendas', format='json', action='create'),
                        params=data, extra_environ={'REMOTE_USER': 'sysadmin'}, status=400)
        response_json = json.loads(response.body)
        self.assertEqual(response_json['data'], u"El campo 'servicio_id' es obligatorio")

    def test_agendas_update_allowed(self):
        """ Actualizar una agenda con el usuario sysadmin """
        data = {"nombre": "testing_update_allowed",
                "codigo": "update_allowed_code",
                "servicio_id": 1}
        response = self.app.post(url_for(controller='/rest/agendas', format='json', action='create'),
                        params=data, extra_environ={'REMOTE_USER': 'sysadmin'}, status=201)
        id_agenda_creada = json.loads(response.body)["id"]
        data = {"_method": "put",
                "nombre": "testing_updated",
                "codigo": "testing_updated_code",
                "servicio_id": 2}
        self.app.post('/rest/agendas/update/' + id_agenda_creada,
                params=data, extra_environ={'REMOTE_USER': 'sysadmin'}, status=200)
        response = self.app.get(url_for(controller='/rest/agendas', id=id_agenda_creada,
                action='show', format='json'),
                extra_environ={'REMOTE_USER': 'sysadmin'}, status=200)
        agenda = json.loads(response.body)
        self.assertEqual(agenda[u"nombre"], u"testing_updated")
        self.assertEqual(agenda[u"codigo"], u"testing_updated_code")

    def test_agendas_update_not_allowed(self):
        """ No dejar actualizar una agenda con otro usuario que no sea sysadmin """
        data = {"nombre": "testing_update_not_allowed",
                "codigo": "update_not_allowed_code",
                "servicio_id": 1}
        response = self.app.post(url_for(controller='/rest/agendas', format='json', action='create'),
                        params=data, extra_environ={'REMOTE_USER': 'sysadmin'}, status=201)
        id_agenda_creada = json.loads(response.body)["id"]
        data = {"_method": "put",
                "nombre": "testing_updated_2",
                "codigo": "testing_updated_code_2",
                "servicio_id": 2}
        self.app.post('/rest/agendas/update/' + id_agenda_creada,
                params=data, extra_environ={'REMOTE_USER': 'normaluser'}, status=403)
        response = self.app.get(url_for(controller='/rest/agendas', id=id_agenda_creada,
                action='show', format='json'),
                extra_environ={'REMOTE_USER': 'normaluser'}, status=200)
        agenda = json.loads(response.body)
        self.assertEqual(agenda[u"nombre"], u"testing_update_not_allowed")
        self.assertEqual(agenda[u"codigo"], u"update_not_allowed_code")


    def test_agendas_delete_allowed(self):
        """ Borrar una agenda con el sysadmin """
        data = {"nombre": "testing_created",
                "codigo": "testing_code",
                "servicio_id": 1}
        response = self.app.post(url_for(controller='/rest/agendas', format='json', action='create'),
                        params=data, extra_environ={'REMOTE_USER': 'sysadmin'}, status=201)
        id_agenda_creada = json.loads(response.body)["id"]
        self.app.post('/rest/agendas/delete/' + id_agenda_creada, params={'_method':'delete'},
                extra_environ={'REMOTE_USER': 'sysadmin'}, status=200)

    def test_agendas_delete_not_allowed(self):
        """ No dejar borrar una agenda con sysadmin """
        data = {"nombre": "testing_created",
                "codigo": "testing_code",
                "servicio_id": 1}
        response = self.app.post(url_for(controller='/rest/agendas', format='json', action='create'),
                        params=data, extra_environ={'REMOTE_USER': 'sysadmin'}, status=201)
        id_agenda_creada = json.loads(response.body)["id"]
        self.app.post('/rest/agendas/delete/' + id_agenda_creada, params={'_method':'delete'},
                extra_environ={'REMOTE_USER': 'normaluser'}, status=403)