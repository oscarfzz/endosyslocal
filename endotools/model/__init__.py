import logging
log = logging.getLogger(__name__)

import sqlalchemy as sa
from sqlalchemy import orm
from endotools.model import meta

log.debug('SQL Alchemy version %s', sa.__version__)

# tablas
from endotools.model.centros import Centro
from endotools.model.servicios import Servicio
from endotools.model.agendas import Agenda, HorarioAgenda
from endotools.model.medicos import Medico
from endotools.model.salas import Sala
from endotools.model.puestos_cliente import Puesto_cliente
from endotools.model.workstations import Workstation
from endotools.model.aseguradoras import Aseguradora
from endotools.model.pacientes import Paciente, Rel_Pacientes_Centros
from endotools.model.fusiones import Fusion
from endotools.model.gruposCampos import GrupoCampos
from endotools.model.campos import Campo
from endotools.model.formularios import Formulario, Rel_Campos_Formularios, Rel_GruposCampos_Formularios
from endotools.model.tiposExploracion import TipoExploracion
from endotools.model.elementos import Elemento
from endotools.model.motivosCancelacion import MotivoCancelacion
from endotools.model.prioridades import Prioridad
from endotools.model.exploraciones import Exploracion, Rel_Formularios_Exploraciones
from endotools.model.exploraciones_dicom import Exploracion_dicom
from endotools.model.capturas import Captura
from endotools.model.informes import Informe
from endotools.model.valores import ValorTexto, ValorSelec, ValorMulti, ValorBool
from endotools.model.citas import Cita
from endotools.model.citas_ex import Cita_ex
from endotools.model.textosPredefinidos import TextoPredefinido
from endotools.model.busquedas import Busqueda
from endotools.model.worklist import Work
from endotools.model.usuarios import Usuario
from endotools.model.map_Prest_TiposExpl import Map_Prest_TiposExpl
from endotools.model.hl7_logs import Hl7_log
from endotools.model.registro import Registro
from endotools.model.provincias import Provincia
from endotools.model.poblaciones import Poblacion
from endotools.model.tareas import Tarea
from endotools.model.notificaciones import Notificacion
from endotools.model.configuraciones import Configuracion

def init_model(engine):
	"""Call me before using any of the tables or classes in the model."""
	sm = orm.sessionmaker(autoflush=True, transactional=True, bind=engine) #echo_uow=True
	meta.engine = engine
	meta.Session = orm.scoped_session(sm)