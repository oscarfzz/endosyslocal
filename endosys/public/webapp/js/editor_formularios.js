/**
 * Esto es una prueba
**/
var editor_formularios = function() {
	var datatable;
	var formdata;
	var gruposcampos = {};

	return {
		datatable: null,

		_seleccionar_row: function(row) {
			datatable.unselectAllRows();
			datatable.selectRow(row);
			datatable.clearTextSelection();
		},

		mostrar: function(formulario_id, formulario_titulo) {
			TM.content_editorFormularios.activate();
			TM.content_editorFormularios.campos.activate();
			TM.content_editorFormularios.gruposcampos.activate();
			TM.content_editorFormularios.formulario.activate();
			Endosys.statusbar.mostrar_mensaje(_('Cargando Editor de formularios...'));	/*IDIOMOK*/
			TM.content_editorFormularios.load_content(mainlayout, 'content/editor_formularios.html'+ew_version_param()).done(function() {
				$('.layout_main_content').layout({
					west__size: 380,
					spacing_closed: 10,
					slideTrigger_open: "click",
					initClosed: false,
					resizable: false
				});

				// titulo formulario
				$('.layout_main_content #editorforms-titulo').html(formulario_titulo);

				// crear la tabla de campos
				// formatter para la columna 'tipo'
				var tipo_formatter = function(elLiner, oRecord, oColumn, oData) {
					if(oData == Endosys.campos.TIPO_TEXTO) {
						elLiner.innerHTML = _('Texto');		/*IDIOMAOK*/
					} else if(oData == Endosys.campos.TIPO_MEMO) {
						elLiner.innerHTML = _('Memo');		/*IDIOMAOK*/
					} else if(oData == Endosys.campos.TIPO_SELECCION) {
						elLiner.innerHTML = _('Select');	/*IDIOMAOK*/
					} else if(oData == Endosys.campos.TIPO_MULTI) {
						elLiner.innerHTML = _('Multi');		/*IDIOMAOK*/
					} else if(oData == Endosys.campos.TIPO_BOOL) {
						elLiner.innerHTML = _('Si/No');		/*IDIOMAOK*/
					} else if(oData == Endosys.campos.TIPO_SEPARADOR) {
						elLiner.innerHTML = _('Título');	/*IDIOMAOK*/
					}
				}

				var utilizado_formatter = function(elLiner, oRecord, oColumn, oData) {
					if(oData) {
						elLiner.innerHTML = _('Si');		/*IDIOMAOK*/
					} else {
						elLiner.innerHTML = _('No');		/*IDIOMAOK*/
					}
				}

				var row_formatter = function(elTr, oRecord) {
					if(oRecord.getData('utilizado')) {
						$(elTr).addClass('utilizado');
					}

					return true;
				}

				fielddef = [
					{key: 'nombre', label: _('Nombre'), width: 100, resizeable: true, sortable: true},									/*IDIOMAOK*/
					{key: 'titulo', label: _('Titulo'), width: 100, resizeable: true, sortable: true},									/*IDIOMAOK*/
					{key: 'tipo', label: _('Tipo'), width: 30, resizeable: false, sortable: true, formatter: tipo_formatter},			/*IDIOMAOK*/
					{key: 'utilizado', label: _('Usado'), width: 30, resizeable: false, sortable: true, formatter: utilizado_formatter}	/*IDIOMAOK*/
				];
				
				editor_formularios.datatable = new YAHOO.widget.ScrollingDataTable(
					"datatable_lista_campos",
					fielddef,
					dummyDataSource,
					{
						initialLoad: false,
						MSG_EMPTY: _('No se encontró el campo.'),	/*IDIOMAOK*/
						height: "350px",
						width: "343px",
						formatRow: row_formatter
					}
				);

				datatable = editor_formularios.datatable;
				// datatable.subscribe("rowMouseoverEvent", datatable.onEventHighlightRow);
				// datatable.subscribe("rowMouseoutEvent", datatable.onEventUnhighlightRow);
				controles.init_YUI_datatable(datatable);

				// evento click en una fila de la tabla
				datatable.subscribe("rowClickEvent", function(oArgs) {
					// comprobar que la fila tiene record asignado (porque la fila con el mensaje 'no hay resultados' no tiene record y daria error)
					if(!datatable.getRecord(oArgs.target)) {
						return;
					}

					editor_formularios._seleccionar_row(oArgs.target);
				});

				// columnas 'calculadas' (que no se extraen directamente de los campos devueltos por el datasource)
				datatable.doBeforeLoadData = function (sRequest, oResponse, oPayload) {
					for(var n in oResponse.results) {
						// campo 'utilizado' por defecto a false (no)
						oResponse.results[n].utilizado = false;
					}

					return true;
				};

				$("#editorforms-nuevo-campo-btn").button().click(function() {
					var el_nuevocampo = null;

					nuevo_campo_dialog.mostrar().then(function(nuevocampo) {
						// nuevocampo:  nombre, titulo, tipo, columnas, tipo_control
						el_nuevocampo = nuevocampo;

						return Endosys.campos.create(TM.content_editorFormularios, {
							nombre: nuevocampo.nombre,
							titulo: nuevocampo.titulo,
							tipo: nuevocampo.tipo,
							columnas: nuevocampo.columnas,
							tipo_control: nuevocampo.tipo_control,
							obligatorio: nuevocampo.obligatorio,
							solo_lectura: nuevocampo.solo_lectura,
							script: nuevocampo.calculado,
							valorPorDefecto: nuevocampo.valorPorDefecto,
							ambito: nuevocampo.ambito
						}).done(function(campo) {
							// añadir el campo al datatable de campos y seleccionarlo
							datatable.addRow({
								id: campo.id,
								columnas: el_nuevocampo.columnas,
								nombre: el_nuevocampo.nombre,
								titulo: el_nuevocampo.titulo,
								tipo: el_nuevocampo.tipo,
								utilizado: false
							});

							var rs = datatable.getRecordSet();
							datatable.unselectAllRows();
							datatable.selectRow(rs.getLength()-1);
							datatable.clearTextSelection();
							datatable.scrollTo( datatable.getRecord(rs.getLength()-1) );
						}).fail(function() {
							alert(_("Ocurrio un error al crear el campo."));	/*IDIOMAOK*/
						});
					});
				});

				$("#editorforms-editar-campo-btn").button().click(function() {
					var rs = datatable.getRecordSet();
					var sel = datatable.getSelectedRows();

					if(sel) {
						sel = sel[0];
						var pos = datatable.getRecordIndex(sel);
						var campo_id = rs.getRecord(sel).getData('id');

						editor_formularios.editar_campo(campo_id, pos);
					} else {
						alert(_("Debe seleccionar un campo"));	/*IDIOMAOK*/
					}
				});

				//  boton eliminar campo
				$("#editorforms-eliminar-campo-btn").button().click(function() {
					controles.confirm_dialog(_('Borrar Campo'), _('¿Está seguro que desea borrar el campo?')).done(function() {	/*IDIOMAOK*/
						var rs = datatable.getRecordSet();
						var sel = datatable.getSelectedRows();
						if(sel) sel = sel[0];
						var campo_id = rs.getRecord(sel).getData('id');

						Endosys.campos['delete'](TM.operaciones, campo_id, null, {'datatable': datatable});
					});
				});

				// boton guardar formulario
				$("#editorforms-guardar-btn").button().click(function() {
					var args = {};
					var grupoCampos;
					var campo;
					var gruposcampos_ordenados = formdata.get_gruposCampos_ordenados();
					args['gruposcampos'] = '';

					for(var n = 0; n < gruposcampos_ordenados.length; n++) {
						grupoCampos = gruposcampos_ordenados[n];

						for(var campo_id in grupoCampos.campos) {
							campo = grupoCampos.campos[campo_id];
							args[campo.id] = grupoCampos.id + ',' + campo.posx + ',' + campo.posy + ',' + campo.ancho + ',' + campo.alto;
						}

						if(args['gruposcampos'] != '') {
							args['gruposcampos'] = args['gruposcampos'] + ',';
						}

						args['gruposcampos'] = args['gruposcampos'] + grupoCampos.id;
					}

					Endosys.formularios.update(TM.content_editorFormularios.formulario, formulario_id, args);
				});

				$('#editorforms-anadir-grupocampos-btn').button().click(function() {
					var $option = $('#gruposCampos-lista-anadir option:selected');
					var grupocampos_id = $option.val();
					var columnas = gruposcampos[grupocampos_id] ? Number(gruposcampos[grupocampos_id].columnas) : 4;

					formdata.addGrupoCampos({
						id: grupocampos_id,
						titulo: $option.text(),
						'columnas': columnas
					});
					formdata.generar_completo(null, true);
				});

				$('#editorforms-nuevo-grupocampos-btn').button().click(function() {
					var el_nuevogrupocampos = null;

					nuevo_grupocampos_dialog.mostrar().then(function(nuevogrupocampos) {
						// nuevogrupocampos:    nombre, columnas
						el_nuevogrupocampos = nuevogrupocampos;

						return Endosys.grupos_campos.create(
							TM.operaciones,
							{
								nombre: nuevogrupocampos.nombre,
								columnas: nuevogrupocampos.columnas
							}
						);
					}).done(function(grupocampos) {
						$('#gruposCampos-lista-anadir').append($('<option value="' + grupocampos.id + '">' + el_nuevogrupocampos.nombre + '</option>'));

						gruposcampos[grupocampos.id] = {
							id: grupocampos.id,
							'nombre': el_nuevogrupocampos.nombre,
							'columnas': Number(el_nuevogrupocampos.columnas)
						}
					});
				});

				$('#editorforms-renombrar-grupocampos-btn').button().click(function() {
					var $option = $('#gruposCampos-lista-anadir option:selected');
					var grupocampos_id = $option.val();

					controles.input_dialog.mostrar(
						_('Renombrar grupo de campos'),							/*IDIOMAOK*/
						_('Ingresar nuevo nombre para este grupo de campos'),	/*IDIOMAOK*/
						$option.text()
					).then(function(nuevo_valor) {
						// modificar el nombre del grupo de campos
						return $.when(nuevo_valor, Endosys.grupos_campos.update(TM.operaciones, grupocampos_id, {nombre: nuevo_valor}));
					}).done(function(nuevo_valor) {
						$option.text(nuevo_valor);

						if(gruposcampos[grupocampos_id]) {
							gruposcampos[grupocampos_id].nombre = nuevo_valor;
						}

						formdata.renombrarGrupoCampos({
							id: grupocampos_id,
							titulo: nuevo_valor
						});

						formdata.generar_completo(null, true);
					});
				});

				$('#editorforms-eliminar-grupocampos-btn').button().click(function() {
					var grupocampos_id = null;

					controles.confirm_dialog(_('Borrar grupo de campos'), ('¿Desea borrar este grupo de campos?')).then(function() {	/*IDIOMAOK*/
						grupocampos_id = $('#gruposCampos-lista-anadir option:selected').val();
						
						return Endosys.grupos_campos['delete'](TM.operaciones, grupocampos_id)
					}).done(function() {
						if (gruposcampos[grupocampos_id]) {
							delete gruposcampos[grupocampos_id];
						}

						$('#gruposCampos-lista-anadir option:selected').remove();
					});
				});

				// BOTONES MANIPULACION FILAS HIGHLIGHT
				$('#editorforms-insertarfila-btn').button().click(function() {
					formdata.insertar_fila();
				});

				$('#editorforms-quitarfila-btn').button().click(function() {
					formdata.quitar_fila();
				});

				// actualizar lista de grupos de campos
				Endosys.grupos_campos.index(TM.content_editorFormularios.gruposcampos).done(function(gruposCampos) {
					var $lista = $('#gruposCampos-lista-anadir');
					$lista.empty();

					for(var n in gruposCampos) {
						var grupocampos = gruposCampos[n];

						gruposcampos[grupocampos.id] = {
							id: grupocampos.id,
							nombre: grupocampos.nombre,
							columnas: Number(grupocampos.columnas)
						}

						// xxx añadir solo los que no esten en el formdata
						$lista.append( $('<option value="' + grupocampos.id + '">' + grupocampos.nombre + '</option>') );
					}
				});

				// cargar el formulario
				Endosys.formularios.show(TM.content_editorFormularios.formulario, formulario_id).done(function(response) {
					var formulario = {
						id: formulario_id,
						titulo: formulario_titulo,
						$contenedor: $('#editor_formularios_tab form'),
						controles: []
					};

					formdata = formularios.generar_formulario(response, formulario, true);

					// el regenerar el formulario marcar los campos utilizados en el datatable
					formdata.onGenerarGrupoCampos = function(grupoCampos) {
						var i, record;
						var allRows = datatable.getTbodyEl().rows;

						for(i = 0; i < allRows.length; i++) {
							record = datatable.getRecord(allRows[i]);                                           
							var utilizado = (record.getData("id") in grupoCampos.campos);
							record.setData("utilizado", utilizado);
							// datatable.updateCell(record, 'utilizado', utilizado);
							// datatable.updateRow(record, {'utilizado': utilizado});
						}

						datatable.render();
					}

					// al quitar un campo del formdata seleccionarlo en el datatable
					formdata.onQuitarCampo = function(campo) {
						// buscar el record por el campo.id
						var i, record;
						var allRows = datatable.getTbodyEl().rows;

						for(i = 0; i < allRows.length; i++) {
							record = datatable.getRecord(allRows[i]);

							if(record.getData("id") == campo.id) {
								datatable.unselectAllRows();
								datatable.selectRow(record);
								datatable.clearTextSelection();
								datatable.scrollTo(record);
								
								return;
							}
						}
					}

					// necesito el formdata en este evento por eso lo subscribo aqui
					// XXX tambien habria que hacerlo en otros eventos, cualquiera que pueda recrear los trs (buscar llamadas a _addTrEl en datatable.js)
					datatable.subscribe("renderEvent", function() {
						var i, id, record, allRows = datatable.getTbodyEl().rows;

						for(i = 0; i < allRows.length; i++) {
							id = allRows[i].id;                                                 
							record = datatable.getRecord(allRows[i]);

							// declarar un 'campo' para el formdata
							var campo = {
								id: Number(record.getData("id")),
								nombre: record.getData("nombre"),
								tipo: record.getData("tipo"),
								tipo_control: record.getData("tipo_control"),
								titulo: record.getData("titulo"),
								ancho: Number(record.getData("columnas")),
								alto: Endosys.campos.get_alto_por_defecto( record.getData("tipo") ),
								orden: -1,
								posx: -1,
								posy: -1,
								solo_lectura: 0,
								script: null
							};

							campo.valor = formdata.valorCampo_from_json(campo, null);

							$('#'+id).addClass('campo-drag-drop').data({
								'campo': campo,
								'formdata': formdata
							}).draggable({
								opacity: 0.5,
								helper: 'clone'
							});
						}

						// además el datatatable es un droppable, para quitar campos
						$(datatable.getTbodyEl()).droppable({
							accept: ".campo-drag-drop",
							tolerance: "pointer",
							drop: function(event, ui) {
								// this:   el TD en el que se está soltando
								// ui:     info de lo que se está arrastrando
								var campo = ui.draggable.data('campo');
								var formdata = ui.draggable.data('formdata');
								var grupoCampos = formdata.get_grupoCampos_by_td(ui.draggable);

								if(!grupoCampos) return;

								// retrasar la ejecución por si se re-crean los elementos involucrados...
								setTimeout(function() {
									formdata.quitarCampo(campo.id);
									formdata.generar_grupoCampos(grupoCampos);

									if(formdata.onQuitarCampo) formdata.onQuitarCampo(campo);
								}, 0);
							}
						});
					});

					datatable.render();
				});

				// cargar todos los campos en el listado de campos
				Endosys.campos.index(TM.content_editorFormularios.campos, null, {'datatable': datatable});
				Endosys.statusbar.mostrar_mensaje(_('Listo'));	/*IDIOMAOK*/
			});
		},

		editar_campo: function(campo_id, pos_datatable){
			// si viene pos_datatable entonces luego se puede actualizar el datatable,
			// sino no se edita
			nuevo_campo_dialog.mostrar(campo_id).then(function(nuevocampo) {
				el_nuevocampo = nuevocampo;

				return Endosys.campos.update(
					TM.content_editorFormularios,
					campo_id,
					{
						nombre: nuevocampo.nombre,
						titulo: nuevocampo.titulo,
						tipo: nuevocampo.tipo,
						columnas: nuevocampo.columnas,
						tipo_control: nuevocampo.tipo_control,
						obligatorio: nuevocampo.obligatorio,
						solo_lectura: nuevocampo.solo_lectura,
						script: nuevocampo.calculado,
						valorPorDefecto: nuevocampo.valorPorDefecto,
						ambito: nuevocampo.ambito
					}
				).done(function(campo) {
					// añadir el campo al datatable de campos y seleccionarlo
					if(pos_datatable != undefined) {
						datatable.updateRow(
							pos_datatable,
							{
								id: campo_id,
								columnas: el_nuevocampo.columnas,
								nombre: el_nuevocampo.nombre,
								titulo: el_nuevocampo.titulo,
								tipo: el_nuevocampo.tipo,
								utilizado: false
							}
						);
					}
				}).fail(function() {
					alert("Ocurrio un error al actualizar el campo.");	//IDIOMAOK
				});
			});
		},

		cerrar: function() {
			// aqui puedo destruir los objetos que se hayan creado para liberar memoria
			if(editor_formularios.datatable) {
				editor_formularios.datatable.destroy();
				editor_formularios.datatable = null;
			}
		}
	}
}();