import endotools.tests as ET
from routes import url_for
import json

"""
class TestCentrosController(ET.TestController):
    def __init__(self, *args, **kwargs):
        ET.TestController.__init__(self,  *args, **kwargs)
        self.nombre_recursos = 'centros'
        self.campos_index = ('id', 'nombre', 'codigo')
        self.campos_show = ('id', 'nombre', 'codigo', 'servicios')

    def test_101_create_allowed(self):
        data = {"nombre": "testing_created",
                "codigo": "testing_code"}
        response = self.app.post(url_for(controller='/rest/centros', format='json', action='create'),
                        params=data, extra_environ={'REMOTE_USER': 'sysadmin'}, status=201)
        id_centro_creado = json.loads(response.body)["id"]
        response = self.app.get(url_for(controller='/rest/centros', id=id_centro_creado,
                action='show', format='json'),
                extra_environ={'REMOTE_USER': 'sysadmin'}, status=200)
        centro = json.loads(response.body)
        self.assertEqual(centro[u"codigo"], u"testing_code")
        self.assertEqual(centro[u'nombre'], u"testing_created")

    def test_102_create_not_allowed(self):
        data = {"nombre": "testing_created",
                "codigo": "testing_code"}
        self.app.post(url_for(controller='/rest/centros', format='json', action='create'),
                params=data, extra_environ={'REMOTE_USER': 'normaluser'}, status=403)

    def test_103_update_allowed(self):
        data = {"nombre": "testing_update_allowed",
                "codigo": "update_allowed_code"}
        response = self.app.post(url_for(controller='/rest/centros', format='json', action='create'),
                        params=data, extra_environ={'REMOTE_USER': 'sysadmin'}, status=201)
        id_centro_creado = json.loads(response.body)["id"]
        data = {"_method": "put",
                "nombre": "testing_updated",
                "codigo": "testing_updated_code"}
        self.app.post('/rest/centros/update/' + id_centro_creado,
                params=data, extra_environ={'REMOTE_USER': 'sysadmin'}, status=200)
        response = self.app.get(url_for(controller='/rest/centros', id=id_centro_creado,
                action='show', format='json'),
                extra_environ={'REMOTE_USER': 'sysadmin'}, status=200)
        centro = json.loads(response.body)
        self.assertEqual(centro[u"nombre"], u"testing_updated")
        self.assertEqual(centro[u"codigo"], u"testing_updated_code")

    def test_104_update_not_allowed(self):
        data = {"nombre": "testing_update_not_allowed",
                "codigo": "update_not_allowed_code"}
        response = self.app.post(url_for(controller='/rest/centros', format='json', action='create'),
                        params=data, extra_environ={'REMOTE_USER': 'sysadmin'}, status=201)
        id_centro_creado = json.loads(response.body)["id"]
        data = {"_method": "put",
                "nombre": "testing_updated_2",
                "codigo": "testing_updated_code_2"}
        self.app.post('/rest/centros/update/' + id_centro_creado,
                params=data, extra_environ={'REMOTE_USER': 'normaluser'}, status=403)
        response = self.app.get(url_for(controller='/rest/centros', id=id_centro_creado,
                action='show', format='json'),
                extra_environ={'REMOTE_USER': 'normaluser'}, status=200)
        centro = json.loads(response.body)
        self.assertEqual(centro[u"nombre"], u"testing_update_not_allowed")
        self.assertEqual(centro[u"codigo"], u"update_not_allowed_code")


    def test_105_delete_allowed(self):
        data = {"nombre": "testing_created",
                "codigo": "testing_code"}
        response = self.app.post(url_for(controller='/rest/centros', format='json', action='create'),
                        params=data, extra_environ={'REMOTE_USER': 'sysadmin'}, status=201)
        id_centro_creado = json.loads(response.body)["id"]
        self.app.post('/rest/centros/delete/' + id_centro_creado, params={'_method':'delete'},
                extra_environ={'REMOTE_USER': 'sysadmin'}, status=200)

    def test_106_delete_not_allowed(self):
        data = {"nombre": "testing_created",
                "codigo": "testing_code"}
        response = self.app.post(url_for(controller='/rest/centros', format='json', action='create'),
                        params=data, extra_environ={'REMOTE_USER': 'sysadmin'}, status=201)
        id_centro_creado = json.loads(response.body)["id"]
        self.app.post('/rest/centros/delete/' + id_centro_creado, params={'_method':'delete'},
                extra_environ={'REMOTE_USER': 'normaluser'}, status=403)
"""