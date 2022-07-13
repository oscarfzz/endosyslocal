/*
objetos de acceso REST
*/

Endotools.opciones_config =		Endotools.REST.make('/rest/opcionesConfig');

Endotools.plantillas = $.extend(Endotools.REST.make('/rest/plantillas'), {
	obtener: function(tm, exploracion_id) {
		return Endotools.plantillas.index(tm, {'exploracion_id': exploracion_id})
	}
});

Endotools.usuarios = $.extend(	Endotools.REST.make('/rest/usuarios'), {
	show: function(tm, id, params) {
		//	sobreescribir el show().
		//	quitar el formato .json en el show, este controller funciona asi,
		//	ya que el id del usuario puede tener puntos
		var rest_cfg = { jquery: true, 'resource': '/rest/usuarios', format: null };
		return Endotools.REST.show(tm, rest_cfg, id, null, params);
	}
	
});

Endotools.motivos_cancelacion =	Endotools.REST.make('/rest/motivosCancelacion');

Endotools.camposFijos =			Endotools.REST.make('/rest/camposFijos');

Endotools.permisos =			Endotools.REST.make('/rest/permisos');

Endotools.informes =			Endotools.REST.make('/rest/informes');

Endotools.centros =				Endotools.REST.make('/rest/centros');

Endotools.pacientes =			Endotools.REST.make('/rest/pacientes');

Endotools.agendas =				Endotools.REST.make('/rest/agendas');

Endotools.servicios =			Endotools.REST.make('/rest/servicios');

Endotools.motivosCancelacion =	Endotools.REST.make('/rest/motivosCancelacion');

Endotools.prioridades =			Endotools.REST.make('/rest/prioridades');

Endotools.grupos_campos =		Endotools.REST.make('/rest/gruposCampos');

Endotools.medicos =				Endotools.REST.make('/rest/medicos');

Endotools.salas =				Endotools.REST.make('/rest/salas');

Endotools.exploraciones =		Endotools.REST.make('/rest/exploraciones');

Endotools.citas =				Endotools.REST.make('/rest/citas');

Endotools.imagenes =			Endotools.REST.make('/rest/capturas');

Endotools.formularios =			Endotools.REST.make('/rest/formularios');

Endotools.campos = $.extend(	Endotools.REST.make('/rest/campos'), {
	TIPO_TEXTO:		1,
	TIPO_SELECCION:	2,
	TIPO_MULTI:		3,
	TIPO_BOOL:		4,
	TIPO_MEMO:		5,
	TIPO_SEPARADOR: 6,
	get_alto_por_defecto: function(tipo) {
		//	alto por defecto (en filas de la tabla) de cada tipo de campo
		if (tipo == Endotools.campos.TIPO_TEXTO) {
			return 1;
		} else if (tipo == Endotools.campos.TIPO_SELECCION) {
			return 1;
		} else if (tipo == Endotools.campos.TIPO_MULTI) {
			return 1;
		} else if (tipo == Endotools.campos.TIPO_BOOL) {
			return 1;
		} else if (tipo == Endotools.campos.TIPO_MEMO) {
			return 1;
		} else if (tipo == Endotools.campos.TIPO_SEPARADOR) {
			return 1;
		}
	}
});

Endotools.tipos_exploracion =	Endotools.REST.make('/rest/tiposExploracion');

Endotools.busqueda_avanzada = $.extend(	Endotools.REST.make('/rest/busquedas'), {
	get_operaciones: function( tipo_dato, tipo_control) {

		// Si es undefined, es de tipo_control=0 por defecto
		if (!tipo_control) tipo_control=0;

		var op = [];
		if (tipo_dato == "1" || tipo_dato == "5") {
			//	campo memo y texto
			var op_detalle0 = { id:"NINGUNO", valor: _('Selecciona'), tipo: "-1", logico: "X"	}/*IDIOMAOK*/
			op.push(op_detalle0);
		
			var op_detalle1 = { id:"IGUAL", valor: _('Sea igual'), tipo: "1", logico: "or"	}/*IDIOMAOK*/
			op.push(op_detalle1);
			
			var op_detalle2 = { id:"DIFERENTE", valor: _('Diferente'), tipo: "1", logico: "or"	}/*IDIOMAOK*/
			op.push(op_detalle2);
			
			var op_detalle3 = { id:"IN", valor: _('Contiene'), tipo: "1", logico: "or"	}/*IDIOMAOK*/
			op.push(op_detalle3);
			
		} else if (tipo_dato == "2") {
			//	Campo select	
			var op_detalle0 = { id:"NINGUNO", valor: _('Selecciona'), tipo: "-1", logico: "X"	}/*IDIOMAOK*/
			op.push(op_detalle0);
			
			var op_detalle1 = { id:"IGUAL", valor: _('Sea igual'), tipo: "1", logico: "or"	}/*IDIOMAOK*/
			op.push(op_detalle1);
			
			var op_detalle2 = { id:"DIFERENTE", valor: _('Diferente'), tipo: "1", logico: "or"	}/*IDIOMAOK*/
			op.push(op_detalle2);
			
		} else if (tipo_dato == "4") {
			//	campo si o no
			var op_detalle0 = { id:"NINGUNO", valor: _('Selecciona'), tipo: "-1", logico: "X"	}/*IDIOMAOK*/
			op.push(op_detalle0);
			
			var op_detalle1 = { id:"IGUAL", valor: _('Sea igual'), tipo: "2", logico: ""	}/*IDIOMAOK*/
			op.push(op_detalle1);
			
		} else if (tipo_dato == "7" || tipo_dato == "8") {
			//	Campo numero 7 y fecha 8
			var op_detalle0 = { id:"NINGUNO", valor: _('Selecciona'), tipo: "-1", logico: "X"	}/*IDIOMAOK*/
			op.push(op_detalle0);
			
			var op_detalle1 = { id:"IGUAL", valor: _('Sea igual'), tipo: "1", logico: "or"	}/*IDIOMAOK*/
			op.push(op_detalle1);
			
			var op_detalle2 = { id:"DIFERENTE", valor: _('Diferente'), tipo: "1", logico: "and"	}/*IDIOMAOK*/
			op.push(op_detalle2);

			var op_detalle3 = { id:"MENOR", valor: _('Menor que'), tipo: "2", logico: ""	}/*IDIOMAOK*/
			op.push(op_detalle3);

			var op_detalle4 = { id:"MAYOR", valor: _('Mayor que'), tipo: "2", logico: ""	}/*IDIOMAOK*/
			op.push(op_detalle4);

			var op_detalle5 = { id:"MAYORIGUAL", valor: _('Mayor o igual que'), tipo: "2", logico: ""	}/*IDIOMAOK*/
			op.push(op_detalle5);

			var op_detalle6 = { id:"MENORIGUAL", valor: _('Menor o igual que'), tipo: "2", logico: ""	}/*IDIOMAOK*/
			op.push(op_detalle6);

			var op_detalle7 = { id:"ENTRE", valor: _('Esté entre'), tipo: "3", logico: "and"	}/*IDIOMAOK*/
			op.push(op_detalle7);

			var op_detalle8 = { id:"NOENTRE", valor: _('No esté entre'), tipo: "3", logico: "and"	}/*IDIOMAOK*/
			op.push(op_detalle8);
			
		} else if (tipo_dato == "3") {

			if (parseInt(tipo_control,10)==2){
				//	Campo multi
				var op_detalle0 = { id:"NINGUNO", valor: _('Selecciona'), tipo: "-1", logico: "X"	}/*IDIOMAOK*/
				op.push(op_detalle0);

				var op_detalle1 = { id:"IN", valor: _('Que tenga alguno de (y cumpla las condiciones)'), tipo: "1", logico: "or"	}/*IDIOMAOK*/
				op.push(op_detalle1);

				var op_detalle2 = { id:"EN", valor: _('Que tenga todos de (y cumpla las condiciones)'), tipo: "1", logico: "and"	}/*IDIOMAOK*/
				op.push(op_detalle2);
			}else{
				//	Campo multi
				var op_detalle0 = { id:"NINGUNO", valor: _('Selecciona'), tipo: "-1", logico: "X"	}/*IDIOMAOK*/
				op.push(op_detalle0);
				
				var op_detalle1 = { id:"IN", valor: _('Que tenga alguno de'), tipo: "1", logico: "or"	}/*IDIOMAOK*/
				op.push(op_detalle1);
				
				var op_detalle2 = { id:"EN", valor: _('Que tenga todos de'), tipo: "1", logico: "and"	}/*IDIOMAOK*/
				op.push(op_detalle2);
			}

		}
		
		return op;			
	}
});

Endotools.aseguradoras =		Endotools.REST.make('/rest/aseguradoras');

Endotools.elementos =			Endotools.REST.make('/rest/elementos');

Endotools.predefinidos =		Endotools.REST.make('/rest/predefinidos');

Endotools.agendas_chus =		Endotools.REST.make('/rest/agendas_chus');

Endotools.valores_default =		Endotools.REST.make('/valoresDefault');

Endotools.provincias =			Endotools.REST.make('/rest/provincias');

Endotools.poblaciones =			Endotools.REST.make('/rest/poblaciones');

Endotools.workstations =		Endotools.REST.make('/rest/workstations');

Endotools.tareas =				Endotools.REST.make('/rest/tareas');

Endotools.notificaciones =		Endotools.REST.make('/rest/notificaciones');
