/*
Solo se utiliza YUI para DataTable.
*/
var gestion_pacientes = function() {

	var datatable_results;
	var opcion_deshabilitados;

	return {

		paciente_id: null,
		datos_paciente_seleccionado: {},
		datatable_results: undefined,
		// PAGINACION - Paso 1: Activar paginacion
		paginacion: true,
		idunico_changed: false,

		obtener_paciente: function(tm, id, $form) {
			//	obtener los datos completos de un paciente por el Id
			Endotools.statusbar.mostrar_mensaje(_('Obteniendo los datos del paciente...'));/*IDIOMAOK*/
			return Endotools.pacientes.show(tm, id)
			.done(function(paciente) {
				var centro_id = Endotools.auth.servicio_activo.centro_id

				if (opciones_config["PACIENTE.PERMITIR_EDITAR_IDUNICO"]=="0"){
					$form.find('.paciente-idunico').prop("disabled",true);
				}else{
					$form.find('.paciente-idunico').prop("disabled",false);
				}

				$form.find('.paciente-dni').val(paciente.DNI);
				$form.find('.paciente-idunico').val(paciente.idunico);
				for (var i=0; i < paciente.centros.length; i++) {
					if ( paciente.centros[i].id === centro_id ){
						$form.find('.paciente-nhc-centro').val(paciente.centros[i].nhc);
					}
				}
				$form.find('.paciente-cip').val(paciente.CIP);
				$form.find('.paciente-nombre').val(paciente.nombre);
				$form.find('.paciente-apellido1').val(paciente.apellido1);
				$form.find('.paciente-apellido2').val(paciente.apellido2);
				/*coment prov
				$form.find('select.paciente-sexo').val(paciente.sexo).selectBoxIt('refresh');*/
				$form.find('select.paciente-sexo').val(paciente.sexo);
				$form.find('.paciente-fecha_nacimiento').val(paciente.fechaNacimiento).change();
				$form.find('.paciente-direccion').val(paciente.direccion);
				$form.find('.paciente-poblacion').val(paciente.poblacion);
				$form.find('.paciente-provincia').val(paciente.provincia);
				$form.find('.paciente-codigo_postal').val(paciente.codigoPostal);
				$form.find('.paciente-telefono1').val(paciente.telefono1);
				$form.find('.paciente-telefono2').val(paciente.telefono2);
				$form.find('.paciente-afiliacion').val(paciente.numAfiliacion);
				$form.find('.paciente-comentarios').val(paciente.comentarios);


				//	aseguradora: si aun no está el item, añadirlo
				var $paciente_aseguradora = $form.find('select.paciente-aseguradora');
				if (paciente.aseguradora) {
					if ($paciente_aseguradora.find('option[value="' + paciente.aseguradora_id + '"]').length < 1)
						$paciente_aseguradora.append($('<option value="' + paciente.aseguradora_id + '">' + paciente.aseguradora.nombre + '</option>'));
				}
				/*coment prov
				$paciente_aseguradora.val(paciente.aseguradora_id).selectBoxIt('refresh');*/
				$paciente_aseguradora.val(paciente.aseguradora_id);

				//	si está deshabilitado añadir la clase al contenedor para mostrarlo en rojo
				if (paciente.deshabilitado) {
					$form.addClass('paciente-deshabilitado');
				}
				Endotools.statusbar.mostrar_mensaje(_('Listo'));/*IDIOMAOK*/
				//$form.parent().find("button").prop("disabled", false);
			})
			.fail(function(error) {
				Endotools.statusbar.mostrar_mensaje(parseError(error.responseText), 1); /*IDIOMAOK*/
			});
		},

		guardar_paciente: function(tm, id, $form) {
			//	guardar los datos de un paciente por el Id
			Endotools.statusbar.mostrar_mensaje(_('Guardando los datos del paciente...'));/*IDIOMAOK*/
			var centro_id = Endotools.auth.servicio_activo.centro_id;
			//	sacar los params del formulario
			var params = {
				idunico:          $form.find('.paciente-idunico').val(),
				DNI:              $form.find('.paciente-dni').val(),
				CIP:              $form.find('.paciente-cip').val(),
				nombre:           $form.find('.paciente-nombre').val(),
				apellido1:        $form.find('.paciente-apellido1').val(),
				apellido2:        $form.find('.paciente-apellido2').val(),
				sexo:             $form.find('select.paciente-sexo').val(),
				fechaNacimiento:  $form.find('.paciente-fecha_nacimiento').val(),
				direccion:        $form.find('.paciente-direccion').val(),
				poblacion:        $form.find('.paciente-poblacion').val(),
				provincia:        $form.find('.paciente-provincia').val(),
				codigoPostal:     $form.find('.paciente-codigo_postal').val(),
				telefono1:        $form.find('.paciente-telefono1').val(),
				telefono2:        $form.find('.paciente-telefono2').val(),
				aseguradora_id:   $form.find('select.paciente-aseguradora').val(),
				numAfiliacion:    $form.find('.paciente-afiliacion').val(),
				comentarios:      $form.find('.paciente-comentarios').val(),
			}
			if ( $form.find('.paciente-nhc-centro').val() !== "") {
				params['centros'] = String(centro_id) + ":" + String($form.find('.paciente-nhc-centro').val());
			}
			return Endotools.pacientes.update(tm, id, params)
			.done(function() {
				Endotools.statusbar.mostrar_mensaje(_('Ready'));/*IDIOMAOK*/
			})
			.fail(function(data) {
				Endotools.statusbar.mostrar_mensaje(parseError(data.responseText), 1);
			});
		},

		nuevo_paciente: function(tm, $form) {
			//	crear un paciente
			Endotools.statusbar.mostrar_mensaje(_('Creando el paciente...'));/*IDIOMAOK*/
			var centro_id = !!Endotools.auth.servicio_activo ? Endotools.auth.servicio_activo.centro_id : null;
			//	sacar los params del formulario
			var params = {
				idunico:    $form.find('.paciente-idunico').val(),
				DNI:		$form.find('.paciente-dni').val(),
				CIP:		$form.find('.paciente-cip').val(),
				nombre:		$form.find('.paciente-nombre').val(),
				apellido1:	$form.find('.paciente-apellido1').val(),
				apellido2:	$form.find('.paciente-apellido2').val(),
				sexo:		$form.find('select.paciente-sexo').val(),
				fechaNacimiento: $form.find('.paciente-fecha_nacimiento').val(),
				direccion:	$form.find('.paciente-direccion').val(),
				poblacion:	$form.find('.paciente-poblacion').val(),
				provincia:	$form.find('.paciente-provincia').val(),
				codigoPostal: $form.find('.paciente-codigo_postal').val(),
				telefono1:	$form.find('.paciente-telefono1').val(),
				telefono2:	$form.find('.paciente-telefono2').val(),
				aseguradora_id:	$form.find('select.paciente-aseguradora').val(),
				numAfiliacion: $form.find('.paciente-afiliacion').val()
			}
			if ( $form.find('.paciente-nhc-centro').val() !== "" && centro_id !== null) {
				params['centros'] = String(centro_id) + ":" + String($form.find('.paciente-nhc-centro').val());
			}
			return Endotools.pacientes.create(tm, params)
			.done(function(paciente) {
				Endotools.statusbar.mostrar_mensaje(_('Listo'));/*IDIOMAOK*/
			})
			.fail(function(data) {
				Endotools.statusbar.mostrar_mensaje(parseError(data.responseText), 1);
			});
		},

		//no esta usado
		check_idunico_available: function(){
			// busca la historia que se escribió y controla si existe.
			// Si existe informa al usuario
			var valor = $form_pacientes.find(".paciente-idunico").val();
			if (valor){
				Endotools.pacientes.index(TM.operaciones, {'idunico': valor} ).done(function(data){
					nombre_completo = "";

					if (data.length>0){
						if (data[0].nombre) { nombre_completo += data[0].nombre }
						if (data[0].apellido1) { nombre_completo += data[0].apellido1 }
						if (data[0].apellido2) { nombre_completo += data[0].apellido2 } 

						alert(_("Ya existe un paciente con el "+ opciones_config.IDUNICO_LABEL) + ": " + valor + "\n " + //IDIOMAOK
						  nombre_completo)
					}	
				});
			}
		},

		_ini_form_paciente: function($form_pacientes) {
			/*	Inicializa el form de detalle de un paciente (los controles, botones...)

				$form_pacientes		Contenedor del form de pacientes

				o					(ESTA PARAMETRO YA NO SE USA)
									opcional. Objeto con callbacks de los botones que
									se quieren utilizar (o.onEliminar, o.onGuardar y
									o.onCancelar).
			*/

			$form_pacientes.i18n();

			// controlar el disable del campo historia si hay historia automatica
			// Solo funciona cuando con el idunico
			var input_historia = $form_pacientes.find(".paciente-idunico");
			if (opciones_config["PACIENTE.NHC_AUTOMATICO"]=="1"){
				input_historia.prop("disabled", true);
				input_historia.attr("placeholder", _("Autogenerado"));//IDIOMAOK
				input_historia.prop("readonly", true);
			}else{
				input_historia.prop("disabled", false);
				input_historia.prop("readonly", false);
				input_historia.attr("placeholder", "");//IDIOMAOK
			}

			//	calcular la edad actual
			$form_pacientes.find('.paciente-fecha_nacimiento').change(function() {
				var edad = calcular_edad( $form_pacientes.find('.paciente-fecha_nacimiento').val() );
				if (!$.isNumeric(edad)) edad = '-';
				$form_pacientes.find('.paciente-edad-actual').val(edad);
			});

			$form_pacientes.find('.cip-label').html(opciones_config.CIP_LABEL);
			$form_pacientes.find('.paciente-idunico-label').html('<strong>'+opciones_config.IDUNICO_LABEL+'</strong>');

			// Aseguradora: crear el control, y obtener las aseguradoras para llenar el listado
			var $paciente_aseguradora = $form_pacientes.find('select.paciente-aseguradora');
			$paciente_aseguradora.append($('<option value="">-</option>'));
			Endotools.aseguradoras.index(TM.operaciones, {'activo': 1} )
			.done(function(aseguradoras) {
				for (var i=0; i < aseguradoras.length; i++) {
					if ($paciente_aseguradora.find('option[value="' + aseguradoras[i].id + '"]').length < 1)
						$paciente_aseguradora.append($('<option value="' + aseguradoras[i].id + '">' + aseguradoras[i].nombre + '</option>'));
				}
			});

			// crear control autocomplete para el campo provincia "paciente-provincia"
			function highlightText(text, $node) {
				//condición para que no lleguen cadenas vacias al subrayado del AUTOCOMPLETE, la cadena vacia hace que funcione mal
				if ($.trim(text).length > 0) {

					var searchText = $.trim(text).toLowerCase(), currentNode = $node.get(0).firstChild, matchIndex, newTextNode, newSpanNode;
					while ((matchIndex = currentNode.data.toLowerCase().indexOf(searchText)) >= 0) {
						newTextNode = currentNode.splitText(matchIndex);
						currentNode = newTextNode.splitText(searchText.length);
						newSpanNode = document.createElement("span");
						newSpanNode.className = "highlight";
						currentNode.parentNode.insertBefore(newSpanNode, currentNode);
						newSpanNode.appendChild(newTextNode);
					}
				}
			}

			/* provincia */
			var $paciente_provincia = $form_pacientes.find('.paciente-provincia');
			$paciente_provincia.autocomplete({
			  source: function( request, response ) {
				Endotools.provincias.index(TM.operaciones, {'nombre': request.term})
				.done(function(provincias) {
					var listado_provincias = [];
					for (var n=0; n < provincias.length; n++) {
						var provincia = provincias[n];
						listado_provincias.push({label: provincia.nombre, value: provincia.nombre, id:provincia.id});
					}
					return response(listado_provincias);
				});

			  },
			 create: function( event, ui ) {
				/*$paciente_provincia.val(campo.valor.nombre);*/
			  },
			  minLength: 2
			})
			.addClass('endosys-autocomplete')
			.data("ui-autocomplete")._renderItem = function(ul, item) {
				var $a = $("<a></a>").text(item.label);
				highlightText(this.term, $a);
				return $("<li></li>").append($a).appendTo(ul);
			};

			/* CONTROL POBLACIÓN AUTOCOMPLETE "paciente-poblacion"*/
			var $paciente_poblacion = $form_pacientes.find('.paciente-poblacion');
			$paciente_poblacion.autocomplete({
			  source: function( request, response ) {
				Endotools.poblaciones.index(TM.operaciones, {'nombre': request.term})
				.done(function(poblaciones) {
					var listado_poblaciones = [];
					for (var n=0; n < poblaciones.length; n++) {
						var poblacion = poblaciones[n];
						listado_poblaciones.push({label: poblacion.nombre, value: poblacion.nombre, id:poblacion.id});
					}
					return response(listado_poblaciones);
				});
			  },
			 create: function( event, ui ) {
				/*$paciente_poblacion.val(campo.valor.nombre);*/
			  },
			  minLength: 2
			})
			.addClass('endosys-autocomplete')
			.data("ui-autocomplete")._renderItem = function(ul, item) {
				var $a = $("<a></a>").text(item.label);
				highlightText(this.term, $a);
				return $("<li></li>").append($a).appendTo(ul);

			};
		},

		mostrar_paciente: function(paciente_id, editable, opciones) {
			/*	Muestra el detalle del paciente en un dialog

					paciente_id		El id del paciente a mostrar. Si no se indica, se muestra
									el gestion_pacientes.paciente_id.
					editable	true|false	Indica si se permitirá modificar o eliminar el paciente
									desde el diálogo. Si no está activa la opción de configuración
									MOSTRAR_BOTONES_MODIFICACION_PACIENTES, se omitirá este valor (será false).
			*/
			paciente_id = paciente_id || gestion_pacientes.paciente_id;
			editable = !!editable && !!opciones_config.MOSTRAR_BOTONES_MODIFICACION_PACIENTES;
			eliminar_habilitado = true;
			update_datatable = true;

			if (opciones){
				if (opciones.btn_eliminar!= undefined && opciones.btn_eliminar == false){
					eliminar_habilitado = false;
				}
				if (opciones.update_datatable != undefined && opciones.update_datatable==false){
					update_datatable = false;
				}
			}

			//	configuración de botones Guardar/Aceptar y Eliminar.
			var buttons = {};
			if (editable) {
				buttons.Aceptar = _('Guardar');/*IDIOMAOK*/

				if (eliminar_habilitado){
					buttons[_('Eliminar')] = function() {/*IDIOMAOK*/
						var $dialog = $(this);
						controles.confirm_dialog(_('Eliminar paciente'), _('¿Está seguro de que desea eliminar este paciente?'))/*IDIOMAOK*/
						.then(function() {
							return Endotools.pacientes['delete'](TM.operaciones, paciente_id, null, {datatable: datatable_results})
						})
						.then(function() {
							$dialog.dialog('close');
						});
					}
				}

			} else {
				buttons.Aceptar = null;
				buttons.Cancelar = _('Cerrar');/*IDIOMAOK*/
			}

			//	mostrar el dialog
			return controles.modal_dialog.mostrar({
				title: _('Datos del paciente'), width: "790px", height: "auto",/*IDIOMAOK*/

				"buttons": buttons,
				"enterAccept": false,

				init: function(accept) {
					var $dialog = this;

					//	cargar el contenido
					return $.get("content/paciente.html"+ew_version_param())
					.done(function(htmldata) {

						$dialog.html(htmldata);
						gestion_pacientes._ini_form_paciente($dialog);
						if (opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'IDUNICO' ||
							opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'IDUNICO+NHC' ||
							opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'NHC+IDUNICO') {
							$('.paciente-idunico-group').show();
						}

						if (opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'NHC' ||
							opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'IDUNICO+NHC' ||
							opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'NHC+IDUNICO') {
							$('.paciente-nhc-group').show();
						}
						gestion_pacientes.obtener_paciente(TM.operaciones, paciente_id, $dialog);

					});
				}

				,result: function() {
					var valores = {
						id: 		paciente_id,
						historia:	this.find('.paciente-historia').val(),
						idunico:    this.find('.paciente-idunico').val(),
						DNI:		this.find('.paciente-dni').val(),
						CIP:		this.find('.paciente-cip').val(),
						nombre:		this.find('.paciente-nombre').val(),
						apellido1:	this.find('.paciente-apellido1').val(),
						apellido2:	this.find('.paciente-apellido2').val(),
						centros:    this.find('.paciente-nhc-centro').val()
					};

					if (editable){
						var resultado = gestion_pacientes.guardar_paciente(TM.operaciones, paciente_id, this);
						resultado.done(function(data){
							if (update_datatable){
								var row = datatable_results.getSelectedRows()[0];
								var pos = datatable_results.getRecordIndex(row);
								datatable_results.updateRow(pos, valores);
							}
						});
					}
					this.guardado=true;
					return this;
				}
			});
		},


		_seleccionar_row: function(row) {
				datatable_results.unselectAllRows();
				datatable_results.selectRow(row);
				datatable_results.clearTextSelection();
				gestion_pacientes.paciente_id = datatable_results.getRecord(row).getData("id");
				gestion_pacientes.datos_paciente_seleccionado = datatable_results.getRecord(row).getData();
		},

		mostrar_para_dialogo: function(callback_fn, capa_destino, opciones) {
				opcion_deshabilitados = (opciones && (opciones.opcion_deshabilitados == true));
				opcion_nuevo_paciente = (opciones && (opciones.nuevo_paciente == true));
				gestion_pacientes.paciente_id = null;
				gestion_pacientes.datos_paciente_seleccionado= {};
				TM.content_pacientes.activate();
				TM.content_pacientes.detalles.activate();
				TM.content_pacientes.buscar.activate();
				Endotools.statusbar.mostrar_mensaje(_('Cargando gestión de pacientes...'));/*IDIOMAOK*/

				var content_html = "content/gestion_pacientes.html"+ew_version_param();


				capa_destino.load(content_html, function(data,textStatus) {
					if (textStatus == "success") {
						capa_destino.i18n();
						gestion_pacientes.logica_pantalla(callback_fn, true, {"ocultar_nuevo_paciente": !opcion_nuevo_paciente});
					} else {
						alert(_('error al cargar el fichero gestion_pacientes.html'));/*IDIOMAOK*/
					}
				});
		},

		mostrar: function(callback_fn, opciones) {
				opcion_deshabilitados = (opciones && (opciones.opcion_deshabilitados == true));
				gestion_pacientes.paciente_id = null;
				TM.content_pacientes.activate();
				TM.content_pacientes.detalles.activate();
				TM.content_pacientes.buscar.activate();
				Endotools.statusbar.mostrar_mensaje(_('Cargando gestión de pacientes...'));/*IDIOMAOK*/

				var content_html = "content/gestion_pacientes.html";


				TM.content_pacientes.load_content(mainlayout, content_html+ew_version_param())
				.done(function() {
					gestion_pacientes.logica_pantalla(callback_fn);
				});

		},

		logica_pantalla: function(callback_fn, isDialog, opciones) {
			//	configurar la busqueda de pacientes
			//	-----------------------------------
			if (!opcion_deshabilitados) {
				$('p:has(#busqueda-pacientes-incl_deshab)').css('visibility', 'hidden');
			} else {
				//	por defecto, chequeado?
				$('#busqueda-pacientes-incl_deshab').prop('checked', opciones_config['PACIENTES_DESHABILITADOS.INCLUIR_POR_DEFECTO'] == '1');
			}

			if (opciones){
				if (opciones.ocultar_nuevo_paciente == true){
					$('#nuevo_paciente_btn').css('visibility', 'hidden');
				}
			}


			var selector1 = ".layout_main_content";
			var selector2 = ".contenedor2";

			if (isDialog) {
				//es un dialogo y cambia los selectores, ya que si no coge los layout de la capa de abajo
				selector1 = "#content_form_paciente " + selector1;
				selector2 = "#content_form_paciente " + selector2;
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
			$(selector2).layout({
				defaults: {
					fxName:		"none",
					fxSpeed:	"fast",
					size:		"auto",
					closable:	false,
					resizable:	false,
					slidable:	false,
					initClosed:	false
				},
				north__size: "auto"
			});


			//	botones
			$("#buscar_pacientes_btn").button();
			$("#nuevo_paciente_btn").button();
			var label_cipa = opciones_config.CIP_LABEL;
			$('#cip-label2').html(label_cipa);
			var label_idunicoa = opciones_config.IDUNICO_LABEL;
			$('#idunico-label2').html(label_idunicoa);
			//	crear la tabla de resultados
			YAHOO.widget.DataTable.Formatter.formatNHC = function(elLiner, oRecord, oColumn, oData) {
				if(typeof(oData) === "object") {
				 	elLiner.innerHTML = "";
				 	for (var i=0; i < oData.length; i++) {
				 		if (String(oData[i].id) === Endotools.auth.servicio_activo.centro_id) {
				 			elLiner.innerHTML = String(oData[i].nhc);
				 			break;
						}
				 	}
				} else {
					elLiner.innerHTML = oData;
				}
			};
			var fielddef = [
				{key: 'idunico', label: label_idunicoa, width: 90, resizeable: true, sortable: true},
				{key: 'centros', label: _('NHC'), width: 90, formatter:"formatNHC", resizeable: true, sortable: true},
				{key: 'CIP', label: label_cipa, width: 110, resizeable: true, sortable: true},
				{key: 'DNI', label: _('Paciente:DNI'), width: 90, resizeable: true, sortable: true},/*IDIOMAOK*/
				{key: 'nombre', label: _('Paciente:Nombre'), width: 140, resizeable: true, sortable: true},/*IDIOMAOK*/
				{key: 'apellido1', label: _('Paciente:html:1er apellido'), width: 140, resizeable: true, sortable: true},/*IDIOMAOK*/
				{key: 'apellido2', label: _('Paciente:html:2o apellido'), width: 140, resizeable: true, sortable: true}/*IDIOMAOK*/
			];

			// Define un custom row formatter para resaltar los deshabilitados
			var rowFormatter = function(elTr, oRecord) {
				if (oRecord.getData('deshabilitado')) {
					$(elTr).addClass('paciente-deshabilitado');
				}
				return true;
			};

			var opciones_datatable = {
				initialLoad:	false,
				MSG_EMPTY:		'<em>' + _('No se ha encontrado ningún paciente') + '</em>',/*IDIOMAOK*/
				formatRow:		rowFormatter,
				height:			"200px",	//	solo para que tenga el scrollbar, luego el alto es dinámico.
				width:			"100%"
			}



			//	y añadir un botón para ver el detalle del paciente
			fielddef.push({
				key: "button",
				label: "",
				width: 28,
				formatter: function(el, oRecord, oColumn, oData) {
					//el.innerHTML = '<button type="button" class="ui-button-small pure-button">...</button>';
					el.innerHTML = $('<button type="button" class="ui-button-small">' + _('Ver detalle') + '</button>').button({icons: {primary: "ui-icon-plus"}, text: false})[0].outerHTML;/*IDIOMAOK*/
				}
			});


			//	Se ha quitado el DataSource de ET_pacientes (ya no existe Endotools.pacientes.datasource)
			//	ahora se usa uno vacío (dummyDataSource)
			gestion_pacientes.datatable_results = new YAHOO.widget.ScrollingDataTable(
					"datatable_busqueda_result", fielddef, dummyDataSource,
					opciones_datatable
			);
			datatable_results = gestion_pacientes.datatable_results;
			controles.init_YUI_datatable(datatable_results, {m_inferior: 45, layoutPaneResizing: $(selector1).layout().panes.center});

			//	evento click en una fila de la tabla
			datatable_results.subscribe("rowClickEvent", function(oArgs) {
				if (!datatable_results.getRecord(oArgs.target)) return;	//	comprobar que la fila tiene record asignado (porque la fila con el mensaje 'no hay resultados' no tiene record y daria error)
				gestion_pacientes._seleccionar_row(oArgs.target);
			});

			//	boton de ver detalle de paciente... solo se usa con el nuevo layout
			datatable_results.subscribe("buttonClickEvent", function(oArgs) {
				if (!datatable_results.getRecord(oArgs.target)) return;
				gestion_pacientes._seleccionar_row(oArgs.target);
				gestion_pacientes.mostrar_paciente(null, true);
			});

			if (opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'IDUNICO' ||
				opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'IDUNICO+NHC' ||
				opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'NHC+IDUNICO') {
				$('#busqueda-pacientes-IDUNICO').show();
				$('#idunico-label2').show();
			}

			if (opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'NHC' ||
				opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'IDUNICO+NHC' ||
				opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'NHC+IDUNICO') {
				$('#busqueda-pacientes-NHC-CENTRO').show();
				$('#nhc-centro-label2').show();
			}

			if (opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'IDUNICO') {
				datatable_results.hideColumn("centros")
			}

			if (opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'NHC') {
				datatable_results.hideColumn("idunico")
			}

			//	boton buscar
			$("#buscar_pacientes_btn").click( function() {
				var params = {
					CIP:		$("#busqueda-pacientes-CIP").val(),
					DNI:		$("#busqueda-pacientes-dni").val(),
					nombre:		$("#busqueda-pacientes-nombre").val(),
					apellido1:	$("#busqueda-pacientes-apellido1").val(),
					apellido2:	$("#busqueda-pacientes-apellido2").val()
				}

				if ((opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'IDUNICO' ||
					opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'IDUNICO+NHC' ||
					opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'NHC+IDUNICO') &&
					$("#busqueda-pacientes-IDUNICO").val() !== '') {
					params["idunico"] = $("#busqueda-pacientes-IDUNICO").val()
				}

				if ((opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'NHC' ||
					opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'IDUNICO+NHC' ||
					opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'NHC+IDUNICO') &&
					$("#busqueda-pacientes-NHC-CENTRO").val() !== '') {
					params["centros"] = String(Endotools.auth.servicio_activo.centro_id) + ":" + $("#busqueda-pacientes-NHC-CENTRO").val()
				}

				for (var p in params) { if (params[p] == '') delete params[p]; }
				if (!$('#busqueda-pacientes-incl_deshab').is(':checked')) params.deshabilitado = '0';

				// PAGINACION
				// Paso 2: Set de parametros y asignacion de pagina que se va a pedir
				if (gestion_pacientes.paginacion){
					gestion_paginacion.set_params(params);
					params._pagina = gestion_paginacion.pagina_actual;
				}
				// < PAGINACION

				Endotools.pacientes.index(TM.content_pacientes.buscar, params, {datatable: datatable_results})
				.done(function(results){
					//reset de animacion de scroll, porque queda guardardo en algun lado
					anim = new YAHOO.util.Scroll(document.getElementsByClassName('yui-dt-bd')[0], { scroll: { to: [10000, 0] } },0.001);
					anim.animate();

					// >> PAGINACION - Crear html y eventos del paginador
					if (gestion_pacientes.paginacion){

						// PASO 3: Crear html del paginador
						gestion_paginacion.asignar_contenedores($("#paginacion"),$("#total"));
						gestion_paginacion.crear_paginador(); // crear html del paginador

						// PASO 4: Evento 1 - Click en el link del numero de pagina
						$("#paginacion a").bind("click",function(){
							gestion_paginacion.cambiar_pagina($(this));
							$("#buscar_pacientes_btn").click();
						});

						// PASO 5: Evento 2 - Cuando se presiona el enter en el input de la pagina actual
						$("#pagina-actual").bind("keydown",function(e){
							if (e.keyCode==13){
								gestion_paginacion.cambiar_pagina($(this));
								$("#buscar_pacientes_btn").click();
							}
						});
					// << PAGINACION
					}else{
						if ($("#total")) $("#total").html(results.length);
					}

					if (results && results.length == 0) {
						//no se ha encontrado ningun paciente
						Endotools.statusbar.mostrar_mensaje(_('No se ha encontrado ningún paciente'));/*IDIOMAOK*/
					} else {
						Endotools.statusbar.mostrar_mensaje(_('Listo'));/*IDIOMAOK*/
					}
				})
				.fail(function () {
					Endotools.statusbar.mostrar_mensaje(_('Error al cargar los pacientes'), 1);/*IDIOMAOK*/
				});
			});

			//	boton nuevo
			$("#nuevo_paciente_btn").click(gestion_pacientes.mostrar_nuevo);

			//	-----------------------------------
			Endotools.statusbar.mostrar_mensaje(_('Ready'));/*IDIOMAOK*/

			if (callback_fn) callback_fn();

			//	cuando se muestra la pantalla en un dialogo (desde gestion_agenda\dialogo_paciente.js)
			//	se tiene que actualizar el layout.
			$('.layout_main_content').layout().resizeAll();
		},

		cerrar: function() {
				//buscar_pacientes_btn.destroy();
				//nuevo_btn.destroy();
				if (gestion_pacientes.datatable_results) {
					gestion_pacientes.datatable_results.destroy();
					gestion_pacientes.datatable_results = null;
				}
		},

		mostrar_nuevo: function() {
			/*	Muestra un dialog para crear un paciente
			*/

			//	mostrar el dialog
			return controles.modal_dialog.mostrar({
				title: _('Nuevo paciente'), width: "780px", height: "auto",/*IDIOMAOK*/

				init: function(accept) {
					var $dialog = this;
					//	cargar el contenido
					return $.get("content/paciente.html"+ew_version_param())
					.done(function(htmldata) {
						$dialog.html(htmldata);
						gestion_pacientes._ini_form_paciente($dialog);
						if (opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'IDUNICO' ||
							opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'IDUNICO+NHC' ||
							opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'NHC+IDUNICO') {
							$('.paciente-idunico-group').show();
						}

						if (opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'NHC' ||
							opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'IDUNICO+NHC' ||
							opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'NHC+IDUNICO') {
							$('.paciente-nhc-group').show();
						}
					});
				}
				,check: function(){
					if (this.find('.paciente-idunico').val()=="" && opciones_config["PACIENTE.NHC_AUTOMATICO"]=="0"){
						alert(_("El " + opciones_config.IDUNICO_LABEL + " no puede estar vacio"));//OK
						return false;
					}else{
						return true;
					}
				}
				,result: function() {
					//	salva los valores que necesitará cuando se haya creado el paciente, y ya se haya
					//	destruido el dialog.

					var valores = {
						idunico:    this.find('.paciente-idunico').val(),
						DNI:		this.find('.paciente-dni').val(),
						CIP:		this.find('.paciente-cip').val(),
						nombre:		this.find('.paciente-nombre').val(),
						apellido1:	this.find('.paciente-apellido1').val(),
						apellido2:	this.find('.paciente-apellido2').val(),
						telefono1:  this.find('.paciente-telefono1').val(),
						telefono2:  this.find('.paciente-telefono2').val(),
						fechaNacimiento: this.find('.paciente-fecha_nacimiento').val(),
						aseguradora_id:	this.find('select.paciente-aseguradora').val(),
						numAfiliacion: this.find('.paciente-afiliacion').val(),
						aseguradora: {id: null, nombre:null},
						'centros': this.find('.paciente-nhc-centro').val()
					};

					if (valores.aseguradora_id){
						valores.aseguradora["id"] = valores.aseguradora_id;
						valores.aseguradora["nombre"] = this.find('select.paciente-aseguradora option[value="'+valores.aseguradora_id+'"]').text();
					}

					//	crear el paciente con los datos introducidos en el dialog
					gestion_pacientes.nuevo_paciente(TM.operaciones, this).done(function(paciente) {

						var historia = valores.historia;
						if (opciones_config["PACIENTE.NHC_AUTOMATICO"]=="1"){
							historia = paciente.id;
						}

						//	añadirlo al datatable y seleccionarlo
						valores["id"] = paciente.id;
						valores["historia"] = historia;
						datatable_results.addRow(valores);

						var rs = datatable_results.getRecordSet();
						gestion_pacientes._seleccionar_row(rs.getLength()-1);

						anim = new YAHOO.util.Scroll(document.getElementsByClassName('yui-dt-bd')[0], { scroll: { to: [0, 10000] } }, 0.01);
						anim.animate();
						$(gestion_pacientes.datatable_results.getRow(rs.getLength()-1)).effect("pulsate",{times:1}, 2000);
						anim=null;

					});
					return this;
				}
			});
		},


	}


}();
