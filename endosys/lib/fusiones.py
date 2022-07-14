import datetime
import logging
from xml.etree.ElementTree import Element, SubElement, tostring
from endosys.model import meta
from endosys.model.fusiones import Fusion
from endosys.model.pacientes import Paciente, Rel_Pacientes_Centros
from endosys.model.citas import Cita
from endosys.model.exploraciones import Exploracion
from endosys.model.centros import get_centro_id
from sqlalchemy.sql import and_, or_

from endosys.lib.genericREST import *

from authkit.authorize.pylons_adaptors import authorize
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And
from endosys.lib.usuarios.seguridad import roles
from pylons import config


import time
from datetime import date
import pacientes
import endosys.lib.registro as registro
import endosys.lib.hl7_wrapper

# Modo 0 de fusión (backward compatibility) - Se trata del modo existente antes
# de la versión 2.4.17. Se mantiene de momento para no "romper" nada, pero es
# posible que ya ni siquiera funcione... se tendrá que revisar.
def FusionarPacientes(paciente_origen, id_unico_origen, paciente_destino, hl7Process = None):
	"""
	Cuando se entra en esta función, el de destino ya existe y se ha actualizado
	con los datos de PID. Por lo tanto, solo falta ver si el origen tenía citas y expls
	y pasarselas al destino, y luego eliminarlo.
	A no ser que fueran el mismo, en ese caso no se hace nada.
	"""
	day_insert = datetime.datetime.today().date()
	hour_insert = datetime.datetime.today()
	#historia_origen
	# puede ocurrir que el origen y destino sean el mismo si se está identificando por CIP (NUHSA) y
	# se está usando esta función de Fusión para Cambios de NHC. En esos casos NO hay que eliminar el
	# paciente origen!!!
	# XXX	lo ideal sería procesar de forma distinta el Cambio de NHC, mas combiar como una simple
	# 		modificación.

	if paciente_origen and (paciente_origen != paciente_destino):

		# SI existe el paciente origen
		#   cambiar las citas y exploraciones del paciente origen al paciente destino
		#   eliminar el paciente origen

		# mirar si el paciente origen tiene citas
		q = meta.Session.query(Cita).filter(Cita.paciente_id == paciente_origen.id)
		# si tiene citas se le asignan al paciente destino
		if q.count() > 0:
			citas = q.all()
			for cita in citas:
				cita.paciente_id = paciente_destino.id
				meta.Session.update(cita)

		# mirar si el paciente origen tiene exploraciones
		q_exp = meta.Session.query(Exploracion).filter(Exploracion.paciente_id == paciente_origen.id)
		# si tiene exploraciones se le asignan al paciente destino
		if q_exp.count() > 0:
			exploraciones = q_exp.all()
			for exploracion in exploraciones:
				exploracion.paciente_id = paciente_destino.id
				meta.Session.update(exploracion)
			meta.Session.commit()# XXX	se hace ya un commit aqui porque he detectado que en
							#		ocasiones (no se si siempre) haciendo solo el commit
							#	   del final, despues del delete, da error porque si ha
							#	   intentado reasignar expls a otro paciente intenta
							#	   asignar paciente_id = NULL...

		#copiar paciente origen porque luego se eliminara
		params = {}

		params["centros"] = []
		for centro in paciente_origen.centros:
			params["centros"].append({'centro_id': centro.centro_id, 'nhc': centro.nhc})

		for campo in paciente_origen.c.keys():
			params[campo] = getattr(paciente_origen, campo)
		paciente_mgr = record(**params)


		# eliminamos el paciente origen
		for centro in paciente_origen.centros:
			meta.Session.delete(centro)
		meta.Session.delete(paciente_origen)
		meta.Session.commit()

		#crear registro en la tabla registro
		if hl7Process:
			registro.nuevo_registro_paciente("sysadmin", hl7Process.ipaddress, paciente_destino, registro.eventos.fusionar,
					registro.res.paciente, 'Datos', paciente_mgr, paciente_destino, hl7Process.id_hl7_log)

	# crear el registro en la tabla fusiones
	new_fusion = Fusion()
	#new_fusion.nhc_origen =		historia_origen
	#new_fusion.nhc_destino =	paciente_destino.historia
	new_fusion.idunico_origen =		id_unico_origen
	new_fusion.idunico_destino =	paciente_destino.idunico
	new_fusion.id_origen =		paciente_origen.id if paciente_origen else None
	new_fusion.id_destino =		paciente_destino.id
	#new_fusion.cip_origen = 	cip_origen
	#new_fusion.cip_destino = 	paciente_destino.CIP
	new_fusion.day_insert =		day_insert
	new_fusion.hour_insert =	hour_insert
	meta.Session.save(new_fusion)
	meta.Session.commit()

    
# Modo 1 - Por IDUNICO. En principio es el que sustituirá al Modo 0.
def FusionarPacientesM1():
    raise Exception("No implementado")
    

# Modo 2 - NHC + CENTRO - requerido para algunos casos multicentro.
def FusionarPacientesM2(codigo_centro, nhc_origen, nhc_destino, idunico_origen, idunico_destino, pid):
    """
    codigo_centro   El código del centro en el que se lleva a cabo la fusión
    nhc_origen      El NHC que desaparecerá
    nhc_destino     El NHC que se va a mantener
    idunico_origen  El IDUNICO del paciente con el NHC que desaparecerá
    idunico_destino El IDUNICO del paciente con el NHC que se va a mantener
    pid             El segmento PID (tipo hl7.Segment), usado si se tiene que
                    crear el paciente destino.
    
    Realiza la fusión de NHCs sólo a nivel de centro.
    Llamada desde lib.hl7.receiving.
    
    También se indican los IDUNICOs, y por lo tanto se debe mantener la
    consistencia de los datos, comprobando que si ya existían registros en la
    BBDD, los IDUNICOs coincidan con los indicados.
    
    Si no existe el NHC de origen devuelve False, pues no hay fusión a realizar.
    Si se termina la fusión, devuelve True (se elimina el NHC origen y queda
    el NHC destino).
    
    1. comprobar si existe el nhc origen en el centro. Si no, terminar.
    
    2. existe, validar que coincida el idunico, si no lanzar un fallo.
    
    3. comprobar si existe el nhc destino en el centro.
    
    4. Si NO existe:
       A. comprobar si existe algún paciente con el IDUNICO destino.
       B. En caso afirmativo, si no tiene NHC para el centro, usar este
          paciente, pero si tiene NHC no coincidirá con el indicado como NHC
          destino, y por lo tanto lanzar un error de consistencia de datos.
       C. En caso negativo, hacer un INSERT de un nuevo paciente con el IDUNICO
          indicado.
       D. Asignar el NHC indicado al paciente encontrado o insertado.
    
    5. Si SÍ existe, validar que coincida el idunico, si no lanzar un fallo.
        
    6. Mover todas las exploraciones y citas que tenga el paciente con el nhc
       origen, realizadas/citadas para este centro, al paciente con el nhc
       destino.
    7. El paciente con el nhc origen ya no debería tener exploraciones ni citas
       para este centro. Se elimina el nhc origen.

    """
    centro_id = get_centro_id(codigo=codigo_centro)
    if centro_id is None:
        raise Exception("FusionarPacientesM2(): No existe el centro con el codigo '%s'" % codigo_centro)
    
    # Obtener el Paciente con el NHC origen indicado, para este Centro.
    q = meta.Session.query(Rel_Pacientes_Centros).filter( and_(Rel_Pacientes_Centros.nhc == nhc_origen, Rel_Pacientes_Centros.centro_id == centro_id) )
    
    # No existe el NHC origen para este Centro, terminar.
    if q.count() == 0:
        return False

    rel_paciente_centro_origen = q.one() # (debería devolver sólo uno)
    paciente_id_origen = rel_paciente_centro_origen.paciente_id

    # Comprobar la consistencia de datos, el idunico del mensaje y de la BBDD deben coincidir
    if idunico_origen != rel_paciente_centro_origen.paciente.idunico:
        raise Exception("FusionarPacientesM2(): Problema en la consistencia de datos. El id. unico indicado ('%s') no coincide con el ya existente en la BBDD de EndoTools Web ('%s')" % (idunico_origen, rel_paciente_centro_origen.paciente.idunico))
    
    # Obtener el Paciente con el NHC destino indicado, para este Centro.
    q = meta.Session.query(Rel_Pacientes_Centros).filter( and_(Rel_Pacientes_Centros.nhc == nhc_destino, Rel_Pacientes_Centros.centro_id == centro_id) )
    

    # No existe el NHC destino para este Centro. Por lo tanto, basta con hacer
    # un UPDATE del de origen y terminar.
    ##if q.count() == 0:
    ##    # Cambiar el NHC origen por el NHC destino
    ##    rel_paciente_centro_origen.nhc = nhc_destino
    ##    Session.update(rel_paciente_centro_origen)
    ##    Session.commit()
    ##    return True
    
    # No existe el NHC destino para este Centro. Por lo tanto, localizar si
    # existe un paciente con el idunico, para asignarle el NHC, y si no insertar
    # uno nuevo.
    if q.count() == 0:

        paciente_destino = None
        
        # Comprobar si existe algún paciente con el IDUNICO destino.
        q = meta.Session.query(Paciente).filter(Paciente.idunico == idunico_destino)

        if q.count() > 0:
            # En caso afirmativo, asegurarse que no tenga ningún NHC para este
            # centro, pues no coincidirá con el indicado en el mensaje, y por lo
            # tanto se deberá lanzar un error de consistencia de datos.
            paciente_destino = q.one()
            q = meta.Session.query(Rel_Pacientes_Centros).filter( and_(Rel_Pacientes_Centros.paciente_id == paciente_destino.id, Rel_Pacientes_Centros.centro_id == centro_id) )
            if q.count() > 0:
                raise Exception("FusionarPacientesM2(): Problema en la consistencia de datos. Ya existe un paciente en la BBDD de EndoTools Web con el IDUNICO '%s' pero con un NHC distinto al indicado ('%s')" % (idunico_destino, nhc_destino))

        else:
            # En caso negativo, hacer un INSERT de un nuevo paciente con el
            # IDUNICO indicado.
            paciente_destino = Paciente()
            endosys.lib.hl7_wrapper.paciente_from_PID(paciente_destino, pid)
            paciente_destino.idunico = idunico_destino # se supone que ya estaba en el segmento PID, pero así queda claro.
            meta.Session.save(paciente_destino)
            meta.Session.flush()
            
        # Asignar el NHC indicado al paciente encontrado o insertado.            
        rel_paciente_centro_destino = Rel_Pacientes_Centros()
        rel_paciente_centro_destino.paciente_id = paciente_destino.id
        rel_paciente_centro_destino.centro_id = centro_id
        rel_paciente_centro_destino.nhc = nhc_destino
        meta.Session.save(rel_paciente_centro_destino)
    else:

        # Sí que existe el NHC destino para este Centro.
        rel_paciente_centro_destino = q.one() # (debería devolver sólo uno)

        # Comprobar la consistencia de datos, el idunico del mensaje y de la BBDD deben coincidir
        if idunico_destino != rel_paciente_centro_destino.paciente.idunico:
            raise Exception("FusionarPacientesM2(): Problema en la consistencia de datos. El id. unico indicado ('%s') no coincide con el ya existente en la BBDD de EndoTools Web ('%s')" % (idunico_destino, rel_paciente_centro_destino.paciente.idunico))

    paciente_id_destino = rel_paciente_centro_destino.paciente_id

    # Mover las Citas y Exploraciones del paciente origen al destino, pero
    # sólo las correspondientes a este Centro.
    # Las de otros centros dejarlas asignadas al paciente origen, pues son de
    # otro NHC distinto.
    
    # Mover las Citas según corresponda
    q = meta.Session.query(Cita).filter(Cita.paciente_id == paciente_id_origen)
    if q.count() > 0:
        for cita in q.all():
            if cita.agenda.servicio.centro_id == centro_id:
                cita.paciente_id = paciente_id_destino
                meta.Session.update(cita)
                # TODO: añadir un Registro por cada movimiento?

    # NOTA: En citas_ex pueden haber quedado datos "incorrectos", ya que se
    # registra también el NHC tal cual viene del SIU o del ORM.

    # Mover las Exploraciones según corresponda
    q = meta.Session.query(Exploracion).filter(Exploracion.paciente_id == paciente_id_origen)
    if q.count() > 0:
        for exploracion in q.all():
            if exploracion.servicio.centro_id == centro_id:
                exploracion.paciente_id = paciente_id_destino
                meta.Session.update(exploracion)
                # TODO: añadir un Registro por cada movimiento?

    meta.Session.commit()    # XXX lo ideal sería DESPUÉS del Delete, pero puede dar
                        # problemas... ver comentarios en FusionarPacientes()

    # Por último, eliminar el NHC origen del Paciente
    meta.Session.delete(rel_paciente_centro_origen)
    meta.Session.commit()
    
    # TODO: En este punto podría ser que el paciente ya no tenga ningún NHC
    # más de ningún otro centro, y por lo tanto no debería tener ninguna cita o
    # exploración... este paciente estaría "huérfano" y se podría eliminar.
		
    # TODO: Añadir la fusión al Registro
    """
    registro.nuevo_registro_paciente(
        "sysadmin",
        hl7Process.ipaddress,
        paciente_destino,
        registro.eventos.fusionar,
        registro.res.paciente,
        'Datos',
        paciente_mgr,
        paciente_destino,
        hl7Process.id_hl7_log
    )
    """

    # TODO: Añadir una fila en Fusiones
    """
	fusion = Fusion()
	fusion.idunico_origen =     id_unico_origen
	fusion.idunico_destino =    paciente_destino.idunico
	fusion.id_origen =		    paciente_origen.id if paciente_origen else None
	fusion.id_destino =		    paciente_destino.id
	fusion.day_insert =		    day_insert
	fusion.hour_insert =	    hour_insert
	Session.save(fusion)
	Session.commit()
    """