/*
objetos de acceso REST
*/

Endosys.opciones_config =		Endosys.REST.make('/rest/opcionesConfig');

Endosys.plantillas = $.extend(Endosys.REST.make('/rest/plantillas'), {
	obtener: function(tm, exploracion_id) {
		return Endosys.plantillas.index(tm, {'exploracion_id': exploracion_id})
	}
});

Endosys.usuarios = $.extend(	Endosys.REST.make('/rest/usuarios'), {
	show: function(tm, id, params) {
		//	sobreescribir el show().
		//	quitar el formato .json en el show, este controller funciona asi,
		//	ya que el id del usuario puede tener puntos
		var rest_cfg = { jquery: true, 'resource': '/rest/usuarios', format: null };
		return Endosys.REST.show(tm, rest_cfg, id, null, params);
	}
	
});

Endosys.motivos_cancelacion =	Endosys.REST.make('/rest/motivosCancelacion');

Endosys.camposFijos =			Endosys.REST.make('/rest/camposFijos');

Endosys.permisos =			Endosys.REST.make('/rest/permisos');

Endosys.informes =			Endosys.REST.make('/rest/informes');

Endosys.centros =				Endosys.REST.make('/rest/centros');

Endosys.pacientes =			Endosys.REST.make('/rest/pacientes');

Endosys.agendas =				Endosys.REST.make('/rest/agendas');

Endosys.servicios =			Endosys.REST.make('/rest/servicios');

Endosys.motivosCancelacion =	Endosys.REST.make('/rest/motivosCancelacion');

Endosys.prioridades =			Endosys.REST.make('/rest/prioridades');

Endosys.grupos_campos =		Endosys.REST.make('/rest/gruposCampos');

Endosys.medicos =				Endosys.REST.make('/rest/medicos');

Endosys.salas =				Endosys.REST.make('/rest/salas');

Endosys.exploraciones =		Endosys.REST.make('/rest/exploraciones');

Endosys.citas =				Endosys.REST.make('/rest/citas');

Endosys.imagenes =			Endosys.REST.make('/rest/capturas');

Endosys.formularios =			Endosys.REST.make('/rest/formularios');

Endosys.campos = $.extend(	Endosys.REST.make('/rest/campos'), {
	TIPO_TEXTO:		1,
	TIPO_SELECCION:	2,
	TIPO_MULTI:		3,
	TIPO_BOOL:		4,
	TIPO_MEMO:		5,
	TIPO_SEPARADOR: 6,
	get_alto_por_defecto: function(tipo) {
		//	alto por defecto (en filas de la tabla) de cada tipo de campo
		if (tipo == Endosys.campos.TIPO_TEXTO) {
			return 1;
		} else if (tipo == Endosys.campos.TIPO_SELECCION) {
			return 1;
		} else if (tipo == Endosys.campos.TIPO_MULTI) {
			return 1;
		} else if (tipo == Endosys.campos.TIPO_BOOL) {
			return 1;
		} else if (tipo == Endosys.campos.TIPO_MEMO) {
			return 1;
		} else if (tipo == Endosys.campos.TIPO_SEPARADOR) {
			return 1;
		}
	}
});

Endosys.tipos_exploracion =	Endosys.REST.make('/rest/tiposExploracion');

Endosys.busqueda_avanzada = $.extend(	Endosys.REST.make('/rest/busquedas'), {
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

Endosys.aseguradoras =		Endosys.REST.make('/rest/aseguradoras');

Endosys.elementos =			Endosys.REST.make('/rest/elementos');

Endosys.predefinidos =		Endosys.REST.make('/rest/predefinidos');

Endosys.agendas_chus =		Endosys.REST.make('/rest/agendas_chus');

Endosys.valores_default =		Endosys.REST.make('/valoresDefault');

Endosys.provincias =			Endosys.REST.make('/rest/provincias');

Endosys.poblaciones =			Endosys.REST.make('/rest/poblaciones');

Endosys.workstations =		Endosys.REST.make('/rest/workstations');

Endosys.tareas =				Endosys.REST.make('/rest/tareas');

Endosys.notificaciones =		Endosys.REST.make('/rest/notificaciones');
