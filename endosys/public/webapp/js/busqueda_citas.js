/*
Solo se utiliza YUI para DataTable.
*/
var busqueda_citas = function() {

	var datatable_results;
	var opcion_deshabilitados;

	return {
	
		cita_id: null,
		datos_cita_seleccionada: {},	
		datatable_results: undefined,
		
		mostrar_para_dialogo: function(callback_fn, capa_destino, filtros) {
				
				busqueda_citas.paciente_id = null;
				TM.content_citas.activate();
				Endosys.statusbar.mostrar_mensaje(_('Cargando citas...'));/*IDIOMAOK*/
				
				var content_html = "content/busqueda_citas.html"+ew_version_param();

				capa_destino.load(content_html, function(data,textStatus) {
					if (textStatus == "success") {
						capa_destino.i18n();
						busqueda_citas.logica_pantalla(callback_fn, true);
						busqueda_citas._buscar(filtros);
					} else {
						alert(_('error al cargar el fichero busqueda_citas.html'));/*IDIOMAOK*/
					}
				});
		},
		
		
		logica_pantalla: function(callback_fn, isDialog) {
			
			var selector1 = ".layout_main_content";
			//var selector2 = ".contenedor2";
			
			if (isDialog) {
				//es un dialogo y cambia los selectores, ya que si no coge los layout de la capa de abajo
				selector1 = "#content_busqueda_citas " + selector1;
			}

			$(selector1).layout({
				defaults: {
					fxName:		"none",
					fxSpeed:	"fast",
					size:		"auto",
					closable:	false,
					resizable:	false,
					slidable:	false,
					initClosed:	false
				},
				west: {
					size:		275
				}
			});
			
			//	crear la tabla de resultados
			var fielddef = [
				{key: 'fecha', label: _('Fecha'), width: 90, resizeable: true, sortable: true},/*IDIOMAOK*/
				{key: 'hora', label: _('Time:Hora'), width: 60,	resizeable: true,	sortable: true},/*IDIOMAOK*/
				{key: 'tipoexploracion', label: _('Abrev:Tipo exploracion'), width: 110, resizeable: true,	sortable: true},/*IDIOMAOK*/
				{key: 'agenda_descr',	label: _('Agenda'),	width: 140,	resizeable: true,	sortable: true},/*IDIOMAOK*/
				{key: 'medico',			label: _('Médico'),	width: "auto",	resizeable: true,	sortable: true},/*IDIOMAOK*/
				{key: 'sala',			label: _('Sala'),		width: "auto",	resizeable: true,	sortable: true},/*IDIOMAOK*/
				{key: 'prioridad',		label: _('Prioridad'),	width: "auto",	resizeable: true,	sortable: true},/*IDIOMAOK*/
				{key: 'observaciones', 	label: _('Observaciones'), width: "auto", resizeable: true, sortable: true},/*IDIOMAOK*/
				
				//{key: 'CIP', label: "test", width: 110, resizeable: true, sortable: true},
				//{key: 'nombre', label: _('Paciente:Nombre'), width: 140, resizeable: true, sortable: true},/*IDIOMAOK*/
				//{key: 'apellido1', label: _('Paciente:html:1er apellido'), width: 140, resizeable: true, sortable: true},/*IDIOMAOK*/
				//{key: 'apellido2', label: _('Paciente:html:2o apellido'), width: 140, resizeable: true, sortable: true}/*IDIOMAOK*/
			];
			
			// Define un custom row formatter para resaltar los deshabilitados
			//var rowFormatter = function(elTr, oRecord) {
				
			//	return true;
			//}; 
			
			var opciones_datatable = {
				initialLoad:	false,
				MSG_EMPTY:		'<em>' + _('No se ha encontrado ninguna cita') + '</em>',/*IDIOMAOK*/
				//formatRow:		rowFormatter,
				height:			"200px",	//	solo para que tenga el scrollbar, luego el alto es dinámico.
				width:			"100%"
			}
			
			busqueda_citas.datatable_results = new YAHOO.widget.ScrollingDataTable(
					"datatable_busqueda_result", fielddef, dummyDataSource,
					opciones_datatable
			);
			datatable_results = busqueda_citas.datatable_results;
			controles.init_YUI_datatable(datatable_results, {m_inferior:45, layoutPaneResizing: $(selector1).layout().panes.center});

			//	evento click en una fila de la tabla
			datatable_results.subscribe("rowClickEvent", function(oArgs) {
				if (!datatable_results.getRecord(oArgs.target)) return;	//	comprobar que la fila tiene record asignado (porque la fila con el mensaje 'no hay resultados' no tiene record y daria error)
				busqueda_citas._seleccionar_row(oArgs.target);
			});
			

			datatable_results.doBeforeLoadData = function (sRequest, oResponse, oPayload) {
				for (var n=0; n < oResponse.results.length; n++) {
					
					if (oResponse.results[n].tipoExploracion) {
						oResponse.results[n].tipoexploracion = oResponse.results[n].tipoExploracion.nombre;
						oResponse.results[n].tipoexploracion_id = oResponse.results[n].tipoExploracion.id;
					} else {
						oResponse.results[n].tipoexploracion = null;
						oResponse.results[n].tipoexploracion_id = null;
					}
						
					if (oResponse.results[n].prioridad)
						oResponse.results[n].prioridad = oResponse.results[n].prioridad.nombre;
					else
						oResponse.results[n].prioridad = null;
						
					if (oResponse.results[n].sala)
						oResponse.results[n].sala =		oResponse.results[n].sala.nombre;
					else
						oResponse.results[n].sala = null;
						
					if (oResponse.results[n].medico)
						oResponse.results[n].medico =	oResponse.results[n].medico.nombre;
					else
						oResponse.results[n].medico = null;
					
					if (oResponse.results[n].agenda){
						oResponse.results[n].agenda_descr = oResponse.results[n].agenda.nombre;
					
					}	
					
				}
				return true;
			};

			//	-----------------------------------
			Endosys.statusbar.mostrar_mensaje(_('Ready'));/*IDIOMAOK*/
			
			if (callback_fn) callback_fn();
			
			//	cuando se muestra la pantalla en un dialogo (desde gestion_agenda\dialogo_paciente.js)
			//	se tiene que actualizar el layout.
			$('.layout_main_content').layout().resizeAll();
		},
		
		cerrar: function() {
				//buscar_pacientes_btn.destroy();
				//nuevo_btn.destroy();
				if (busqueda_citas.datatable_results) {
					busqueda_citas.datatable_results.destroy();
					busqueda_citas.datatable_results = null;
				}				
		},

		_seleccionar_row: function(row) {
				datatable_results.unselectAllRows();
				datatable_results.selectRow(row);
				datatable_results.clearTextSelection();
				busqueda_citas.cita_id = datatable_results.getRecord(row).getData("id");
				busqueda_citas.datos_cita_seleccionada = datatable_results.getRecord(row).getData();
		},

		//	boton buscar
		_buscar: function (filtros){
			var params;
			if (filtros){
				params = filtros;
			}

			for (var p in params) { if (params[p] == '') delete params[p]; }
		
			Endosys.citas.index(TM.content_citas, params, {datatable: busqueda_citas.datatable_results})
			.done(function(results){
				
				busqueda_citas.cita_id = null;
				busqueda_citas.datos_cita_seleccionada = {};

				if ($("#total")) $("#total").html(results.length);
				
				if (results && results.length == 0) {
					//no se ha encontrado ningun paciente
					Endosys.statusbar.mostrar_mensaje(_('No se ha encontrado ninguna cita'));/*IDIOMAOK*/
				} else {
					Endosys.statusbar.mostrar_mensaje(_('Listo'));/*IDIOMAOK*/
				}								
			})
			.fail(function () {
				Endosys.statusbar.mostrar_mensaje(_('Error al cargar las citas'), 1);/*IDIOMAOK*/
			});
		},
	
	}


}();