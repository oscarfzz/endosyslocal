import logging
log = logging.getLogger(__name__)

import sqlalchemy as sa
from sqlalchemy import orm
from endosys.model import meta

log.debug('SQL Alchemy version %s', sa.__version__)

# tablas
from endosys.model.centros import Centro
from endosys.model.servicios import Servicio
from endosys.model.agendas import Agenda, HorarioAgenda
from endosys.model.medicos import Medico
from endosys.model.salas import Sala
from endosys.model.puestos_cliente import Puesto_cliente
from endosys.model.workstations import Workstation
from endosys.model.aseguradoras import Aseguradora
from endosys.model.pacientes import Paciente, Rel_Pacientes_Centros
from endosys.model.fusiones import Fusion
from endosys.model.gruposCampos import GrupoCampos
from endosys.model.campos import Campo
from endosys.model.formularios import Formulario, Rel_Campos_Formularios, Rel_GruposCampos_Formularios
from endosys.model.tiposExploracion import TipoExploracion
from endosys.model.elementos import Elemento
from endosys.model.motivosCancelacion import MotivoCancelacion
from endosys.model.prioridades import Prioridad
from endosys.model.exploraciones import Exploracion, Rel_Formularios_Exploraciones
from endosys.model.exploraciones_dicom import Exploracion_dicom
from endosys.model.capturas import Captura
from endosys.model.informes import Informe
from endosys.model.valores import ValorTexto, ValorSelec, ValorMulti, ValorBool
from endosys.model.citas import Cita
from endosys.model.citas_ex import Cita_ex
from endosys.model.textosPredefinidos import TextoPredefinido
from endosys.model.busquedas import Busqueda
from endosys.model.worklist import Work
from endosys.model.usuarios import Usuario
from endosys.model.map_Prest_TiposExpl import Map_Prest_TiposExpl
from endosys.model.hl7_logs import Hl7_log
from endosys.model.registro import Registro
from endosys.model.provincias import Provincia
from endosys.model.poblaciones import Poblacion
from endosys.model.tareas import Tarea
from endosys.model.notificaciones import Notificacion
from endosys.model.configuraciones import Configuracion

def init_model(engine):
	"""Call me before using any of the tables or classes in the model."""
	sm = orm.sessionmaker(autoflush=True, transactional=True, bind=engine) #echo_uow=True
	meta.engine = engine
	meta.Session = orm.scoped_session(sm)