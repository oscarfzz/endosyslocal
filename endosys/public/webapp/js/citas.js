var gestion_citas = function() {

	var datatable_results;
	var temporizador = null;
	var scroll_pos = 0;
	
	return {
	
		cita_id: null,
		paciente_id: null,
		idunico: null,
		tipo_exploracion_id: null,
		datatable_results: undefined,
		paciente: null,
		flag_estado: null,
		agendas: null,
		exploracion: null, // se guarda la exploracion de la cita seleccionada en el datatable
		sortedBy: null,

		_actualizar_agendas: function($agendas, agendas) {
			/*
			Actualiza el control select de agendas.
				agendas: devuelto por Endosys.usuarios.show()
			*/
			for (var i=0; i < agendas.length; i++) {
				// Solo crea las option del select de las agendas que pertenecen al servicio activo
				//	Si la agenda no tiene servicio_id también se añade... esto sirve para la integr. SIHGA, con las agendas_chus
				if (agendas[i].servicio_id == undefined  ||  agendas[i].servicio_id == null  ||
				    (parseInt(agendas[i].servicio_id,10) == parseInt(Endosys.auth.servicio_activo.id,10))) {
						var id =		agendas[i].id;
						var nombre =	agendas[i].nombre;
						var op =		$('<option value="' + id + '">' + nombre + '</option>');
						if (agendas.length == 1) op.attr('selected', '');	//	si solo hay una, seleccionarla
						$agendas.append(op);
				}
			}
			/*PROV
			if ($agendas.data("selectBox-selectBoxIt")) $agendas.selectBoxIt('refresh');	*///	Si es un selectBoxIt hace el refresh
		},
		
		mostrar: function(callback_fn) {
				// Limpia la informacion de gestion_citas
				gestion_citas.cita_id = null;
				gestion_citas.tipo_exploracion_id = null;
				gestion_citas.paciente_id = null;
				gestion_citas.paciente = null;
				gestion_citas.idunico = null;
				gestion_citas.estado = null;

				TM.content_citas.activate();
				TM.content_citas.agendas_chus.activate();
				//TM.content_citas.servicios.activate();
				TM.content_citas.agendas.activate();
				TM.content_citas.detalles.activate();
				Endosys.statusbar.mostrar_mensaje(_('Loading...'));/*IDIOMAOK*/

				// Carga la grilla de citas
				TM.content_citas.load_content(mainlayout, 'content/lista_citas.html'+ew_version_param())
				.done(function() {
				
					var north_size = 275;
					// desactiva el input de nhc paciente si la clave CITAS_PENDIENTES_BUSQUEDA_POR_HISTORIA
					//alert(!opciones_config.CITAS_PENDIENTES_BUSQUEDA_POR_HISTORIA);
					if (!parseInt(opciones_config.CITAS_PENDIENTES_BUSQUEDA_POR_HISTORIA,10)){
						$("#id-unico-paciente").hide();
						$("#checkbox-fecha").hide();
						north_size = 210;
					}
					
					// desactivar el input de NHC paciente ya que no se usa
					// XXX esta linea se saco por que ahora se puede desactivar mediante clave: CITAS_PENDIENTES_BUSQUEDA_POR_HISTORIA
					// if (opciones_config.INTEGRACION_SIHGA) $('#busqueda-id-unico-paciente').parent().hide();
					
					$('.layout_main_content').layout({
						west__size:	275,
						//spacing_closed:		10,
						slideTrigger_open:	"click",
						initClosed:			false,
						resizable:			false
					});
					$('.contenedor2').layout({
						north__size:	north_size,	//	Para SIHGA hacer algo más pequeño el panel
						resizable:		false,
						slidable:		false,
						closable:		false,						
					});		


					/* Muestra el boton imprimir */
					$("#imprimir-citas-btn").button();

		
					//	configurar la busqueda de citas
					//	--------------------------------

					fielddef = gestion_citas.configurar_columnas();
					gestion_citas.datatable_results = new YAHOO.widget.ScrollingDataTable("datatable_busqueda_result",
																		fielddef,
																		//Endosys.citas.datasource,
																		dummyDataSource,	//	en util/misc.js
																		{ initialLoad: false,
																		  //formatRow:		rowFormatter,
																		  MSG_EMPTY: '<em>' + _('No se ha encontrado ninguna cita') + '</em>',/*IDIOMAOK*/
																		  height:			"200px",
																		  width: "100%"
																		});
																		
					datatable_results = gestion_citas.datatable_results;					
					controles.init_YUI_datatable(datatable_results, {layoutPaneResizing: $('.layout_main_content').layout().panes.center});

					//	columnas 'calculadas' (que no se extraen directamente de los campos devueltos por el datasource)
					datatable_results.doBeforeLoadData = function (sRequest, oResponse, oPayload) {
						var centro_id = Endosys.auth.servicio_activo.centro_id;
						for (var n=0; n < oResponse.results.length; n++) {
							oResponse.results[n].paciente_id =	oResponse.results[n].paciente.id;
							oResponse.results[n].idunico =		oResponse.results[n].paciente.idunico;
							oResponse.results[n].nhc_centro =  	"";
							for(var i=0; i < oResponse.results[n].paciente.centros.length; i++) {
								if(oResponse.results[n].paciente.centros[i].id = centro_id) {
									oResponse.results[n].nhc_centro =	oResponse.results[n].paciente.centros[i].nhc;
									break;
								}
							}
							oResponse.results[n].cip =			oResponse.results[n].paciente.CIP;
							oResponse.results[n].nombre =		oResponse.results[n].paciente.nombre;
							oResponse.results[n].apellido1 =	oResponse.results[n].paciente.apellido1;
							oResponse.results[n].apellido2 =	oResponse.results[n].paciente.apellido2;
							oResponse.results[n].fechaNacimiento =		oResponse.results[n].paciente.fechaNacimiento;
							//siempre calcula la edad en base a la fecha de nacimiento.
							oResponse.results[n].edad = calcular_edad(oResponse.results[n].paciente.fechaNacimiento);
							
							oResponse.results[n].paciente =		(oResponse.results[n].nombre || "" ) + ' ' +
																(oResponse.results[n].apellido1 || "" ) + ' ' +
																(oResponse.results[n].apellido2 || "" );
							
							
							if (oResponse.results[n].exploracion && oResponse.results[n].exploracion.estado != '2'){
								oResponse.results[n].medico_realizado_cita = oResponse.results[n].exploracion.medico.nombre;
							}else{
								oResponse.results[n].medico_realizado_cita = null;
							}
							
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
								oResponse.results[n].medico =		oResponse.results[n].medico.nombre;
							else
								oResponse.results[n].medico = null;
								
							if (oResponse.results[n].ex) {
								oResponse.results[n].agenda_cod = oResponse.results[n].ex.agenda_cod;
								oResponse.results[n].agenda_descr = oResponse.results[n].ex.agenda_descr;
								oResponse.results[n].prestacion_cod = oResponse.results[n].ex.prestacion_cod;
								oResponse.results[n].prestacion_descr = oResponse.results[n].ex.prestacion_descr;
							} else {
								oResponse.results[n].agenda_cod = null;
								oResponse.results[n].agenda_descr = null;
								oResponse.results[n].prestacion_cod = null;
								oResponse.results[n].prestacion_descr = null;
							}
							
							if (oResponse.results[n].info) {
								oResponse.results[n].codigo_prestacion = oResponse.results[n].info.codigo_prestacion;
								oResponse.results[n].descripcion_prestacion = oResponse.results[n].info.descripcion_prestacion;
							} else {
								oResponse.results[n].codigo_prestacion = null;
								oResponse.results[n].descripcion_prestacion = null;
							}

							//Datos del worklist
							if (oResponse.results[n].work){
								if (oResponse.results[n].work.schProcStepLoc){
									oResponse.results[n].mwl_schProcStepLoc = oResponse.results[n].work.schProcStepLoc;
								}else{
									oResponse.results[n].mwl_schProcStepLoc = null;
								}

								if (oResponse.results[n].work.accessionNumber){
									oResponse.results[n].mwl_accessionNumber = oResponse.results[n].work.accessionNumber;
								}else{
									oResponse.results[n].mwl_accessionNumber = null;
								}

								if (oResponse.results[n].work.studyInstanceUID){
									oResponse.results[n].mwl_studyInstanceUID = oResponse.results[n].work.studyInstanceUID;
								}else{
									oResponse.results[n].mwl_studyInstanceUID = null;
								}

								if (oResponse.results[n].work.schProcStepID){
									oResponse.results[n].mwl_schProcStepID = oResponse.results[n].work.schProcStepID;
								}else{
									oResponse.results[n].mwl_schProcStepID = null;
								}

								if (oResponse.results[n].work.schProcStepDescription){
									oResponse.results[n].mwl_schProcStepDescription = oResponse.results[n].work.schProcStepDescription;
								}else{
									oResponse.results[n].mwl_schProcStepDescription = null;
								}

								if (oResponse.results[n].work.reqProcedurePriority){
									oResponse.results[n].mwl_reqProcedurePriority = oResponse.results[n].work.reqProcedurePriority;
								}else{
									oResponse.results[n].mwl_reqProcedurePriority = null;
								}

								if (oResponse.results[n].work.patientLocation){
									oResponse.results[n].mwl_patientLocation = oResponse.results[n].work.patientLocation;
								}else{
									oResponse.results[n].mwl_patientLocation = null;
								}

								if (oResponse.results[n].work.admissionID){
									oResponse.results[n].mwl_admissionID = oResponse.results[n].work.admissionID;
								}else{
									oResponse.results[n].mwl_admissionID = null;
								}

								if (oResponse.results[n].work.reqService){
									oResponse.results[n].mwl_reqService = oResponse.results[n].work.reqService;
								}else{
									oResponse.results[n].mwl_reqService = null;
								}

								if (oResponse.results[n].work.refPhysicianName){
									oResponse.results[n].mwl_refPhysicianName = oResponse.results[n].work.refPhysicianName;
								}else{
									oResponse.results[n].mwl_refPhysicianName = null;
								}

								if (oResponse.results[n].work.reqPhysician){
									oResponse.results[n].mwl_reqPhysician = oResponse.results[n].work.reqPhysician;
								}else{
									oResponse.results[n].mwl_reqPhysician = null;
								}

								if (oResponse.results[n].work.schStationName){
									oResponse.results[n].mwl_schStationName = oResponse.results[n].work.schStationName;
								}else{
									oResponse.results[n].mwl_schStationName = null;
								}

								if (oResponse.results[n].work.schPerfPhysicianName){
									oResponse.results[n].mwl_schPerfPhysicianName = oResponse.results[n].work.schPerfPhysicianName;
								}else{
									oResponse.results[n].mwl_schPerfPhysicianName = null;
								}

								if (oResponse.results[n].work.schStationAETitle){
									oResponse.results[n].mwl_schStationAETitlee = oResponse.results[n].work.schStationAETitle;
								}else{
									oResponse.results[n].mwl_schStationAETitle = null;
								}

							}

							// Obtiene el campo string y lo convierte a tipo Date de javascript.
							// fecha de la cita
							if (oResponse.results[n].fecha){
								var aFecha = oResponse.results[n].fecha.split("/");
								oResponse.results[n].fecha = new Date(aFecha[2],parseInt(aFecha[1],10)-1,aFecha[0],0,0,0);
							}
							// fechaNacimiento
							if (oResponse.results[n].fechaNacimiento){
								var aFechaNac = oResponse.results[n].fechaNacimiento.split("/");
								oResponse.results[n].fechaNacimiento = new Date(aFechaNac[2],parseInt(aFechaNac[1],10)-1,aFechaNac[0],0,0,0);
							}

						}
						
						return true;
					};
					 
					datatable_results.subscribe("initEvent", function(oArgs) {
						// configurar el orden que tenia anteriormente
						var dir_class = YAHOO.widget.DataTable.CLASS_ASC;
						if (gestion_citas.sortedBy!=null){
							var dir = gestion_citas.sortedBy.dir.split("-")[2];
							if (dir == "desc"){
								dir_class = YAHOO.widget.DataTable.CLASS_DESC;
							}
							gestion_citas.datatable_results.sortColumn(gestion_citas.datatable_results.getColumn(gestion_citas.sortedBy.key), dir_class);
						}else{
							if (opciones_config.COLUMNAS_CITAS.indexOf('flag_estado')!=-1){
								gestion_citas.datatable_results.sortColumn(gestion_citas.datatable_results.getColumn("flag_estado"),dir_class);	
							}
						}
					});
					
					//	evento click en una fila de la tabla
					datatable_results.subscribe("rowClickEvent", function(oArgs) {
						this.unselectAllRows();
						this.selectRow(oArgs.target);
						this.clearTextSelection();
						var data =  datatable_results.getRecord(oArgs.target).getData();
						gestion_citas.procesar_seleccionar_row(data);
					});

					datatable_results.subscribe("buttonClickEvent", function(oArgs) {
						var record = datatable_results.getRecord(oArgs.target);
						var cita_id = record.getData("id");
						controles.confirm_dialog(_('Cancelar cita'), _('¿Está seguro de que desea no realizar la cita? ya no se volverá a mostrar en este listado.'),/*IDIOMAOK*/
							function() {
							
								var _do_cancelar = function(motivo_cancelacion) {
									var params = {cancelada: '1'};
									if (motivo_cancelacion) {
										params.motivo_id = motivo_cancelacion;
									}

									Endosys.citas.update(TM.operaciones, cita_id, params)
									.done(function() {
										//	quitarla del datatable
										if(opciones_config.CITAS_PENDIENTES_MODO == 0){
											datatable_results.deleteRow(record);
										}else{
											$("#busqueda-buscar-btn").click();	
										}
										
									})
									.fail(function() {
										//En este fail se puede diferenciar si no se ha podido cancelar por:
										//1. ya estaba cancelada
										//2. se habia iniciado la exploracion
										Endosys.statusbar.mostrar_mensaje(_('La cita no se puede cancelar'), 1);/*IDIOMAOK*/
										
									});
								}
							
								if (opciones_config.USAR_MOTIVO_CANCELACION) {
									motivo_cancelacion_dialog.mostrar()
									.done(function(motivo_cancelacion) {
										if (motivo_cancelacion == null) {
											Endosys.statusbar.mostrar_mensaje(_('No ha seleccionado un motivo de cancelación'), 1);/*IDIOMAOK*/
										} else {
											_do_cancelar(motivo_cancelacion);
										}
									});
								} else {
									_do_cancelar();
								}
							
						});
					});


					// Inicializando datepicker con la fecha actual
					$("#busqueda-fecha").flatpickr({
						defaultDate: new Date(),
						dateFormat: "d-m-Y",
					});

					
					//	boton buscar
					$("#busqueda-buscar-btn").button().click(function() {
						var params = {};
						if(opciones_config.CITAS_PENDIENTES_MODO == 0){
							//FORMA ANTIGUA DE FUNCIONAR
							params = {
								exploracion_id:	'',	//	buscar las citas que no tienen expl. asignada, es decir, no realizadas
								cancelada:		'0'	//	y que no estén canceladas
							};
						}

						// accion del boton imprimir
						$("#imprimir-citas-btn").off().click(function() {
							dia_seleccionado = $("#busqueda-fecha").val();
							agenda_seleccionada = $('#busqueda-citas-agenda option[value="'+$("#busqueda-citas-agenda").val()+'"]').text()

							var opciones = {titulo: _("Citas del ")+ dia_seleccionado + " - " + agenda_seleccionada}
							gestion_imprimir.imprimir_con_dialog(opciones);
						});

						

						//>>> Set de parametros de busqueda
						if ($("#checkbox-id-unico-paciente").prop("checked")){
							if ($("#busqueda-id-unico-paciente").val()!=""){
								params.id_unico_paciente = $("#busqueda-id-unico-paciente").val();	
							}else{
								//si esta seleccionado id-uncio-paciente pero no tiene ningun valor, 
								//automaticamente se selecciona checkbox fecha y se deselecciona
								//checkbox id-unico-paciente para que busque por fechas y no genere una 
								//busqueda de todas las citas del sistema
								$("#checkbox-fecha").prop("checked",true).trigger("change");
								$("#checkbox-id-unico-paciente").prop("checked",false).trigger("change");
							}	
						}
						if ($("#checkbox-fecha").prop("checked")){
							params.fecha = $("#busqueda-fecha").val();	
						}
						//<<<
						
						//	si no es la integración de CHUS, usar las agendas estandar
						//	de endosys.
						var $agenda = $("#busqueda-citas-agenda");
						if ($agenda.val())
							params.agenda_id = $agenda.val();
						//	NO PERMITIR SIN AGENDA
						if (!params.agenda_id) {
							alert(_('Debe seleccionar una agenda'));/*IDIOMAOK*/
							return;
						}
						
						//	en integración SIHGA, el param es "_agenda_id", no "agenda_id"
						if (opciones_config.INTEGRACION_SIHGA) {
							params._agenda_id = params.agenda_id;
							delete params.agenda_id;
						}
							
						// Grabar el orden
						gestion_citas.sortedBy = gestion_citas.datatable_results.getState().sortedBy;
						
						Endosys.citas.index(TM.buscar_citas, params, {datatable: datatable_results})
						.done(function(results){
							if (results && results.length == 0){
								//no se ha encontrado ninguna cita
								Endosys.statusbar.mostrar_mensaje(_('No se ha encontrado ninguna cita'));/*IDIOMAOK*/
							}else{
								Endosys.statusbar.mostrar_mensaje(_('Ready'));/*IDIOMAOK*/

								//mostrar/ocultar columna fecha segun el tipo de busqueda que se hizo
								if ($("#checkbox-fecha").prop("checked")){
									datatable_results.hideColumn("fecha");	
								}else{
									datatable_results.showColumn("fecha");
								}

							}

							// seleccionar la cita que se selecciono anteriormente
							if (gestion_citas.cita_id!=null){
								//buscar y seleccionar la cita en el datatable

								for (var n=0; n < gestion_citas.datatable_results.getRecordSet().getLength(); n++) {
									row = gestion_citas.datatable_results.getRecordSet().getRecord(n);
									if (row.getData().id.toString() == gestion_citas.cita_id.toString()){
										datatable_results.unselectAllRows();
										datatable_results.selectRow(row);
										datatable_results.clearTextSelection();
										gestion_citas.procesar_seleccionar_row(row.getData());
									}
								}

							}

							/*if(arguments[2].status && arguments[2].status == 404){
							//no se ha encontrado ninguna cita
								Endosys.statusbar.mostrar_mensaje("No se han encontrado ninguna Cita");
							}*/
								
						})
						.then(function(){
							if(scroll_pos > 0) {
								anim = new YAHOO.util.Scroll(document.getElementsByClassName('yui-dt-bd')[0], { scroll: { to: [0, scroll_pos] } },0.001);
								anim.animate();
								scroll_pos = 0;
							}
						})
						.fail(function(jqXHR, textStatus, errorThrown) { 
							if (textStatus!="abort"){
								// solo muestra el mensaje de error si no es un abort
								if (jqXHR.responseText){
									error = parseError(jqXHR.responseText);
									Endosys.statusbar.mostrar_mensaje(error, 1);
								}else{
									Endosys.statusbar.mostrar_mensaje(_('Error al cargar las citas'), 1);/*IDIOMAOK*/
								}
							}
						});
					});
						
					//	CONTROL SELECCION AGENDA
					
					//		dewsactivarlo al principio, y cuando esté lleno activarlo
					$('#busqueda-citas-agenda').attr('disabled', 'disabled');
					
					//		Solo usar el selectBoxIt si no es SIHGA, ya que en ese caso los listados de agenda son largos y no se muestran bien...
					// PROV
					/*if (!opciones_config.INTEGRACION_SIHGA)
						$('#busqueda-citas-agenda').selectBoxIt({
							copyClasses: "container",	//	necesario para aplicar el estilo
							autoWidth:	false,
							theme:		"jqueryui"
						});*/
					
					//		llenarlo
					if (opciones_config.INTEGRACION_SIHGA) {
						Endosys.agendas_chus.index(TM.content_citas.agendas_chus)
						
						.done(function(agendas) {
							gestion_citas.agendas = agendas;
							var $control = $('#busqueda-citas-agenda');
							gestion_citas._actualizar_agendas($control, gestion_citas.agendas);
							$control.removeAttr('disabled');
							//PROV
							/*if ($control.data("selectBox-selectBoxIt"))
								$control.selectBoxIt('refresh');	*/
								
							/*var items = [];
							for (var n=0; n < agendas.length; n++) {
								var elemento = agendas[n];
								items.push({
									text: elemento.nombre,
									value: elemento.id
								});
							}
							agendas_chus_menubtn.getMenu().itemData = items;
							agendas_chus_menubtn.set('disabled', false);*/
						})
						
						.fail(function() {
							Endosys.statusbar.mostrar_mensaje(_('Ha ocurrido un error obteniendo las agendas'), 1);/*IDIOMAOK*/
						});
						
					} else {
						Endosys.usuarios.show(TM.content_citas.agendas, Endosys.auth.username)

						.then(function(usuario) {
							//almacena las agendas del medico actual
							gestion_citas.agendas = usuario.medico.agendas;
							return Endosys.valores_default.show(TM.operaciones, 'index')
						})
						
						.done(function(valores_default) {
							//obtener el servicio activo, y crea el select de agendas segun el servicio activo
							if (Endosys.auth.servicio_activo!=null){
								gestion_citas.servicio_id = valores_default.servicio_id;
								gestion_citas._actualizar_agendas($("#busqueda-citas-agenda"), gestion_citas.agendas);
								$("#busqueda-citas-agenda").removeAttr('disabled');
							}

							//	realizar busqueda automaticamente una vez se han recuperado
							//	los valores por defecto, para saber la agenda
							if (valores_default.agenda_id) {
								var $agendas = $("#busqueda-citas-agenda");
								var op = $agendas.find('option[value="' + valores_default.agenda_id + '"]')
								if (op) {
									$agendas.find('option').removeAttr('selected');
									op.attr('selected', '');
									//PROV
									/*if ($agendas.data("selectBox-selectBoxIt")) $agendas.selectBoxIt('refresh');	*///	Si es un selectBoxIt hace el refresh
								}
							}
							$("#busqueda-buscar-btn").click();
						});
					}
					
					//CITAS_PENDIENTES_REFRESCO
					if(opciones_config.CITAS_PENDIENTES_REFRESCO >= 1000 ){
						temporizador =setInterval(function () {
						    scroll_pos = $(".yui-dt-bd").scrollTop();
						    $("#busqueda-buscar-btn").click();
						}, opciones_config.CITAS_PENDIENTES_REFRESCO);
					}

					if(opciones_config.IDENTIFICADORES_PACIENTE == "NHC" ||
					   opciones_config.IDENTIFICADORES_PACIENTE == "NHC+IDUNICO"){
						$("#label-citas-id-unico-paciente").text(_('NHC'));
					} else {
						$("#label-citas-id-unico-paciente").text(opciones_config.IDUNICO_LABEL);
					}

					//Control de los checkbox para que al menos uno quede seleccionado
					$(".checkbox_citas").on("change",function(){
						var check = $(this);
						if (gestion_citas._no_hay_seleccionados()){
							check.prop("checked", true);
						}
						if (check.prop("checked")){
							check.parent().next().css('color','black');
						}else{
							check.parent().next().css('color','gray');
						}
					});

					/*>>> Seleccion automatica cuando se hace foco en el input text
					      y deseleccion automatica si se va del foco y no tiene contenido (siempre
					      que no sea el unico seleccinado)
					*/
					$("#busqueda-id-unico-paciente").on("focusin",function(){
						var check = $("#checkbox-id-unico-paciente");
						check.prop("checked", true).trigger("change");
					});
					$("#busqueda-id-unico-paciente").on("focusout",function(){
						var check = $("#checkbox-id-unico-paciente");
						if ($(this).val()=="" && $("#checkbox-fecha").prop("checked")==true){
							check.prop("checked", false).trigger("change");
						}
					});
					$("#busqueda-fecha").on("focusin",function(){
						var check = $("#checkbox-fecha");
						check.prop("checked", true).trigger("change");
					});
					$("#busqueda-fecha").on("focusout",function(){
						var check = $("#checkbox-fecha");
						if ($(this).val()=="" && $("#checkbox-id-unico-paciente").prop("checked")==true){
							check.prop("checked", false).trigger("change");
						}
					});
					//<<<

					if (callback_fn) callback_fn();
				});

		},

		procesar_seleccionar_row: function(data){
			
			gestion_citas.cita_id =				data.id;							
			gestion_citas.tipo_exploracion_id =	data.tipoexploracion_id;
			gestion_citas.paciente_id =			data.paciente_id;
			gestion_citas.idunico =             data.idunico;
			gestion_citas.paciente =			(data.nombre || "" ) + " " + (data.apellido1 || "" ) + " " + (data.apellido2 || "" );
			if (data.exploracion!=undefined){
				gestion_citas.exploracion = data.exploracion;
				gestion_citas.medico_id_exploracion = data.exploracion.medico.id;
			}else{
				gestion_citas.exploracion = null;
				gestion_citas.medico_id_exploracion = null;
			}
			
			if (data.flag_estado){
				gestion_citas.flag_estado = data.flag_estado;
			}
			nueva_exploracion.set_continuar_seleccion_cita();		
		},
		
		//retorna true si no hay checkbox seleccionados
		_no_hay_seleccionados: function(){

			var checks = $(".checkbox_citas");
			var cantidad = 0;
			//recorre todos los checkbox y suma si esta seleccionado
			checks.each(function(){
				if ($(this).prop("checked")){
					cantidad += 1;
				}
			});

			if (cantidad==0){
				return true;
			}else{
				return false;
			}

		},

		cerrar: function() {
				//$("#busqueda-citas-agenda").multiselect('destroy');	//	XXX	importante!!!
				//PROV
				/*
				if ($("#busqueda-citas-agenda").data("selectBox-selectBoxIt"))
					$("#busqueda-citas-agenda").selectBoxIt('destroy');	*///	Si es un selectBoxIt hace el destroy

				if (gestion_citas.datatable_results) {
					gestion_citas.datatable_results.destroy();
					gestion_citas.datatable_results = null;
				}
				clearInterval(temporizador);
				temporizador = null;
				scroll_pos = 0;
		},
		
		configurar_columnas: function() {
			/*	Configura las columnas a mostrar en la lista de citas pendientes. Esta configuración se obtiene
				de la opción "COLUMNAS_CITAS" de "opciones_config", que en el servidor se configura en el
				archivo "development.ini".
				Esta opción contiene los nombres de las columnas en el orden deseado y separados por comas.
				Si no se indica esta opción, por defecto se muestran estas columnas:
				idunico,paciente,hora,prioridad,[descripcion_prestacion,codigo_prestacion|tipoexploracion],observaciones,[button]
				
				XXX
				debido a que habia dos formas de recibir la prestacion (en INFO y en EX), la correcta
				actualmente (EX) se mantiene con los nombres indicados, y los anteriores (INFO) tienen estos
				nombres: _descripcion_prestacion, _codigo_prestacion				
			*/
			
			//	Formatear el valor de las prioridades
			/*var prioridad_formatter = function(elLiner, oRecord, oColumn, oData) {
					elLiner.innerHTML = Endosys.citas.descr_prioridad(oData);
			}*/
			
			//	formatear el botón de "No realizada"
			var formatNoRealizadaBtn = function(el, oRecord, oColumn, oData) {
				/*var caption = 'No realizada';
				el.innerHTML = "<button type=\"button\" class=\"" + YAHOO.widget.DataTable.CLASS_BUTTON + "\">" + caption + "</button>";*/
				//solo pintar el boton de cancelar en aquellas citas con estado pendiente o para el metodo antiguo que siempre son las pendientes
				if((oRecord.getData('flag_estado') && oRecord.getData('flag_estado') == '00') || opciones_config.CITAS_PENDIENTES_MODO == 0 ) {
					el.innerHTML = $('<button type="button" class="ui-button-small">' + _('No realizada') + '</button>'/*IDIOMA*/).button({icons: {primary: "ui-icon-close"}, text: false})[0].outerHTML;
				}		
			}

			var pintar_estado = function(elLiner, oRecord, oColumn, oData) { 
				
				
				if (oRecord.getData('exploracion_id')){
					if(oRecord.getData('exploracion')){
						//la cita tiene una exploracion asignada								
						var estado_expl = oRecord.getData('exploracion').estado;
						var borrado = oRecord.getData('exploracion').borrado;
						if (borrado === "sí") {
							$(elLiner.parentNode.parentNode).addClass('cita-inactiva');
							$(elLiner.parentNode).addClass('cita-cancelada');
							$(elLiner.parentNode).attr('title', _('Exploración borrada'));
							oRecord.setData("flag_estado","04");
						}
						else if(estado_expl == "0"){
							//cita iniciada
							//exploración asignada + estado exploración 0 = cita iniciada
							if (oRecord.getData('exploracion').medico.id!= userinfo.get_usuario().medico.id)
							{
								$(elLiner.parentNode.parentNode).addClass('cita-inactiva');
							}
							$(elLiner.parentNode).addClass('cita-iniciada');
							$(elLiner.parentNode).attr('title', _('En curso'));	/*IDIOMAOK*/						
							//$(elLiner).html("01");
							oRecord.setData("flag_estado","01");
														
						
						}else if(estado_expl == "1") {
							//cita finalizada
							//exploración asignada + estado exploración 1 = cita finalizada
							$(elLiner.parentNode.parentNode).addClass('cita-inactiva');
							$(elLiner.parentNode).addClass('cita-realizada');
							$(elLiner.parentNode).attr('title', _('Finalizada'));	/*IDIOMAOK*/	
							//$(elLiner).html("02");
							oRecord.setData("flag_estado","02");
						
						}else if (estado_expl == "2") {
							//cita candelada
							//exploración asignada + estado exploración 2 = exploracion cancelada y por consiguiente cita cancelada (se representan igual)
							$(elLiner.parentNode.parentNode).addClass('cita-inactiva');
							$(elLiner.parentNode).addClass('cita-cancelada');
							$(elLiner.parentNode).attr('title', _('Cancelada'));	/*IDIOMAOK*/	
							//$(elLiner).html("03");
							oRecord.setData("flag_estado","03");
						
						}
					
					}
					
				
				}else if(oRecord.getData('cancelada')){
					$(elLiner.parentNode.parentNode).addClass('cita-inactiva');
					$(elLiner.parentNode).addClass('cita-cancelada');	
					$(elLiner.parentNode).attr('title', _('Cancelada'));	/*IDIOMAOK*/	
					//$(elLiner).html("03");											
					oRecord.setData("flag_estado","03");
				}
				else{
					$(elLiner.parentNode).addClass('cita-pendiente');
					$(elLiner.parentNode).attr('title', _('Pendiente'));	/*IDIOMAOK*/	
					//$(elLiner).html("00");
					oRecord.setData("flag_estado","00");

				}

			};

			// Configurarle el data locale al YUI para usarlo en el formatter
			YAHOO.util.DateLocale["es-ES"] = YAHOO.lang.merge(YAHOO.util.DateLocale, {x:"%d/%m/%Y"});

			//funcion que aplica el formateo de la fecha
			var formatterDate = function(container, record, column, data) {
        		container.innerHTML = YAHOO.util.Date.format(data, {format:"%x"}, "es-ES");
    		};
			//defaultDir:YAHOO.widget.DataTable.CLASS_ASC
			var defs = {
				flag_estado:				{key:"flag_estado", label: '',	width: 'auto',formatter: pintar_estado,  sortable:true},
				fecha:						{key: 'fecha',		label: _('Fecha'),	width: 80,	resizeable: true,formatter: formatterDate,	sortable: true},/*IDIOMAOK*/
				idunico:					{key: 'idunico',		label: opciones_config.IDUNICO_LABEL, width: 100, resizeable: true, sortable: true},
				nhc_centro:         		{key: 'nhc_centro',		label: _('NHC'), width: 100, resizeable: true, sortable: true},
				cip:						{key: 'cip',			label: opciones_config.CIP_LABEL, width: 100, resizeable: true, sortable: true},
				paciente:					{key: 'paciente',		label: _('Paciente'),	width: 150,	resizeable: true,	sortable: true},/*IDIOMAOK*/
				nombre:						{key: 'nombre',		label: _('Paciente:Nombre'),	width: 150,	resizeable: true,	sortable: true},/*IDIOMAOK*/			
				apellido1:					{key: 'apellido1',		label: _('Paciente:html:1er apellido'),	width: 150,	resizeable: true,	sortable: true},/*IDIOMAOK*/
				apellido2:					{key: 'apellido2',		label: _('Paciente:html:2o apellido'),	width: 150,	resizeable: true,	sortable: true},/*IDIOMAOK*/
				fechaNacimiento:			{key: 'fechaNacimiento',		label: _('Nacimiento'),	width: 90,	formatter: formatterDate,	resizeable: true,	sortable: true},/*IDIOMAOK*/
				edad:						{key: 'edad',		label: _('Edad'),	width: 45,	resizeable: true,	sortable: true},/*IDIOMAOK*/
				tipoexploracion:			{key: 'tipoexploracion', label: _('Abrev:Tipo exploracion'), width: 80, resizeable: true,	sortable: true},/*IDIOMAOK*/
				hora:						{key: 'hora',			label: _('Time:Hora'),		width: 60,	resizeable: true,	sortable: true},/*IDIOMAOK*/
				prioridad:					{key: 'prioridad',		label: _('Prioridad'),	width: 70,	resizeable: true,	sortable: true},/*IDIOMAOK*/
				mwl_reqProcedurePriority:	{key: 'mwl_reqProcedurePriority', label: _('Prioridad'),	width: 70,	resizeable: true,	sortable: true},/*IDIOMAOK*/
				sala:						{key: 'sala',			label: _('Sala'),		width: 80,	resizeable: true,	sortable: true},/*IDIOMAOK*/
				mwl_schProcStepLoc:    		{key: 'mwl_schProcStepLoc',		label: _('Sala'),		width: 80,	resizeable: true,	sortable: true},/*IDIOMAOK*/
				mwl_schStationName:    		{key: 'mwl_schStationName',		label: _('Sala'),		width: 80,	resizeable: true,	sortable: true},/*IDIOMAOK*/
				mwl_schStationAETitle:    	{key: 'mwl_schStationAETitle',		label: _('Sala'),		width: 80,	resizeable: true,	sortable: true},/*IDIOMAOK*/
				agenda_cod:					{key: 'agenda_cod',		label: _('Agenda'),	width: 50,	resizeable: true,	sortable: true},/*IDIOMAOK*/
				agenda_descr:				{key: 'agenda_descr',	label: _('Agenda'),	width: 80,	resizeable: true,	sortable: true},/*IDIOMAOK*/
				medico:						{key: 'medico',			label: _('Médico'),	width: 150,	resizeable: true,	sortable: true},/*IDIOMAOK*/
				mwl_mwl_schPerfPhysicianName:{key: 'mwl_schPerfPhysicianName',			label: _('Médico'),	width: 150,	resizeable: true,	sortable: true},/*IDIOMAOK*/
				mwl_reqService:				{key: 'mwl_reqService',		label: _('Servicio Peticionario'),	width: 150,	resizeable: true,	sortable: true},/*IDIOMAOK*/
				mwl_refPhysicianName:		{key: 'mwl_refPhysicianName',	label: _('Médico Peticionario'),	width: 150,	resizeable: true,	sortable: true},/*IDIOMAOK*/
				mwl_reqPhysician:			{key: 'mwl_reqPhysician',		label: _('Médico Peticionario'),	width: 150,	resizeable: true,	sortable: true},/*IDIOMAOK*/
				cancelada:					{key: 'cancelada',		label: _('Cancelada'),	width: 70,	resizeable: true,	sortable: true},/*IDIOMAOK*/
				observaciones:				{key: 'observaciones', 	label: _('Observaciones'), width: 150, resizeable: true, sortable: true},/*IDIOMAOK*/
				_codigo_prestacion:			{key: 'codigo_prestacion', 		label: _('Abrev:Código'),		 width: 50,	 resizeable: true, sortable: true},/*IDIOMAOK*/
				_descripcion_prestacion: 	{key: 'descripcion_prestacion', label: _('Prestación'), width: 150, resizeable: true, sortable: true},/*IDIOMAOK*/
				codigo_prestacion:			{key: 'prestacion_cod', 		label: _('Abrev:Código'),		 width: 50,	 resizeable: true, sortable: true},/*IDIOMAOK*/
				descripcion_prestacion: 	{key: 'prestacion_descr',		label: _('Prestación'), width: 150, resizeable: true, sortable: true},/*IDIOMAOK*/
				mwl_schProcStepID:			{key: 'mwl_schProcStepID', 		label: _('Abrev:Código'),		 width: 50,	 resizeable: true, sortable: true},/*IDIOMAOK*/
				mwl_schProcStepDescription: {key: 'mwl_schProcStepDescription',		label: _('Prestación'), width: 150, resizeable: true, sortable: true},/*IDIOMAOK*/
				mwl_patientLocation: 		{key: 'mwl_patientLocation',		label: _('Ubicación del Paciente'), width: 150, resizeable: true, sortable: true},/*IDIOMAOK*/
				mwl_admissionID: 			{key: 'mwl_admissionID',		label: _('ID Admisión'), width: 150, resizeable: true, sortable: true},/*IDIOMAOK*/
				mwl_accessionNumber: 			{key: 'mwl_accessionNumber',		label: _('Accession Number'), width: 150, resizeable: true, sortable: true},/*IDIOMAOK*/
				mwl_studyInstanceUID: 			{key: 'mwl_studyInstanceUID',		label: _('Study Instance UID'), width: 150, resizeable: true, sortable: true},/*IDIOMAOK*/
				medico_realizado_cita: {key: 'medico_realizado_cita',		label: _('Realizada por'), width: 150, resizeable: true, sortable: true},/*IDIOMAOK*/
				button:				{key: 'button',			label: '',			width: 'auto',	formatter: formatNoRealizadaBtn}
			};
			
			var columnas_citas = '';

			if (opciones_config.COLUMNAS_CITAS) {
				columnas_citas = opciones_config.COLUMNAS_CITAS;
			} else {
				//	COLUMNAS POR DEFECTO (las mismas que se mostraban hasta ahora)
				//		HISTORIA, PACIENTE, HORA y PRIORIDAD
				columnas_citas = 'idunico,nhc_centro,paciente,hora,prioridad,';
				//		si existen los campos de PRESTACIÓN mostrarlos tambien (existen en integraciones,
				//		p.e. SIHGA, o mediante worklist...), y si no se muestra el TIPO DE EXPLORACIÓN
				//	XXX	de momento hay una opción de la configuración para indicar si se muestra o no la prestacion
				if (opciones_config.MOSTRAR_PRESTACION_EN_CITAS) {
					columnas_citas = columnas_citas + 'descripcion_prestacion,codigo_prestacion,';
				} else {
					columnas_citas = columnas_citas + 'tipoexploracion,';
				}
				// OBSERVACIONES
				columnas_citas = columnas_citas + 'observaciones';
				//		para INTEGRACION_SIHGA añadir la columna con el BOTON de no realizada
//				if (opciones_config.INTEGRACION_SIHGA) {
//					columnas_citas = columnas_citas + ',button';
//				}
			}

			//Agregar columna fecha
			if (columnas_citas.indexOf('flag_estado')==0){
				// si viene la columan de flag estado, la columna fecha tiene que estar en la 
				// segunda posicion (index = 1), por eso se hace un substr de la cadena para poder
				// insertarla entremedio de flag_estado y el resto de las columnas que vienen por
				// parametro.
				columnas_citas = columnas_citas.substr(0,12) + "fecha," +  columnas_citas.substr(12,columnas_citas.length);
			}else{
				columnas_citas = "fecha,"+ columnas_citas;
			}	
			
			
			//	separar las columnas por las comas y asignar al "fielddef".
			fielddef = [];
			columnas_citas = columnas_citas.split(',');
			for (var i = 0; i < columnas_citas.length; i++) {
				//	verificar que exista la definicion de la columna...
				if (defs[columnas_citas[i]]) {
					//	...y añadirla

					// En el caso de la columna "button" solo se añade si
					// esta activa la cancelacion de citas/exploraciones en el ini
					if (columnas_citas[i] == 'button') {
						if (opciones_config.CANCELAR_CITAS_EXPLORACIONES == 0) {
							continue;
						}
					}

					fielddef.push( defs[columnas_citas[i]] );
				}
			}
			
			return fielddef;		
		}


	}


}();
