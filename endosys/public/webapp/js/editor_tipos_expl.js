var editor_tipos_expl = function() {
	var datatable;
	var formdata;
	var _modificado = false;

	return {
		_row: null,
		tipoexpl_id: null,
		tipoexpl_nombre: null,	// solo utilizado para mostrar inicialmente el nombre del tipo de expl al renombrarlo
		tipoexpl_codigo: null,
		tipoexpl_servicio: null,
		datatable: null,

		_check_modificado: function(func) {
			if(_modificado) {
				controles.confirm_dialog(
					_('Tipo de exploración modificada'),	/*IDIOMAOK*/
					_('El tipo de exploración seleccionada ha sido modificada, si continua cualquier cambio realizado se perderá. ¿Está seguro que desea seleccionar otro tipo de exploración?'),	/*IDIOMAOK*/

					function() {
						_modificado = false;	//	no volver a preguntar
						func();
					}
				);
			} else {
				func();
			}
		},

		_mostrartipoexpl: function(tipoexpl_id) {
			//	mostrar los formularios asignados al tipo de expl
			_modificado = false;
			var $lista_seleccionados = $('#formularios_seleccionados');
			$lista_seleccionados.empty();

			if (tipoexpl_id == null) return;

			Endosys.formularios.index(TM.content_editorTiposExpl.tiposexploracion, {'tipoexploracion_id': tipoexpl_id}).done(function(formularios) {
				for (var i=0; i < formularios.length; i++) {
					$lista_seleccionados.append( $('<option value="' + formularios[i].id + '">' + formularios[i].titulo + '</option>') );
				}
			});
		},

		_seleccionar_row: function(row) {
			//	comprobar primero si se ha modificado la actual
			var do_it = function() {
				datatable.unselectAllRows();
				datatable.selectRow(row);
				datatable.clearTextSelection();

				editor_tipos_expl.tipoexpl_id = datatable.getRecord(row).getData("id");
				editor_tipos_expl.tipoexpl_nombre = datatable.getRecord(row).getData("nombre");
				editor_tipos_expl.tipoexpl_codigo = datatable.getRecord(row).getData("codigo");

				if(datatable.getRecord(row).getData("servicio") && datatable.getRecord(row).getData("servicio").codigo) {
					editor_tipos_expl.tipoexpl_servicio = datatable.getRecord(row).getData("servicio").codigo;
				} else {
					editor_tipos_expl.tipoexpl_servicio = datatable.getRecord(row).getData("servicio");
				}
				
				editor_tipos_expl._mostrartipoexpl(editor_tipos_expl.tipoexpl_id);
				editor_tipos_expl._row = row;

				//completar informacion de nombre en el titulo
				$("#form_select").html("("+_("Seleccionado")+": "+ editor_tipos_expl.tipoexpl_nombre+ ")");	//IDIOMAOK
			}

			editor_tipos_expl._check_modificado(do_it);
		},

		init_form_tipo_expl: function(tipo_expl) {
			var $form_tipo_expl = $("#tipo_exploracion_detail");

			// Busca los servicios.
			Endosys.servicios.index(TM.content_editorTiposExpl.tiposexploracion).then(function(servicios) {
				var $servicios = $form_tipo_expl.find("#servicio_tipo_expl");

				for(var i = 0; i < servicios.length; i++) {
					var $op = $('<option value="' + servicios[i].id + '">' + servicios[i].nombre + '</option>');

					// selecciona los servicios si viene con el objeto de tipo_expl y tiene seleccionado uno
					if(tipo_expl && tipo_expl.servicios) {
						var array_servicios_id = tipo_expl.servicios.map(function(el) {
							return el.id;
						});

						if($.inArray(servicios[i].id, array_servicios_id) !== -1) {
							$op.attr('selected', '');
						}
					}

					$servicios.append($op);
				}

				//	crea el select de servicios // adaptable en futuro a multiselect
				$form_tipo_expl.find("#servicio_tipo_expl").multiselect({
					multiple: true,
					header: false,
					minWidth: 320,
					selectedList: 3,
					noneSelectedText: _('Ninguno'),	/*IDIOMAOK*/
					//selectedText: _('# Servicio seleccionado...'),	/*IDIOMAOK*/
					//click: function(event, ui){},
				});

				if(tipo_expl) {
					$form_tipo_expl.find("#nombre_tipo_expl").val(tipo_expl.nombre);
					$form_tipo_expl.find("#codigo_tipo_expl").val(tipo_expl.codigo);
					$form_tipo_expl.find("#duracion_tipo_expl").val(tipo_expl.duracion);
					$form_tipo_expl.find("#color_tipo_expl").val(tipo_expl.color);
					$form_tipo_expl.find("#orden_tipo_expl").val(tipo_expl.orden);
				} else {
					$form_tipo_expl.find("#color_tipo_expl").val("#80FFA0");
					$form_tipo_expl.find("#duracion_tipo_expl").val(opciones_config["GESTION_AGENDA.CITA.TIEMPO_POR_DEFECTO"] || 30);
				}
			});
		},

		mostrar: function() {
			TM.content_editorTiposExpl.activate();
			TM.content_editorTiposExpl.tiposexploracion.activate();
			TM.content_editorTiposExpl.detalles.activate();
			Endosys.statusbar.mostrar_mensaje(_('Cargando editor de tipo de exploración'));	/*IDIOMAOK*/
			TM.content_editorTiposExpl.load_content(mainlayout, 'content/editor_tipos_exploracion.html'+ew_version_param()).done(function() {
				$('.layout_main_content').layout({
					west__size: 300,
					spacing_closed: 10,
					slideTrigger_open: "click",
					initClosed: false,
					resizable:	false
					// togglerAlign_open: "top"
				});

				// var format_activo = function(el, oRecord, oColumn, oData) {
				// 	if(oData == "true") {
				// 		el.innerHTML = '<input type="checkbox" checked="checked">';
				// 	} else if(oData == 'false') {
				// 		el.innerHTML = '<input type="checkbox">';
				// 	} else {
				// 		el.innerHTML = '<input type="checkbox">';
				// 	}
				// }

				fielddef = [
					{key: 'nombre', label: _('Nombre'), width: 200, resizeable: true, sortable: true},	/*IDIOMAOK*/
					// {key: 'color', label: 'Color', width: 100, resizeable: true, sortable: true},
					// {key: 'activo', label: 'Active', width: 30, resizeable: false, sortable: true, formatter: format_activo}	/*IDIOMA*/
					{key: 'activo', label: _('Activo'), width: 30, resizeable: false, sortable: true, formatter: 'checkbox'}	/*IDIOMAOK*/
				];

				editor_tipos_expl.datatable = new YAHOO.widget.ScrollingDataTable(
					"datatable_tipos_expl",
					fielddef,
					dummyDataSource,
					{
						initialLoad: false,
						MSG_EMPTY: _('No se encontró ningún tipo de exploración.'),	/*IDIOMAOK*/
						height: "400px",																			  
						width: "280px"
					}
				);

				datatable = editor_tipos_expl.datatable;
				// datatable.subscribe("rowMouseoverEvent", datatable.onEventHighlightRow);
				// datatable.subscribe("rowMouseoutEvent", datatable.onEventUnhighlightRow);
				controles.init_YUI_datatable(datatable);

				// columnas 'calculadas' (que no se extraen directamente de los campos devueltos por el datasource)

				// datatable.doBeforeLoadData = function (sRequest, oResponse, oPayload) {
				// 	for(var n in oResponse.results) {
				// 		//	campo 'utilizado' por defecto a false (no)
				// 		oResponse.results[n].utilizado = false;
				// 	}

				// 	return true;
				// };

				//	evento click en una fila de la tabla
				// SI HACEMOS CLICK EN EL CHECKBOX "Active" SE DEBERÁ GUARDAR EL VALOR DE ESTE CAMPO
				datatable.subscribe("checkboxClickEvent", function(oArgs) {
					var elCheckbox = oArgs.target;
					var oRecord = this.getRecord(elCheckbox);
					var newValueActive = elCheckbox.checked;
					var tipoexpl_id = oRecord.getData("id");

					console.log(newValueActive);
					console.log(tipoexpl_id);

					Endosys.tipos_exploracion.update(TM.content_editorTiposExpl, tipoexpl_id, {'activo': newValueActive ? '1' : '0'});				
				});

				datatable.subscribe("rowClickEvent", function(oArgs) {
					// comprobar que la fila tiene record asignado (porque la fila con el mensaje 'no hay resultados' no tiene record y daria error)
					if(!datatable.getRecord(oArgs.target)) return;
					
					editor_tipos_expl._seleccionar_row(oArgs.target);
				});

				$('#editor-nuevo-tipoexpl-btn').button().click(function() {
					controles.modal_dialog.mostrar({
						title: _('Nuevo tipo de exploración'),	//IDIOMAOK
						buttons: {
							Aceptar: _("Guardar")
						},
						height:'500',
						resizable: true,
						enterAccept: false,
						result: function() {
							var tipo_expl = {};
							tipo_expl.nombre = $("#nombre_tipo_expl").val();
							tipo_expl.codigo = $("#codigo_tipo_expl").val();
							tipo_expl.servicio = $("#servicio_tipo_expl").val();
							tipo_expl.color = $("#color_tipo_expl").val();
							tipo_expl.duracion = $("#duracion_tipo_expl").val();
							tipo_expl.orden = $("#orden_tipo_expl").val();

							return tipo_expl;
						},
						init: function(accept) {
							var $dialog = this;

							// cargar el contenido
							return $.get("content/dialog_editar_tipo_exploracion.html"+ew_version_param()).done(function(html) {
								$dialog.html(html);
								editor_tipos_expl.init_form_tipo_expl();
							});
						}
					}).then(function(tipo_expl) {
						el_nombre = tipo_expl.nombre;
						el_codigo = tipo_expl.codigo;

						// Crear
						var params = {
							'nombre': tipo_expl.nombre,
							'codigo': tipo_expl.codigo,
							'servicios': (tipo_expl.servicio != null) ? tipo_expl.servicio.join(",") : "",
							'activo': 1,
							'color': tipo_expl.color,
							'orden': tipo_expl.orden,
							'duracion': tipo_expl.duracion
						};

						return Endosys.tipos_exploracion.create(TM.content_editorTiposExpl.tiposexploracion, params);
					}).done(function(tipoexpl) {
						// agregar al datatable
						var fields = {
							'id': tipoexpl.id,
							'nombre': el_nombre,
							'codigo': el_codigo,
							// 'servicio': el_servicio,
							'activo': 'sí'
						};

						datatable.addRow(fields);
						editor_tipos_expl._seleccionar_row(datatable.getRecordSet().getLength()-1);
					});
				});

				$('#editor-renombrar-tipoexpl-btn').button().click(function() {
					if(!editor_tipos_expl.tipoexpl_id) {
						alert(_("Debe seleccionar el tipo de exploración a editar"));	//IDIOMAOK
						return;
					}

					editor_tipos_expl._check_modificado(function() {
						controles.modal_dialog.mostrar({
							title: _('Editar tipo de exploración'),	//IDIOMAOK
							buttons: {Aceptar: _("Guardar")},
							height:'500',
							resizable: true,
							enterAccept: false,
							result: function() {
								var tipo_expl = {};
								tipo_expl.nombre = $("#nombre_tipo_expl").val();
								tipo_expl.codigo = $("#codigo_tipo_expl").val();
								tipo_expl.servicio = $("#servicio_tipo_expl").val();
								tipo_expl.color = $("#color_tipo_expl").val();
								tipo_expl.duracion = $("#duracion_tipo_expl").val();
								tipo_expl.orden = $("#orden_tipo_expl").val();

								return tipo_expl;
							},
							init: function(accept) {
								var $dialog = this;
								
								// cargar el contenido
								return $.get("content/dialog_editar_tipo_exploracion.html" + ew_version_param()).done(function(html) {
									$dialog.html(html);

									// carga los datos del tipo de exploracion a editar
									Endosys.tipos_exploracion.show(TM.content_editorTiposExpl.tiposexploracion, editor_tipos_expl.tipoexpl_id).done(function(tipo_expl) {
										editor_tipos_expl.init_form_tipo_expl(tipo_expl);
									});
								});
							}
						}).then(function(tipo_expl) {
							el_nombre = tipo_expl.nombre;
							el_codigo = tipo_expl.codigo;

							// Crear
							var params = {
								'nombre': tipo_expl.nombre,
								'codigo': tipo_expl.codigo,
								'servicios': (tipo_expl.servicio != null) ? tipo_expl.servicio.join(",") : "",
								'color': tipo_expl.color,
								'orden': tipo_expl.orden,
								'duracion': tipo_expl.duracion
							};

							return Endosys.tipos_exploracion.update(TM.content_editorTiposExpl.tiposexploracion, editor_tipos_expl.tipoexpl_id, params).then(function() {
								return tipo_expl;
							});
						}).done(function(tipoexpl) {
							// agregar al datatable
							var fields = {
								'id': tipoexpl.id,
								'nombre': tipoexpl.nombre,
								'codigo': tipoexpl.codigo,
								// 'servicio': el_servicio,
								'activo': 'sí'
							};

							// XXX tendria que editar el row del datatable
							// datatable.addRow(fields);
							// editor_tipos_expl._seleccionar_row(datatable.getRecordSet().getLength()-1);
						});					
					});
				});

				$('#editor-eliminar-tipoexpl-btn').button().click(function() {
					if (!editor_tipos_expl.tipoexpl_id){
						alert(_("Debe seleccionar el tipo de exploración"));	//IDIOMAOK
						return;
					}

					controles.confirm_dialog(_('Eliminar tipo de exploración'), _('¿Estás seguro de que quieres eliminar este tipo de exploración?')).then(function() {	/*IDIOMAOK*/
						return Endosys.tipos_exploracion['delete'](TM.operaciones, editor_tipos_expl.tipoexpl_id, null, {'datatable': datatable})
					}).done(function() {
						editor_tipos_expl._mostrartipoexpl(null);
					}).fail(function() {
						Endosys.statusbar.mostrar_mensaje(_('No se pudo borrar el tipo de exploración.'), 1);	/*IDIOMAOK*/
					});
				});

				$('#editor-anadirform-btn').button({
					text: false,
					icons: {
						primary: "ui-icon-triangle-1-w"
					}
				}).click(function() {
					var $lista_seleccionados = $('#formularios_seleccionados');
					
					$('#formularios_todos').find('option:selected').each(function(index, el) {
						// si ya está añadido no volverlo a añadir
						if($lista_seleccionados.find('option[value="' + $(el).val() + '"]').length) return;

						$lista_seleccionados.append($(el).clone());
						_modificado = true;
					});
				});

				$('#formularios_todos').dblclick(function() {
					$('#editor-anadirform-btn').click()
				});

				$('#editor-quitarform-btn').button({
					text: false,
					icons: {
						primary: "ui-icon-triangle-1-e"
					}
				}).click(function() {
					if($('#formularios_seleccionados').find('option:selected').remove().length) {
						_modificado = true;
					}
				});

				$('#formularios_seleccionados').dblclick(function() {
					$('#editor-quitarform-btn').click()
				});

				// botones arriba y abajo
				$('#editor-formarriba-btn').button({
					text: false,
					icons: {
						primary: "ui-icon-triangle-1-n"
					}
				}).click(function() {
					var $selected = $('#formularios_seleccionados option:selected');
					var $prev = $selected.prev();

					if($prev.length) $prev.before($selected); {
						_modificado = true;
					}
				});

				$('#editor-formabajo-btn').button({
					text: false,
					icons: {
						primary: "ui-icon-triangle-1-s"
					}
				}).click(function() {
					var $selected = $('#formularios_seleccionados option:selected');
					var $next = $selected.next();

					if($next.length) {
						$next.after($selected);
					}

					_modificado = true;
				});

				$('#editor-guardar-btn').button().click(function() {
					var formularios = $('#formularios_seleccionados option').map(function(index, el) {
						return el.value;
					}).get().join(',');

					var v = $( datatable.getTrEl(editor_tipos_expl._row) ).find('input:checkbox:checked').val() ? '1' : '0';

					Endosys.tipos_exploracion.update(TM.content_editorTiposExpl.tiposexploracion, editor_tipos_expl.tipoexpl_id, {'formularios': formularios, activo: v});
					_modificado = false;
				});

				$('#editor-cancelar-btn').button().click(function() {
					// volver a cargar los datos
					_modificado = false;
					editor_tipos_expl._mostrartipoexpl(editor_tipos_expl.tipoexpl_id);
				});

				$('#editor-nuevoform-btn').button().click(function() {
					controles.input_dialog.mostrar(
						_('Nuevo formulario'),	/*IDIOMAOK*/
						_('Escribe el título para el nuevo formulario'),	/*IDIOMAOK*/
						''
					).then(function(nuevo_valor) {
						// crear el nuevo form
						return $.when(
							Endosys.formularios.create(TM.operaciones, {'titulo': nuevo_valor}),
							nuevo_valor	//	con el when puedo añadir args al done
						);
					}).done(function(formulario, titulo_formulario) {
						// añadirlo a la lista
						var formulario_id = formulario[0].id;

						$('#formularios_todos').append( $('<option value="' + formulario_id + '">' + titulo_formulario + '</option>') );
					});
				});

				$('#editor-renombrarform-btn').button().click(function() {
					var $option = $('#formularios_todos option:selected');

					if($option.length != 1) return;

					controles.input_dialog.mostrar(
						_('Renombrar formulario'),	/*IDIOMAOK*/
						_('Escribe el nombre para el formulario'),	/*IDIOMAOK*/
						$option.text()
					).then(function(nuevo_valor) {
						// modificar el nombre del formulario
						return $.when(
							nuevo_valor,	//	(esta es una forma de "arrastrar" una variable al siguiente done/then)
							Endosys.formularios.update(TM.operaciones, $option.val(), {titulo: nuevo_valor})
						);
					}).done(function(nuevo_valor) {
						$option.text(nuevo_valor);
					});
				});

				$('#editor-eliminarform-btn').button().click(function() {
					var $option = $('#formularios_todos option:selected');

					if ($option.length != 1) return;

					controles.confirm_dialog(_('Eliminar formulario'), _('¿Estás seguro de que quieres eliminar el formulario seleccionado?')).then(function() {	/*IDIOMAOK*/
						return Endosys.formularios['delete'](TM.operaciones, $option.val());
					}).done(function() {
						$option.remove();
					});
				});

				$('#editor-editarform-btn').button().click(function() {
					set_titulo_pantalla(_('Editor de formulario'));	/*IDIOMAOK*/
					desactivar_asistente();

					var $selected = $('#formularios_todos option:selected');

					if (!$selected.length) return;

					var formulario_id = $selected.val();
					var formulario_titulo = $selected.text();
					contenido_principal.mostrar(editor_formularios, formulario_id, formulario_titulo);
				});

				$('#editor-importarform-btn').button();

				$('#editor-importar-fileupload').fileupload({
					url: '/rest/formularios',
					dataType: 'xml',
					done: function(e, result) {
						// añadirlo a la lista
						var xml = result.jqXHR.responseXML;
						var formulario_id = xml.getElementsByTagName('formulario')[0].getAttribute('id');
						var titulo = '(imported form)';	//	XXX	de momento no se retorna el titulo.../*IDIOMA*/

						$('#formularios_todos').append(
							$('<option value="' + formulario_id + '">' + titulo + '</option>')
						);

						editor_tipos_expl._reloadFormsDisponibles();
					}
				});

				$('#editor-exportarform-btn').button().click(function(e) {
					var formulario_id = $('#formularios_todos option:selected').first().val();
					//var formulario_titulo = $('#formularios_todos option:selected').first().text();

					if(formulario_id) {
						window.open(Endosys.formularios.resource + '/' + formulario_id + '.download', null);
					}
				});
				
				editor_tipos_expl._reloadFormsDisponibles();
			});
		},
		
		_reloadFormsDisponibles: function() {
			// cargar todos los tipos de exploracion
			Endosys.tipos_exploracion.index(TM.content_editorTiposExpl.tiposexploracion, {'_all': 1}, {'datatable': datatable});
			Endosys.statusbar.mostrar_mensaje(_('Listo'));	/*IDIOMOK*/
			
			// cargar todos los formularios
			var $lista_todos = $('#formularios_todos');
			$lista_todos.empty();
			
			Endosys.formularios.index(TM.content_editorTiposExpl.detalles, {"_all": 1}).done(function(formularios) {
				for(var i = 0; i < formularios.length; i++) {
					$lista_todos.append( $('<option value="' + formularios[i].id + '">' + formularios[i].titulo + '</option>') );
				}
			});
		},

		cerrar: function() {
			// aqui puedo destruir los objetos que se hayan creado para liberar memoria
			if(editor_tipos_expl.datatable) {
				editor_tipos_expl.datatable.destroy();
				editor_tipos_expl.datatable = null;
			}
		}
	}
}();