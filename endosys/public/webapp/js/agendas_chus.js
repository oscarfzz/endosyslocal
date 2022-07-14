var gestion_agendas_chus = function() {

	var datatable_results;

	return {
	
		agenda_id: null,
		servicio_id: null,
		prestacion_id: null,
		tipoExploracion_id: null,
		datatable_results: undefined,
		datatable_prestaciones: undefined,
		
		_seleccionar_row: function(row) {
				datatable_results.unselectAllRows();
				datatable_results.selectRow(row);
				datatable_results.clearTextSelection();
				gestion_agendas_chus.agenda_id = datatable_results.getRecord(row).getData("id");
//				gestion_agendas_chus.servicio_id = datatable_results.getRecord(row).getData("servicio_id");
				gestion_agendas_chus.servicio_id = datatable_results.getRecord(row).getData("codigo_servicio");
				//	mostrar las prestaciones de la agenda
				//Endosys.agendas_chus.obtener_prestaciones(TM.content_agendas_chus.detalles, null, gestion_agendas_chus.agenda_id, datatable_prestaciones);
				Endosys.statusbar.mostrar_mensaje("Obteniendo las prestaciones...");
				Endosys.agendas_chus.show(TM.content_agendas_chus.detalles, gestion_agendas_chus.agenda_id)
				.done(function(agenda_chus) {
					datatable_prestaciones.onDataReturnInitializeTable(null, { results: agenda_chus.prestaciones });
				})
				.fail(function() {
					datatable_prestaciones.getRecordSet().reset();
					datatable_prestaciones.render();
					Endosys.statusbar.mostrar_mensaje("Ha ocurrido un error obteniendo las prestaciones de la agenda", 1);
				});						
		},
		
		_seleccionar_row_prestaciones: function(row) {
				datatable_prestaciones.unselectAllRows();
				datatable_prestaciones.selectRow(row);
				datatable_prestaciones.clearTextSelection();
				gestion_agendas_chus.prestacion_id = datatable_prestaciones.getRecord(row).getData("id");
				gestion_agendas_chus.tipoExploracion_id = datatable_prestaciones.getRecord(row).getData("tipoExploracion_id");
		},
		
		mostrar: function() {
				gestion_agendas_chus.agenda_id = null;
				gestion_agendas_chus.servicio_id = null;
				TM.content_agendas_chus.activate();
				TM.content_agendas_chus.detalles.activate();
				Endosys.statusbar.mostrar_mensaje("Cargando selección de agenda...");
				return TM.content_agendas_chus.load_content(mainlayout, "content/gestion_agendas_chus.html"+ew_version_param())
				.done(function() {
					//	configurar la busqueda de agendas
					//	---------------------------------
					
					//	crear la tabla de resultados
					fielddef = [
						{key: "id", label: "Código", width: 70, resizeable: true, sortable: true},
						{key: "nombre", label: "Agenda", width: 400, resizeable: true, sortable: true}
					];
					gestion_agendas_chus.datatable_results = new YAHOO.widget.ScrollingDataTable("datatable_agendas_chus_result",
																		fielddef,
																		dummyDataSource,
																		{ initialLoad: false,
																		  MSG_EMPTY: "No se ha encontrado ninguna agenda."
																			,
																			height: "280px",
//																			  height: "280px",
																		  width: "370px"
																		});
					datatable_results = gestion_agendas_chus.datatable_results;
					datatable_results.subscribe("rowMouseoverEvent", datatable_results.onEventHighlightRow);
					datatable_results.subscribe("rowMouseoutEvent", datatable_results.onEventUnhighlightRow);
					
					//	evento click en una fila de la tabla
					datatable_results.subscribe("rowClickEvent", function(oArgs) {
							if (!datatable_results.getRecord(oArgs.target)) return;	//	comprobar que la fila tiene record asignado (porque la fila con el mensaje 'no hay resultados' no tiene record y daria error)
							gestion_agendas_chus._seleccionar_row(oArgs.target);
						});

					//	crear la tabla de resultados de prestaciones
					fielddef = [
						{key: "id", label: "Código", width: 70, resizeable: true, sortable: true},
						{key: "descripcion", label: "Prestación", width: 400, resizeable: true, sortable: true}
					];
					gestion_agendas_chus.datatable_prestaciones = new YAHOO.widget.ScrollingDataTable("datatable_prestaciones_result",
																		fielddef,
																		dummyDataSource,
																		{	initialLoad: false,
																			MSG_EMPTY: "Seleccione una agenda",
																			height: "280px"
//																				height: "280px",
//																				width: "450px"
																		});
					datatable_prestaciones = gestion_agendas_chus.datatable_prestaciones;
					datatable_prestaciones.subscribe("rowMouseoverEvent", datatable_prestaciones.onEventHighlightRow);
					datatable_prestaciones.subscribe("rowMouseoutEvent", datatable_prestaciones.onEventUnhighlightRow);
					
					//	evento click en una fila de la tabla
					datatable_prestaciones.subscribe("rowClickEvent", function(oArgs) {
						if (!datatable_prestaciones.getRecord(oArgs.target)) return;
						gestion_agendas_chus._seleccionar_row_prestaciones(oArgs.target);
					});

					//	buscar
					//Endosys.agendas_chus.obtener(TM.content_agendas_chus, null, datatable_results);
					Endosys.statusbar.mostrar_mensaje("Obteniendo las agendas...");
					Endosys.agendas_chus.index(TM.content_agendas_chus, null, {'datatable': datatable_results})
					.fail(function() {
						Endosys.statusbar.mostrar_mensaje("Ha ocurrido un error obteniendo las agendas", 1);
					});
					
					//	-----------------------------------
					Endosys.statusbar.mostrar_mensaje("Listo");
				});

		},
		
		cerrar: function() {
				if (gestion_agendas_chus.datatable_results) {
					gestion_agendas_chus.datatable_results.destroy();
					gestion_agendas_chus.datatable_results = null;
				}				
		}
		
	}


}();