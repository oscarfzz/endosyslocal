# -*- coding: utf-8 -*-

"""
Herramienta del Admin: Actualización de la base de datos.

Actualiza la base de datos a la versión actual.

Se debería poder ejecutar las veces que se quiera sin riesgo de perder información
o generar ningún problema.

Inicialmente solo realizará las modificaciones de tablas. La creación de tablas
ya se hace mediante el SETUP-APP.

Solo sirve para actualizar BBDDs desde la versión 2.2.1.3

TODO:
    tener en cuenta integridad referencial, claves foraneas, etc...!!!

PROBADO OK:
    actualización a 2.3.0 en:   SQL Server  Oracle  MySQL

"""

import logging


from pylons import config
import datetime

from authkit.authorize.pylons_adaptors import authorize
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And
import sqlalchemy as sa
import sqlalchemy.databases.mssql as mssql
import sqlalchemy.databases.oracle as oracle
import sqlalchemy.databases.mysql as mysql

from endosys.model import meta
from endosys.lib.checks import check_cache_dir
from endosys.lib.misc import *
from endosys.lib.db import nombre_tabla, nueva_columna, existe_columna
from endosys.lib.base import *

class DbupdateController(BaseController):
    @authorize(UserIn(['sysadmin']))
    def index(self):
        """
        """

        response.content_type = "text/html"
        s = '<html><head>'
        #s += '<script type="text/javascript" src="/lib/jquery/js/jquery-1.8.2.js"></script>'
        s += '<script data-main="/web/" type="text/javascript" src="/lib/jquery/require-jquery.js"></script>'

        s += '<style type="text/css">'
        s += 'table {width: 100%;} '
        s += '.valor {width: 100%;} '
        s += '.key_col {width: 30%;} '
        s += '.value_col {width: 70%;} '
        s += '</style>'

        s += '<title>Endosys App - Actualización de base de datos (beta)</title>'
        s += '</head><body>'

        s += '<h1>Actualización de base de datos (beta)</h1>'
        s += '<h2>Notas</h2>'
        s += '<p>'
        s += """
        La actualización automática de la base de datos de Endosys App sólo se puede utilizar
        con la versión <strong>2.2.1.3</strong> o posterior. En versiones anteriores se deberá realizar de forma manual.
        <br>
        """
        s += """
        De momento, sólo se puede utilizar con el motor de base de datos <strong>MS SQL Server 2000, 2005 y 2008.</strong>
        <br>
        """
        s += """
        Este actualizador automático sólo modifica las tablas existentes, añadiendo nuevas columnas o
        modificándolas pero no crea nuevas tablas. Para crear las nuevas tablas debe utilizarse
        previamente la utilidad del servidor <strong>"setup-app"</strong>.
        """
        s += '</p>'

        s += '<h2>Instrucciones de uso</h2>'
        s += '<ol>'
        s += """<li>
        Actualizar Endosys App a la versión deseada, copiando los ficheros en el servidor.
        </li>"""
        s += """<li>
        Crear las nuevas tablas de base de datos mediante la utilidad del servidor "setup-app".
        </li>"""
        s += """<li>
        Actualizar las tablas existentes pulsando el botón <button id="actualizar">Actualizar tablas</button>.
        </li>"""
        s += '</ol>'

        s += '<div>'
        s += '<h3>Salida</h3>'
        s += '<textarea id="output" style="width: 100%" rows=15></textarea>'
        s += '</div>'

        # script jquery para:
        #   evento click del botón para actualizar la BBDD
        s += '<script>'
        s += """
            $(function() {

                $('#actualizar').click(function(e) {

                    //  enviar mediante POST ajax
                    //v = v.join('&');
                    $.ajax({
                        type: 'POST',
                        url: '/dbupdate/actualizar',
                        //data: v,
                        processData: false,
                        //contentType: 'text/plain; charset=UTF-8',
                        //contentType: 'application/x-www-form-urlencoded; charset=UTF-8',
                        success: function(data) {
                            $('#output').val( $('#output').val() + '\\n\\n\\n' + data);
                        },
                        error: function(data) {
                            alert('Ha ocurrido un error');
                        }
                    });

                });

            });
        """
        s += '</script>'

        s += '</body></html>'
        return s

    @authorize(UserIn(['sysadmin']))
    def actualizar(self):
        """
        realiza la actualización de la BBDD.

        SQL Alchemy no tiene opciones de actualización de tablas, asi que se
        tiene que hacer directamente con "ALTER TABLES".

        Esta función se debería mantener "sincronizada" con el model de EndoTools
        Web y con el archivo "MODIFICACIONES BBDD.txt"

        Además debería probarse siempre con SQL Server, Oracle, y otros posibles
        sistemas (MySQL y SQLite).

        Mas info:
         http://docs.sqlalchemy.org/en/latest/core/schema.html#altering-schemas-through-migrations
        """
        self.output_log =   'ACTUALIZANDO BBDD (motor: %s)      ' % meta.engine.name
        self.output_log +=  datetime.datetime.now().strftime('%d-%m-%Y, %H:%M:%S') + '\n'
        self.output_log +=  '================================================================================\n'

        if  not isinstance(meta.engine.dialect, mysql.MySQLDialect) and \
            not isinstance(meta.engine.dialect, mssql.MSSQLDialect) and \
            not isinstance(meta.engine.dialect, oracle.OracleDialect):
            self.output_log +=  'ATENCION!!! El motor de base de datos no es compatible con EndoTools.'
            log.error('motor de bbdd imcompatible.')
        else:
            # 2.3.0
            self.output_log +=  '\nv2.3.0\n'
            self.output_log +=  '--------------------------------------------------------------------------------\n'
            r, out = nueva_columna(meta.Session, meta.engine,'Pacientes', 'deshabilitado', sa.types.Boolean, nullable=True)
            self.output_log += out
            r, out = nueva_columna(meta.Session, meta.engine,'Informes', 'invalido', sa.types.Boolean, nullable=True)
            self.output_log += out

            # 2.3.1
            self.output_log +=  '\nv2.3.1\n'
            self.output_log +=  '--------------------------------------------------------------------------------\n'
            r, out = nueva_columna(meta.Session, meta.engine,'TiposExploracion', 'codigo', sa.types.String(50), nullable=True)
            self.output_log += out

            # 2.3.1.3
            self.output_log +=  '\nv2.3.1.3\n'
            self.output_log +=  '--------------------------------------------------------------------------------\n'
            if self._renombrar_columna('Citas', 'prioridad', 'prioridad_id', sa.types.Integer):
                self._update_prioridad()

            # 2.3.2.3
            self.output_log +=  '\nv2.3.2.3\n'
            self.output_log +=  '--------------------------------------------------------------------------------\n'
            r, out = nueva_columna(meta.Session, meta.engine,'Exploraciones_dicom', 'studyDescription', sa.types.String(64), nullable=True)
            self.output_log += out

            # 2.3.3
            self.output_log +=  '\nv2.3.3\n'
            self.output_log +=  '--------------------------------------------------------------------------------\n'
            r, out = nueva_columna(meta.Session, meta.engine,'Campos', 'script', sa.types.Text, nullable=True)
            self.output_log += out          
            r, out = nueva_columna(meta.Session, meta.engine,'Exploraciones', 'edad_paciente', sa.types.Integer, nullable=True)
            self.output_log += out          
            r, out = nueva_columna(meta.Session, meta.engine,'Capturas', 'comentario', sa.types.Text, nullable=True)
            self.output_log += out          
            r, out = nueva_columna(meta.Session, meta.engine,'Capturas', 'orden', sa.types.Integer, nullable=True)
            self.output_log += out

            # 2.3.3.2
            self.output_log +=  '\nv2.3.3.2\n'
            self.output_log +=  '--------------------------------------------------------------------------------\n'
            r, out = nueva_columna(meta.Session, meta.engine,'Capturas', 'tipo', sa.types.String(8), nullable=True)
            self.output_log += out

            # 2.3.3.4-HUCA
            self.output_log +=  '\nv2.3.3.4-HUCA\n'
            self.output_log +=  '--------------------------------------------------------------------------------\n'
            r, out = nueva_columna(meta.Session, meta.engine,'Worklist', 'placerOrderNumber', sa.types.String(64), nullable=True)
            self.output_log += out

            # 2.4
            self.output_log +=  '\nv2.4\n'
            self.output_log +=  '--------------------------------------------------------------------------------\n'
            r, out = nueva_columna(meta.Session, meta.engine,'Capturas', 'posx', sa.types.Integer, nullable=True)
            self.output_log += out
            r, out = nueva_columna(meta.Session, meta.engine,'Capturas', 'posy', sa.types.Integer, nullable=True)
            self.output_log += out

            # 2.4.2
            self.output_log +=  '\nv2.4.2\n'
            self.output_log +=  '--------------------------------------------------------------------------------\n'
            r, out = nueva_columna(meta.Session, meta.engine,'Citas_ex', 'filler_status_code', sa.types.String(15), nullable=True)
            self.output_log += out

            # 2.4.3
            self.output_log +=  '\nv2.4.3\n'
            self.output_log +=  '--------------------------------------------------------------------------------\n'
            r, out = nueva_columna(meta.Session, meta.engine,'Campos', 'obligatorio', sa.types.Boolean, nullable=True)
            self.output_log += out
            r, out = nueva_columna(meta.Session, meta.engine,'Registro', 'hl7_log_id',  sa.types.Integer, nullable=True)
            self.output_log += out
            # Y se añade una nueva tabla "Hl7_logs", que se crea con el setup-app

            # 2.4.7
            self.output_log +=  '\nv2.4.7\n'
            self.output_log +=  '--------------------------------------------------------------------------------\n'
            #   QUITAR_CITA.SERVICIO_ID
            #   XXX se debería eliminar la columna citas.servicio_id, pero aun no tenemos una función _eliminar_columna()
            r, out = nueva_columna(meta.Session, meta.engine,'Exploraciones', 'servicio_id', sa.types.Integer, sa.ForeignKey('Servicios.id'), nullable=True)
            self.output_log += out
            self._nueva_foreignkey(cons_table='Exploraciones',
                cons_field='servicio_id', ref_table='Servicios', ref_field='id')
            # en una futura version se tendrá que eliminar Exploraciones.centro_id, migrando el valor a Exploraciones.servicio_id

            # 2.4.8.4
            self.output_log +=  '\nv2.4.8.4\n'
            self.output_log +=  '--------------------------------------------------------------------------------\n'
            r, out = nueva_columna(meta.Session, meta.engine,'Informes', 'enviado', sa.types.Boolean, nullable=True)
            self.output_log += out

            # 2.4.8.5
            self.output_log +=  '\nv2.4.8.5\n'
            self.output_log +=  '--------------------------------------------------------------------------------\n'
            self._modificar_columna('Workstations', 'ip', sa.types.String(15), nullable=True) # Nullable False -> True

            # 2.4.9
            self.output_log +=  '\nv2.4.9\n'
            self.output_log +=  '--------------------------------------------------------------------------------\n'
            # columna disponible que indica si una captura ya tiene su archivo disponible en el servidor
            r, out = nueva_columna(meta.Session, meta.engine,'Capturas', 'disponible', sa.types.Boolean, nullable=True)
            self.output_log += out
            r, out = nueva_columna(meta.Session, meta.engine,'Capturas', 'uuid', sa.types.String(32), nullable=True)
            self.output_log += out
            # Columna que relaciona un campo con otro
            #nueva_columna(meta.Session, meta.engine,'Campos', 'campo_rel_id', sa.types.Integer, sa.ForeignKey('Campos.id'), nullable=True)          #Columna para registrar la aseguradora asociada al paciente el dia que se realizó la exploración
            r, out = nueva_columna(meta.Session, meta.engine,'Exploraciones', 'aseguradora_id', sa.types.Integer, sa.ForeignKey('Aseguradoras.id'), nullable=True)
            self.output_log += out
            self._nueva_foreignkey(cons_table='Exploraciones',
                cons_field='aseguradora_id', ref_table='Aseguradoras', ref_field='id')

            r, out = nueva_columna(meta.Session, meta.engine,'Aseguradoras', 'activo', sa.types.Boolean, nullable=True)
            self.output_log += out
            r, out = nueva_columna(meta.Session, meta.engine,'TiposExploracion','duracion', sa.types.Integer, nullable=True, default=0)
            self.output_log += out

            # 2.4.10
            self.output_log +=  '\nv2.4.10\n'
            self.output_log +=  '--------------------------------------------------------------------------------\n'
            r, out = nueva_columna(meta.Session, meta.engine,'Exploraciones','borrado', sa.types.Boolean, default=False, nullable=True)  # Borrado logico
            self.output_log += out
            r, out = nueva_columna(meta.Session, meta.engine,'Exploraciones','borrado_motivo', sa.types.String(200), nullable=True)      # Borrado logico
            self.output_log += out
            r, out = nueva_columna(meta.Session, meta.engine,'Capturas','borrado', sa.types.Boolean, default=False, nullable=True)       # Borrado logico
            self.output_log += out
            r, out = nueva_columna(meta.Session, meta.engine,'Capturas','borrado_motivo', sa.types.String(200), nullable=True)           # Borrado logico
            self.output_log += out
            self._renombrar_columna('Informes', 'invalido', 'borrado', sa.types.Boolean)
            r, out = nueva_columna(meta.Session, meta.engine,'Informes','borrado_motivo', sa.types.String(200), nullable=True)           # Borrado logico
            self.output_log += out
            r, out = nueva_columna(meta.Session, meta.engine,'ValoresMulti','cantidad', sa.types.Integer, nullable=True,default=1)       # #680
            self.output_log += out
            self._update_valor_multi_cantidad() # pone todos los elemento en cantidad =1 cuando son NULL de la tabla valores multi
            self._reasignar_servicios() # usa el servicio_id de la tabla tipos de explo para agregar el registro en la tabla realcion

            # 2.4.10.3
            self.output_log +=  '\nv2.4.10.3\n'
            self.output_log +=  '--------------------------------------------------------------------------------\n'
            r, out = nueva_columna(meta.Session, meta.engine,'Rel_Campos_Formularios', 'campo_rel_id', sa.types.Integer, sa.ForeignKey('Campos.id'), nullable=True)
            self.output_log += out
            self._nueva_foreignkey(cons_table='rel_Campos_Formularios',
                cons_field='campo_rel_id', ref_table='Campos', ref_field='id')

            # 2.4.11.1
            self.output_log += '\n2.4.11.1\n'
            self.output_log += '--------------------------------------------------------------------------------\n'
            r, out = nueva_columna(meta.Session, meta.engine,'Usuarios','activo', sa.types.Boolean, nullable=True, default=True)
            self.output_log += out
            
            nueva_usuarios_tipo, output_log = nueva_columna(meta.Session, meta.engine,'Usuarios','tipo', sa.types.Integer, nullable=True, default=0)
            self.output_log += output_log
            if nueva_usuarios_tipo:
                self._update_valor_tipo_usuario() #Cambiamos el valor del usuario en el caso que existan sysadmin o administrador.
            r, out = nueva_columna(meta.Session, meta.engine,'Informes','medico_id',  sa.types.Integer, nullable=True)
            self.output_log += out
            self.output_log += 'ACTUALIZAR DATOS columna activo y tipo de la tabla usuarios (Valores NULL a 1 y 0)\n'
            meta.Session.execute('update %s set activo = 1 where activo IS NULL' % (nombre_tabla(meta.engine, 'Usuarios')))
            meta.Session.execute('update %s set tipo = 0 where tipo IS NULL' % (nombre_tabla(meta.engine, 'Usuarios')))
            self.output_log += '        Se han actualizado los datos de la columna activo y tipo de la tabla usuarios\n'
            # 2.4.11.2
            self.output_log += '\n2.4.11.2\n'
            self.output_log += '--------------------------------------------------------------------------------\n'
            r, out = nueva_columna(meta.Session, meta.engine,'Elementos', 'orden', sa.types.Integer, nullable=True)
            self.output_log += out

            # 2.4.12
            self.output_log += '\n2.4.12\n'
            self.output_log += '--------------------------------------------------------------------------------\n'
            r, out = nueva_columna(meta.Session, meta.engine,'Busquedas', 'nivel', sa.types.Integer, default=0, nullable=True)
            self.output_log += out
            r, out = nueva_columna(meta.Session, meta.engine,'Busquedas', "username", sa.types.String(255), sa.ForeignKey('users.username'), nullable=True)
            self.output_log += out
            self._nueva_foreignkey(cons_table='Busquedas', cons_field='username',
                ref_table='users', ref_field='username')

            r, out = nueva_columna(meta.Session, meta.engine,'Busquedas', "servicio_id", sa.types.Integer, sa.ForeignKey('Servicios.id'), nullable=True)
            self.output_log += out
            self._nueva_foreignkey(cons_table='Busquedas', cons_field='servicio_id',
                ref_table='Servicios', ref_field='id')

            nueva_busq_com, output_log = nueva_columna(meta.Session, meta.engine,'Busquedas', "comentario", sa.types.Text, nullable=True)
            self.output_log += output_log
            if nueva_busq_com:
                self.output_log += "ACTUALIZAR DATOS columna nivel y propietario a 0 y \"sysadmin\" en la tabla de busquedas.\n"
                meta.Session.execute('update %s set nivel = 0 where nivel IS NULL' % (nombre_tabla(meta.engine, 'Busquedas')))
                meta.Session.execute("update %s set username = 'sysadmin' where username IS NULL" % (nombre_tabla(meta.engine, 'Busquedas')))
            
            nueva_pacientes_idunico, output_log = nueva_columna(meta.Session, meta.engine,'Pacientes', 'idunico', sa.types.String(50), nullable=True)
            self.output_log += output_log
            if nueva_pacientes_idunico:
                self.output_log += "ACTUALIZAR DATOS copiamos \"historia\" a \"idunico\" en la tabla pacientes.\n"
                meta.Session.execute('update %s set idunico = historia where idunico IS NULL' % (nombre_tabla(meta.engine, 'Pacientes')))
                self._modificar_columna('Pacientes', 'historia', sa.types.String(50), nullable=True)
            r, out = nueva_columna(meta.Session, meta.engine,'Registro', 'idunico', sa.types.String(50), nullable=True)
            self.output_log += out
            r, out = nueva_columna(meta.Session, meta.engine,'Registro', 'centro_id', sa.types.Integer, sa.ForeignKey('Centros.id'), nullable=True)
            self.output_log += out

            nueva_registro_nhc_centro, output_log = nueva_columna(meta.Session, meta.engine,'Registro', 'nhc_centro', sa.types.String(50), nullable=True)
            self.output_log += output_log
            if nueva_registro_nhc_centro:
                self._modificar_columna('Registro', 'nhc', sa.types.String(50), nullable=True)

            # 2.4.13
            self.output_log += '\n2.4.13\n'
            self.output_log += '--------------------------------------------------------------------------------\n'
            r, out = nueva_columna(meta.Session, meta.engine,'Workstations','borrado', sa.types.Boolean, default=False, nullable=True)   # Borrado logico
            self.output_log += out
            r, out = nueva_columna(meta.Session, meta.engine,'Workstations','borrado_motivo', sa.types.String(200), nullable=True)       # Borrado logico
            self.output_log += out
            r, out = nueva_columna(meta.Session, meta.engine,'Registro', 'workstation_id', sa.types.Integer, sa.ForeignKey('Workstations.id'), nullable=True)
            self.output_log += out
            self._nueva_foreignkey(cons_table='Registro',
                cons_field='workstation_id', ref_table='Workstations', ref_field='id')

            r, out = nueva_columna(meta.Session, meta.engine,'Usuarios', 'clave', sa.types.String(255), nullable=True)
            self.output_log += out
            r, out = nueva_columna(meta.Session, meta.engine,'Hl7_logs', 'idunico', sa.types.String(50), nullable=True)
            self.output_log += out
            r, out = nueva_columna(meta.Session, meta.engine,'Citas_ex', 'idunico', sa.types.String(50), nullable=True)
            self.output_log += out
            r, out = nueva_columna(meta.Session, meta.engine,'Fusiones', 'idunico_origen', sa.types.String(50), nullable=True)
            self.output_log += out
            r, out = nueva_columna(meta.Session, meta.engine,'Fusiones', 'idunico_destino', sa.types.String(50), nullable=True)
            self.output_log += out

            # 2.4.14
            self.output_log += '\n2.4.14\n'
            self.output_log += '--------------------------------------------------------------------------------\n'
            self._modificar_columna('Informes', 'plantilla', sa.types.String(100), nullable=True)
            nueva_informes_tipo, output_log = nueva_columna(meta.Session, meta.engine,'Informes', 'tipo', sa.types.Integer, default=0, nullable=True)
            self.output_log += output_log
            if nueva_informes_tipo:
                meta.Session.execute('update %s set tipo = 0 where tipo IS NULL' % (nombre_tabla(meta.engine, 'Informes')))
            r, out = nueva_columna(meta.Session, meta.engine,'Informes', 'comentarios', sa.types.Text, nullable=True)
            self.output_log += out
            r, out = nueva_columna(meta.Session, meta.engine,'Hl7_logs', 'canal', sa.types.String(50), nullable=True)
            self.output_log += out
            r, out = nueva_columna(meta.Session, meta.engine,'Hl7_logs', "exploracion_id", sa.types.Integer, sa.ForeignKey('Exploraciones.id'), nullable=True)
            self.output_log += out
            self._nueva_foreignkey(cons_table='Hl7_logs',
                cons_field='exploracion_id', ref_table='Exploraciones', ref_field='id')
            r, out = nueva_columna(meta.Session, meta.engine,'Hl7_logs', "estado_envio", sa.types.Integer, nullable=True)
            self.output_log += out

            # 2.4.16
            self.output_log += '\n2.4.16\n'
            self.output_log += '--------------------------------------------------------------------------------\n'
            r, out = nueva_columna(meta.Session, meta.engine,'Citas', 'aseguradora_id', sa.types.Integer, sa.ForeignKey('Aseguradoras.id'), nullable=True)
            self.output_log += out
            self._nueva_foreignkey(cons_table='Citas',
                                    cons_field='aseguradora_id', ref_table='Aseguradoras', ref_field='id')

            # 2.4.21
            self.output_log += '\n2.4.21\n'
            self.output_log += '--------------------------------------------------------------------------------\n'
            r, out = nueva_columna(meta.Session, meta.engine, 'Campos', "ambito", sa.types.Integer, nullable=True)
            self.output_log += out
            r, out = nueva_columna(meta.Session, meta.engine, 'Elementos', "servicio_id", sa.types.Integer, sa.ForeignKey('Servicios.id'), nullable=True)
            self.output_log += out

            # 2.4.22
            self.output_log += '\n2.4.22\n'
            self.output_log += '--------------------------------------------------------------------------------\n'
            r, out = nueva_columna(meta.Session, meta.engine, 'worklist', "schStationAETitle", sa.types.String(64), nullable=True)
            self.output_log += out
            r, out = nueva_columna(meta.Session, meta.engine, 'worklist', "reqProcedureDesc", sa.types.String(64), nullable=True)
            self.output_log += out
            r, out = nueva_columna(meta.Session, meta.engine, 'worklist', "schProcStepLoc", sa.types.String(64), nullable=True)
            self.output_log += out
            r, out = nueva_columna(meta.Session, meta.engine, 'worklist', "admissionID", sa.types.String(64), nullable=True)
            self.output_log += out
            r, out = nueva_columna(meta.Session, meta.engine, 'worklist', "modality", sa.types.String(4), nullable=True)
            self.output_log += out
            
            # 2.4.23
            self.output_log += '\n2.4.23\n'
            self.output_log += '--------------------------------------------------------------------------------\n'
            r, out = nueva_columna(meta.Session, meta.engine, 'Capturas', "dicom_stored", sa.types.Boolean,nullable=True, default=False)
            self.output_log += out
            r, out = nueva_columna(meta.Session, meta.engine, 'Capturas', "dicom_stgcmt", sa.types.Boolean,nullable=True, default=False)
            self.output_log += out
            r, out = nueva_columna(meta.Session, meta.engine, 'worklist', "schPerfPhysicianName", sa.types.String(64), nullable=True)
            self.output_log += out
            r, out = nueva_columna(meta.Session, meta.engine, 'worklist', "schStationName", sa.types.String(64), nullable=True)
            self.output_log += out
            r, out = nueva_columna(meta.Session, meta.engine, 'worklist', "schStationName", sa.types.String(64), nullable=True)
            self.output_log += out
            r, out = nueva_columna(meta.Session, meta.engine, 'worklist', "reqProcedureID", sa.types.String(64), nullable=True)
            self.output_log += out
            r, out = nueva_columna(meta.Session, meta.engine, 'worklist', "reqProcedurePriority", sa.types.String(64), nullable=True)
            self.output_log += out
            r, out = nueva_columna(meta.Session, meta.engine, 'worklist', "patientLocation", sa.types.String(64), nullable=True)
            self.output_log += out
            r, out = nueva_columna(meta.Session, meta.engine, 'worklist', "admDiagnosisDesc", sa.types.String(64), nullable=True)
            self.output_log += out
            r, out = nueva_columna(meta.Session, meta.engine, 'worklist', "patientWeight", sa.types.String(16), nullable=True)
            self.output_log += out
            r, out = nueva_columna(meta.Session, meta.engine, 'worklist', "source", sa.types.String(128), nullable=True)
            self.output_log += out
            self._modificar_columna('Configuraciones', 'valor', sa.types.Text, nullable=False)       
            r, out = nueva_columna(meta.Session, meta.engine, 'exploraciones', "SeriesInstanceUID", sa.types.String(128), nullable=True)
            self.output_log += out
            r, out = nueva_columna(meta.Session, meta.engine, 'Capturas', "updated_at", sa.types.DateTime,nullable=True)
            self.output_log += out


            # Actualizar la version en la base de datos
            update_version_number_db(meta.Session)

            # -----------------------------
            meta.Session.commit()
            #------------------------------
            
        return self.output_log

    def _nueva_foreignkey(self, cons_table, cons_field, ref_table, ref_field):
        """
        Crea una nueva foreign key a partir del nombre de dos tablas y dos campos. Si la foreign
        key ya existe no ejecuta el sql y imprime un mensaje por pantalla y en el log.
        """
        INITIAL_LOG_MESSAGE = 'NUEVA FOREIGN KEY   %s.%s en referencia a %s.%s\n'
        self.output_log += INITIAL_LOG_MESSAGE % (cons_table, cons_field, ref_table, ref_field)
        # Comprobar si la foreign key existe
        if self._existe_foreignkey(cons_table, cons_field, ref_table, ref_field):
            # Logging
            self.output_log += '        La foreign key ya existe, no se realizará ninguna acción\n'
            log.debug("La foreign key ya existe, no se realizará ninguna acción\n")
            return None

        if isinstance(meta.engine.dialect, mysql.MySQLDialect):
            """
            MySQL Server
            """
            SQL = """
                ALTER TABLE {0} ADD
                FOREIGN KEY ({1}) REFERENCES {2}({3})
            """.replace('\n', ' ').replace('\t', ' ') # Eliminar retorno de carro y tabs

        elif isinstance(meta.engine.dialect, mssql.MSSQLDialect):
            """
            Microsoft SQL Server
            """
            SQL = """
                ALTER TABLE dbo.{0} ADD
                FOREIGN KEY ({1}) REFERENCES dbo.{2}({3})
            """.replace('\n', ' ').replace('\t', ' ') # Eliminar retorno de carro y tabs

        elif isinstance(meta.engine.dialect, oracle.OracleDialect):
            """
            Oracle Server

            En este caso si el nombre de una tabla o columna esta definido en el codigo python
            todo minusculas la query tiene que estar en mayusculas en cualquier otro caso no hace
            falta modificarlo.
            """
            SQL = """
                ALTER TABLE "{0}" ADD
                FOREIGN KEY ({1}) REFERENCES "{2}"({3})
            """.replace('\n', ' ').replace('\t', ' ') # Eliminar retorno de carro y tabs
            if cons_table.islower(): cons_table = cons_table.upper()
            if cons_field.islower(): cons_field = cons_field.upper()
            if ref_table.islower(): ref_table = ref_table.upper()
            if ref_field.islower(): ref_field = ref_field.upper()

        # Formatear SQL
        SQL = SQL.format(cons_table, cons_field, ref_table, ref_field)
        # Ejecutar SQL
        meta.Session.execute(SQL)
        # Logging
        self.output_log += '        La foreign key no existe, se añadirá al esquema\n'
        log.debug("La foreign key no existe, se añadirá al esquema\n")
    
    def _renombrar_columna(self, table_name, column_name, new_column_name, column_type):
        """
        renombrar una columna.
        Si se renombra devuelve True, si no False.
        Si no se renombra porque ya se había renombrado anteriormente, devuelve False.
        """
        self.output_log +=  'RENOMBRAR COLUMNA  %s.%s ---> %s.%s\n' % \
                            (table_name,
                             column_name,
                             table_name,
                             new_column_name
                             )
        log.debug('Renombrar columna: %s, %s, %s' % (table_name, column_name, new_column_name))

        # Comprobar la existencia de las columnas
        existe_old = existe_columna(meta.Session, meta.engine, table_name, column_name)
        existe_new = existe_columna(meta.Session, meta.engine, table_name, new_column_name)

        # si existe la columna con el nombre antiguo y no existe la nueva, renombrar
        log.debug('EXISTE: %s %s', existe_old , existe_new)
        if existe_old and not existe_new:
            log.debug('La columna no ha sido renombrada, se va a renombrar')

            #   ejecutar el ALTER TABLE para renombrar la columna
            if isinstance(meta.engine.dialect, mysql.MySQLDialect):
                #   MySQL
                #       generar la definicion de columna para el motor de bbdd
                schema_generator = meta.engine.dialect.schemagenerator(meta.engine.dialect, meta.Session.connection)
                columna_sql = schema_generator.get_column_specification( sa.Column(new_column_name, column_type) )
                log.debug('SQL: %s' % (columna_sql))
                r = meta.Session.execute('ALTER TABLE %s CHANGE %s %s' % (table_name, column_name, columna_sql))
            elif isinstance(meta.engine.dialect, mssql.MSSQLDialect):
                #   SQL Server
                r = meta.Session.execute("sp_RENAME '%s.%s', '%s' , 'COLUMN'" % (table_name, column_name, new_column_name))
            elif isinstance(meta.engine.dialect, oracle.OracleDialect):
                #   Oracle
                r = meta.Session.execute('ALTER TABLE "%s" RENAME COLUMN %s TO %s' % (table_name, column_name, new_column_name))
            self.output_log +=  '           Se ha renombrado la columna'
            resultado = True
        elif not existe_old and existe_new:
            self.output_log +=  '       La columna ya ha sido renombrada. no se realiza ninguna acción'
            log.debug('La columna ya ha sido renombrada. No se realizara ningun cambio')
            resultado = False
        elif existe_old and existe_new:
            self.output_log +=  '       ATENCION!!! EXISTEN LAS DOS COLUMNAS. Se debería revisar la base de datos. No se realiza ninguna acción'
            log.warning('EXISTEN LAS DOS COLUMNAS. No se realizara ningun cambio')
            resultado = False
        elif not existe_old and not existe_new:
            self.output_log +=  '       ATENCION!!! NO EXISTE LA COLUMNA, Y NO HA SIDO RENOMBRADA PREVIAMENTE.  Se debería revisar la base de datos. no se realiza ninguna acción'
            log.warning('NO EXISTE NINGUNA DE LAS COLUMNAS. No se realizara ningun cambio')
            resultado = False
        self.output_log +=  '\n'
        return resultado

    def _modificar_columna(self, table_name, column_name, column_type, *args, **kwargs):
        """
        modificar una columna.
        ¿?De momento solo sirve para cambiar el NULLABLE/ALLOW NULLS
        ////////////Si se renombra devuelve True, si no False.
        ////////////Si no se renombra porque ya se había renombrado anteriormente, devuelve False.
        """
        self.output_log +=  'MODIFICAR COLUMNA  %s.%s ( %s %s %s )\n' % \
                            (table_name,
                             column_name,
                             meta.engine.dialect.type_descriptor(column_type).get_col_spec(),
                             args,
                             kwargs
                             )
        log.debug('Modificar columna: %s, %s, %s' % (table_name, column_name, column_type))

        #   ejecutar el ALTER TABLE para renombrar la columna
        if isinstance(meta.engine.dialect, mysql.MySQLDialect):
            #   MySQL
            #       generar la definicion de columna para el motor de bbdd
            schema_generator = meta.engine.dialect.schemagenerator(meta.engine.dialect, meta.Session.connection)
            columna_sql = schema_generator.get_column_specification( sa.Column(column_name, column_type, *args, **kwargs) )
            log.debug('SQL: %s' % (columna_sql))
            r = meta.Session.execute('ALTER TABLE %s MODIFY %s' % (table_name, columna_sql))
        elif isinstance(meta.engine.dialect, mssql.MSSQLDialect):
            #   SQL Server (PROBADO OK)
            #       generar la definicion de columna para el motor de bbdd
            schema_generator = meta.engine.dialect.schemagenerator(meta.engine.dialect, meta.Session.connection)
            columna_sql = schema_generator.get_column_specification( sa.Column(column_name, column_type, *args, **kwargs) )
            log.debug('SQL: %s' % (columna_sql))
            r = meta.Session.execute('ALTER TABLE %s ALTER COLUMN %s' % (table_name, columna_sql))
        elif isinstance(meta.engine.dialect, oracle.OracleDialect):
            #   Oracle
            schema_generator = meta.engine.dialect.schemagenerator(meta.engine.dialect, meta.Session.connection)
            columna_sql = schema_generator.get_column_specification( sa.Column(column_name, column_type, *args, **kwargs) )
            log.debug('SQL: %s' % (columna_sql))
            r = meta.Session.execute("""ALTER TABLE "%s" MODIFY %s""" % (table_name, columna_sql))
        self.output_log +=  '           Se ha modificado la columna'
        resultado = True

        self.output_log +=  '\n'
        return resultado

    def _existe_foreignkey(self, cons_table, cons_field, ref_table, ref_field):
        """
        Esta funcion comprueba si una foreign key ya existe a partir del nombre
        de dos tablas y dos columnas.
        """
        schema_name = meta.engine.dialect.get_default_schema_name(meta.Session.connection())
        #Determinar que base de datos se esta usando
        if isinstance(meta.engine.dialect, mysql.MySQLDialect):
            """
            MySQL Server

            En mysql server la informacion de las foreign keys se almacena en la tabla
            KEY_COLUMN_USAGE del esquema information_schema.

            ATENCION: Esta tabla es com un para todos los esquemas, por lo tanto hay que filtrar
            por el nombre del esquema que se esta utilizando.
            """
            SQL = """
                SELECT
                    COUNT(*) AS result

                FROM information_schema.KEY_COLUMN_USAGE

                WHERE CONSTRAINT_NAME != 'PRIMARY'
                    AND TABLE_NAME = '{cons_table}'
                    AND COLUMN_NAME = '{cons_field}'
                    AND REFERENCED_TABLE_NAME = '{ref_table}'
                    AND REFERENCED_COLUMN_NAME = '{ref_field}'
                    AND CONSTRAINT_SCHEMA = '{schema_name}';
            """.replace('\n', ' ').replace('\t', ' ') # Eliminar retorno de carro y tabs

        elif isinstance(meta.engine.dialect, mssql.MSSQLDialect):
            """
            Microsoft SQL Server

            La informacion sobre las foreign keys se gurdan en la tabla foreign_key_columns del
            esquema sys.

            ATENCION: No esta probado en SQL Server 2005 aunque en la documentacion aparacen como
            compatibles las funciones OBJECT_NAME y COL_NAME.

            OBJECT_NAME: https://msdn.microsoft.com/es-es/library/ms186301(v=sql.90).aspx
            COL_NAME: https://technet.microsoft.com/es-es/library/ms174974(v=sql.90).aspx
            """
            SQL = """
                SELECT
                    COUNT(*) AS result

                FROM sys.foreign_key_columns

                WHERE OBJECT_NAME(parent_object_id) = '{cons_table}'
                    AND COL_NAME(parent_object_id, parent_column_id) = '{cons_field}'
                    AND OBJECT_NAME(referenced_object_id) = '{ref_table}'
                    AND COL_NAME(referenced_object_id, referenced_column_id) = '{ref_field}';
            """.replace('\n', ' ').replace('\t', ' ') # Eliminar retorno de carro y tabs

        elif isinstance(meta.engine.dialect, oracle.OracleDialect):
            """
            Oracle Server

            La informacion sobre las foreign keys se guarda en las tablas user_cons_columns y
            all_constraints.

            ATENCION: si el nombre de una tabla o columna es todo minusculas lo espera en
            mayusculas en cualquier otro caso no hace falta modificarlo.
            """
            if cons_table.islower(): cons_table = cons_table.upper()
            if cons_field.islower(): cons_field = cons_field.upper()
            if ref_table.islower(): ref_table = ref_table.upper()
            if ref_field.islower(): ref_field = ref_field.upper()
            SQL = """
                SELECT COUNT(*) AS result

                FROM user_cons_columns a
                    INNER JOIN all_constraints b
                        ON a.CONSTRAINT_NAME = b.CONSTRAINT_NAME
                    INNER JOIN user_cons_columns c
                        ON b.R_CONSTRAINT_NAME = c.CONSTRAINT_NAME

                WHERE a.TABLE_NAME = '{cons_table}'
                    AND a.COLUMN_NAME = '{cons_field}'
                    AND c.TABLE_NAME = '{ref_table}'
                    AND c.COLUMN_NAME = '{ref_field}'
                    AND b.CONSTRAINT_TYPE = 'R'
            """.replace('\n', ' ').replace('\t', ' ') # Eliminar retorno de carro y tabs

        # Formatear la cadena de SQL con los parametros de la función
        SQL = SQL.format(cons_table=cons_table, cons_field=cons_field, ref_table=ref_table,
            ref_field=ref_field, schema_name=schema_name)
        # Ejecutar SQL
        results = meta.Session.execute(SQL)
        # Determinar si existe la foreign key en funcion de si se devuelve algun resultado
        return (iter(results).next()['result'] > 0)

    def _update_prioridad(self):
        """

        """
        from endosys.model import Prioridad
        self.output_log +=  'ACTUALIZAR DATOS   columna prioridad_id de la tabla Citas\n'
        #resultados = meta.Session.execute('select prioridad_id from "Citas" group by prioridad_id')
        resultados = meta.Session.execute('select prioridad_id from %s group by prioridad_id' % nombre_tabla(meta.engine, 'Citas'))

        resultados = resultados.fetchall()

        for r in resultados:
            if r['prioridad_id']:   #los que no sean null ni vacios
                prioridad_id = r['prioridad_id']
                nombre = None
                nivel = None
                #1 - Normal, 2 - Preferente, 3 - Urgente
                if prioridad_id == 1:
                    nombre = "Normal"
                    nivel = 1
                elif prioridad_id == 2:
                    nombre = "Preferente"
                    nivel = 2
                elif prioridad_id == 3:
                    nombre = "Urgente"
                    nivel = 3
                else:
                    nombre = str(prioridad_id)
                    nivel = 1

                e = meta.Session.execute('SELECT COUNT(*) AS result FROM %s WHERE codigo = \'%s\'' % (nombre_tabla(meta.engine, 'Prioridades'), str(prioridad_id)))
                existe = (iter(e).next()['result'] > 0)

                if not existe:
                    prioridad = Prioridad()
                    prioridad.codigo = str(prioridad_id)
                    prioridad.nombre = nombre
                    prioridad.nivel = str(nivel)
                    meta.Session.save(prioridad)
                    meta.Session.commit()
                    self.output_log +=  '               Se ha creado la Prioridad "%s"\n' % nombre



        meta.Session.execute('update %s set prioridad_id = (select id from %s where codigo = prioridad_id)' % (nombre_tabla(meta.engine, 'Citas'), nombre_tabla(meta.engine, 'Prioridades')))
        self.output_log +=  '           Se han actualizado los datos de la columna prioridad_id de la tabla Citas\n'

    def _update_valor_multi_cantidad(self):
        self.output_log +=  'ACTUALIZAR DATOS columna cantidad de la tabla ValoresMulti (Valores NULL a 1)\n'

        meta.Session.execute('update %s set cantidad = 1 where cantidad IS NULL' % (nombre_tabla(meta.engine, 'ValoresMulti')))
        self.output_log +=  '       Se han actualizado los datos de la columna cantidad de la tabla ValoresMulti\n'

    def _update_valor_tipo_usuario(self):
        '''
        Añade los usuarios de todos los medicos que no tengan usuario. Buscamos valores sysadmin/admin para asignarles
        el tipo 1.
        '''
        from endosys.model import Usuario, Medico

        self.output_log +=  'AÑADIR medicos a la tabla Usuarios si no existen\n'
        #import pdb; pdb.set_trace()
        #usuarios = [x.username for x in meta.Session.query(Usuario).all()]
        usuarios = [x.username for x in meta.Session.execute("SELECT username from %s" % (nombre_tabla(meta.engine, "Usuarios")))]
        medicos = meta.Session.query(Medico).filter(~Medico.username.in_(usuarios)).all()
        for medico in medicos:
            username = medico.username
            self.output_log += '        Se ha creado el usuario %s en la tabla Usuarios\n' % username
            usuario = Usuario()
            usuario.username = username
            usuario.ldap = False
            usuario.activo = True
            usuario.tipo = 0
            meta.Session.save(usuario)
            #meta.Session.commit()

        self.output_log +=  'ACTUALIZAR DATOS columna tipo de la tabla Usuarios (Usuario sysadmin/admin a 1)\n'

        meta.Session.execute("update %s set tipo = 1 where username = 'sysadmin' OR username = 'admin'" % (nombre_tabla(meta.engine, 'Usuarios')))
        for usuario in ["admin", "sysadmin"]:
            self.output_log += '        Se ha cambiado el tipo=1 al usuario %s\n' % usuario

        """
        administradores = meta.Session.query(Usuario).filter(Usuario.username.in_(['sysadmin', 'admin'])).all()
        for usuario in administradores:
            if usuario.tipo == 0:
                self.output_log += '        Se ha cambiado el tipo al usuario %s\n' % usuario.username
                usuario.tipo = 1
                meta.Session.update(usuario)
                #meta.Session.commit()
        """

    def _reasignar_servicios(self):
        ''' El servicio que estaba guardado en tiposExploracion.servicio_id para a ser un item de rel_Serv_tiposExpl
            Si No hay entonces a esa exploración se le agregan todos los servicios
        '''

        from endosys.model import Servicio
        from endosys.model.tiposExploracion import TipoExploracion,Rel_Servicios_TiposExploracion

        self.output_log +=  'ACTUALIZAR DATOS Crear relaciones rel_serv_tipoExpl según datos existentes en columna tiposExploracion.servicio_id \n'

        # XXX verificar si ya existen datos en Rel_servicios_tiposExploracion
        rel_ser_te_all  = meta.Session.query(Rel_Servicios_TiposExploracion).all()
        if len(rel_ser_te_all)==0:

            servicios_all = meta.Session.query(Servicio).all()
            tipos_expl_all = meta.Session.query(TipoExploracion).all()

            for tipo_expl in tipos_expl_all:
                if tipo_expl.servicio_id is None:
                    #asignar todos los servicios a esa exploracion
                    for ser in servicios_all:
                        #asingar 1 solo que es el que estaba en servicio_id
                        rel_ser_te = Rel_Servicios_TiposExploracion()
                        rel_ser_te.servicio_id = ser.id
                        rel_ser_te.tipoExploracion_id = tipo_expl.id
                        meta.Session.save(rel_ser_te)

                else:
                    #asingar 1 solo que es el que estaba en servicio_id
                    rel_ser_te = Rel_Servicios_TiposExploracion()
                    rel_ser_te.servicio_id = tipo_expl.servicio_id
                    rel_ser_te.tipoExploracion_id = tipo_expl.id
                    meta.Session.save(rel_ser_te)

            self.output_log +=  '       Se han creado las relaciones \n'

        else:
            self.output_log +=  '       NO se han crearon las realaciones porque la tabla rel_Serv_tipoExpl ya tiene datos \n'