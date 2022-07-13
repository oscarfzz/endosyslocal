var gestion_busquedas = function () {
	var datatable_results;

	var eliminar_btn;
	var renombrar_btn;
	var modificar_btn;
	var ejecutar_btn;

	return {
		datatable_results: undefined,

		mostrar: function () {
			TM.gestion_busquedas.activate();
			TM.gestion_busquedas.detalles.activate();
			Endotools.statusbar.mostrar_mensaje(_('Cargando gestión de búsquedas...'));	// IDIOMAOK

			return TM.gestion_busquedas.load_content(mainlayout, "content/gestion_busquedas.html" + ew_version_param()).done(function () {
				// CREAR layout
				$('.layout_main_content').layout({
					//west__size: 330,
					closable: false,
					resizable: false,
					slidable: false,
					initClosed: false
				});

				// funcion para formatear el estado de la tarea en el datatable
				var formatterNivel = function (container, record, column, data) {
					switch (parseInt(data, 10)) {
						case 0:
							container.innerHTML = _("Público global");
							break;
						case 1:
							container.innerHTML = _("Público de servicio");
							break;
						case 2:
							container.innerHTML = _("Protegido global");
							break;
						case 3:
							container.innerHTML = _("Protegido de servicio");
							break;
						case 4:
							container.innerHTML = _("Privada");
							break;
						default:
							container.innerHTML = "¿?";
					}
				}

				// crear la tabla de resultados
				gestion_busquedas.datatable_results = new YAHOO.widget.ScrollingDataTable(
					"datatable_busqueda_result",
					[
						{ key: 'descripcion', label: _('Búsquedas'), width: 350, resizeable: true, sortable: true },	// IDIOMAOK
						{ key: 'username', label: _('Propietario'), width: 150, resizeable: true, sortable: true },
						{ key: 'nivel', label: _('Nivel'), formatter: formatterNivel, width: 150, resizeable: true, sortable: true }
					],
					dummyDataSource,
					{ initialLoad: false, MSG_EMPTY: _('No se ha encontrado ninguna búsqueda'), height: "400px" }		// IDIOMAOK
				);
				datatable_results = gestion_busquedas.datatable_results;
				datatable_results.subscribe("rowClickEvent", datatable_results.onEventSelectRow);
				//controles.init_YUI_datatable(datatable_results);
				controles.init_YUI_datatable(datatable_results, { layoutPaneResizing: $('.layout_main_content').layout().panes.center });
				Endotools.busqueda_avanzada.index(
					TM.gestion_busquedas,
					{ 'username': Endotools.auth.username, 'servicio_id': Endotools.auth.servicio_activo.id },
					{ 'datatable': datatable_results }
				);

				$("#nuevo_btn").button().click(function () {
					desactivar_asistente();
					ejecutar_busqueda.mostrar_ejecutar_busqueda_no_exist();
				});

				$("#eliminar_btn").button().click(function () {
					desactivar_asistente();

					var selected = datatable_results.getSelectedRows();
					if (selected.length == 1) {
						//verificamos que ha seleccionado alguna fila
						var confirmacion = confirm("¿Esta seguro que quiere borrar esta busqueda avanzada?");	// IDIOMAOK

						if (confirmacion) {
							var pos = datatable_results.getRecordIndex(selected[0]);
							var object_selected = datatable_results.getRecord(pos);
							var id = object_selected._oData.id;
							var descripcion = object_selected._oData.descripcion;

							Endotools.busqueda_avanzada['delete'](TM.gestion_busquedas, id, null, { 'datatable': datatable_results }).done(function () {
								Endotools.busqueda_avanzada.index(TM.gestion_busquedas).done(function (busquedas_avanzadas) {
									//datatable_results.deleteRow(pos);
									var opciones_menu = userinfo.get_opciones_menu();
									gestion_busquedas.refrescar_menu_busquedas(opciones_menu, busquedas_avanzadas);
								});
							});
						}
					} else {
						alert(_('Debes seleccionar una búsqueda'));	// IDIOMAOK
					}
				});

				$("#renombrar_btn").button().click(function () {
					var selected = datatable_results.getSelectedRows();

					if (selected.length < 1) return;

					//desactivar_asistente();
					var pos = datatable_results.getRecordIndex(selected[0]);
					var object_selected = datatable_results.getRecord(pos);
					var id = object_selected._oData.id;
					var descripcion_antigua = object_selected._oData.descripcion;

					var titulo = _('Renombrar búsqueda');	// IDIOMAOK
					var desc_campo = _('Nueva descripción');	// IDIOMAOK
					var el_nuevo_valor = null;

					controles.input_dialog.mostrar(titulo, desc_campo, descripcion_antigua).then(function (nuevo_valor) {
						el_nuevo_valor = nuevo_valor;

						return Endotools.busqueda_avanzada.update(TM.gestion_busquedas, id, { 'descripcion': el_nuevo_valor });
					}).then(function () {
						return Endotools.busqueda_avanzada.index(TM.gestion_busquedas);
					}).done(function (busquedas_avanzadas) {
						var busqueda = busquedas_avanzadas[pos];
						console.log(busqueda);
						datatable_results.updateRow(pos, { id: id, descripcion: el_nuevo_valor, username: busqueda.username, nivel: busqueda.nivel });

						var opciones_menu = userinfo.get_opciones_menu();
						gestion_busquedas.refrescar_menu_busquedas(opciones_menu, busquedas_avanzadas);
					});
				});

				$("#ejecutar_btn").button().click(function () {
					var selected = datatable_results.getSelectedRows();

					if (selected.length == 1) {
						//verificamos que ha seleccionado alguna fila
						desactivar_asistente();

						var pos = datatable_results.getRecordIndex(selected[0]);
						var object_selected = datatable_results.getRecord(pos);
						var id = object_selected._oData.id;
						var descripcion = object_selected._oData.descripcion;

						ejecutar_busqueda.mostrar_ejecutar_busqueda_exist(id);
					} else {
						alert(_('Debes seleccionar una búsqueda'));	// IDIOMAOK
					}
				});

				$("#modificar_btn").button().click(function () {
					var selected = datatable_results.getSelectedRows();

					if (selected.length == 1) {
						//verificamos que ha seleccionado alguna fila
						desactivar_asistente();

						var pos = datatable_results.getRecordIndex(selected[0]);
						var object_selected = datatable_results.getRecord(pos);
						var id = object_selected._oData.id;
						var descripcion = object_selected._oData.descripcion;

						ejecutar_busqueda.mostrar_modificar_busqueda_exist(id, descripcion);
					} else {
						alert(_('Debes seleccionar una búsqueda'));	// IDIOMAOK
					}
				});

				Endotools.statusbar.mostrar_mensaje(_('Ready'));	// IDIOMAOK
			});
		},

		refrescar_menu_busquedas: function (opciones_menu, busquedas_avanzadas) {
			menu_principal.menu('destroy').remove();
			menu_principal = crear_menu_principal(opciones_menu, busquedas_avanzadas);
		}
	}
}();