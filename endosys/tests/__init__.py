# -*- coding: utf-8 -*-
"""Pylons application test package

When the test runner finds and executes tests within this directory,
this file will be loaded to setup the test environment.

It registers the root directory of the project in sys.path and
pkg_resources, in case the project hasn't been installed with
setuptools. It also initializes the application via websetup (paster
setup-app) with the project's test.ini configuration file.
"""
import os
import sys
from unittest import TestCase

import pkg_resources
import paste.fixture
import paste.script.appinstall

from paste.deploy import loadapp
from routes import url_for
import json

__all__ = ['url_for', 'TestController']

here_dir = os.path.dirname(os.path.abspath(__file__))
conf_dir = os.path.dirname(os.path.dirname(here_dir))
conf_dir = os.path.join(conf_dir,'utils','tests')

sys.path.insert(0, conf_dir)
pkg_resources.working_set.add_entry(conf_dir)
pkg_resources.require('Paste')
pkg_resources.require('PasteScript')

test_file = os.path.join(conf_dir, 'test-endosys-sample.ini')
cmd = paste.script.appinstall.SetupCommand('setup-app')
#cmd.run([test_file])

class TestController(TestCase):

    def __init__(self, *args, **kwargs):
        from paste import lint
        lint.check_content_type = lambda status, headers: None
        wsgiapp = loadapp('config:test-endosys-sample.ini', relative_to=conf_dir)
        self.app = paste.fixture.TestApp(wsgiapp)
        TestCase.__init__(self, *args, **kwargs)
        self.nombre_recursos = None
        self.campos_index = None
        self.campos_show = None
    
    """
    def test_001_index(self):
        if self.nombre_recursos is not None and self.campos_index is not None:
            response = self.app.get(url_for(controller='/rest/' + self.nombre_recursos,
                action='index', format='json'), #headers={'Content-Type': 'application/json'},
                extra_environ={'REMOTE_USER': 'sysadmin'}, status=200)
            objetos = json.loads(response.body)
            for campo in self.campos_index:
                self.assertEqual(objetos[0].has_key(campo), True)

            assert (len(objetos) > 0), "No se retorna ningún objeto para %s" % self.nombre_recursos
        else:
            assert 0, "No se ha definido nombre_recursos o campos_index."

    
    def test_002_show(self):
        if self.nombre_recursos is not None and self.campos_show is not None:
            response = self.app.get(url_for(controller='rest/' + self.nombre_recursos, action='index', format='json'),
                                    extra_environ={'REMOTE_USER': 'sysadmin'}, status=200)
            objetos = json.loads(response.body)
            objeto_id = objetos[0]["id"]
            response = self.app.get(url_for(controller='rest/' + self.nombre_recursos, id=objeto_id, action='show',
                                            format='json'), extra_environ={'REMOTE_USER': 'sysadmin'}, status=200)
            objeto = json.loads(response.body)
            
            self.assertEqual(objeto[u"id"], objeto_id)
            for campo in self.campos_show:
                assert objeto.has_key(campo), "No se retorna un valor de %s para %s." % (campo, self.nombre_recursos)
        else:
            assert 0, "No se ha definido nombre_recursos o campos_show."

    def test_003_show_noid(self):
        if self.nombre_recursos:
            # Si no indicamos id devuelve 404
            self.app.get(url_for(controller='rest/' + self.nombre_recursos, id='', action='show', format='json'),
                                 extra_environ={'REMOTE_USER': 'sysadmin'}, status=404)
        else:
            assert 0, "No se ha definido nombre_recursos."
    """