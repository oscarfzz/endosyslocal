var nueva_exploracion = function() {

	return {

		CON_CITA: 'CON_CITA',
		SIN_CITA: 'SIN_CITA',

		modo: null,	//	CON_CITA o SIN_CITA
		paciente_id: null,
		cita_id: null,
		tipo_exploracion_id: null,

		// REVISAR Y BORRAR
		// se usa para guardar el id de la exploracion en caso de ir hacia atras
		expl_anterior: null, 
		cita_id_expl_anterior:null,

		//2.4.8 - Se pueden modificar estos 3 campos si voy hacia atras.
		cita_id_original: null,
		paciente_id_original: null,
		tipo_exploracion_id_original: null,
		exploracion_id_editandose: null,

		//	SOLO SE USAN EN EL CASO DE "INTEGRACION_SIHGA"
		agenda_id: null,
		SIHGA_servicio_id: null,
		prestacion_id: null,
		medico_id_exploracion: null, // guarda el id del medico de la cita en caso de que se este realizando 
		///////////////////////////

		reset_valores_originales:function(){
			nueva_exploracion.cita_id_original = null;
			nueva_exploracion.paciente_id_original = null;
			nueva_exploracion.tipo_exploracion_id_original = null;
			nueva_exploracion.exploracion_id_editandose = null;
		},

		//Devuelve TRUE si la exploracion esta siendo editada.
		is_exploracion_editandose: function(){
			if (nueva_exploracion.exploracion_id_editandose != null || 
				nueva_exploracion.cita_id_original != null ||
				nueva_exploracion.paciente_id_original != null ||
				nueva_exploracion.tipo_exploracion_id_original != null){
				return true;
			}else{
				return false
			}
		},

		// reset_originales: Sirve para comenzar una nueva exploracion sin datos guardados por la 
		//					 funcionalidad de ir hacia atras
		mostrar_sin_cita: function(reset_originales) {
			set_titulo_pantalla(_('Nueva exploración'));/*IDIOMAOK*/
			activar_asistente();
			nueva_exploracion.modo = nueva_exploracion.SIN_CITA;
			nueva_exploracion.paciente_id = null;
			nueva_exploracion.cita_id = null;
			nueva_exploracion.tipo_exploracion_id = null;
			nueva_exploracion.agenda_id = null;
			nueva_exploracion.SIHGA_servicio_id = null;
			nueva_exploracion.prestacion_id = null;

			if (reset_originales){
				nueva_exploracion.reset_valores_originales();
			}

			// Cargar la pantalla de pacientes
			nueva_exploracion._seleccionar_paciente();
		}, 
		// Siguiente funcion: nueva_exploracion._seleccionar_paciente()


		// reset_originales: Sirve para comenzar una nueva exploracion sin datos guardados por la 
		//					 funcionalidad de ir hacia atras
		mostrar_con_cita: function(reset_originales) {
			set_titulo_pantalla(_('Nueva exploración'));/*IDIOMAOK*/
			activar_asistente();
			nueva_exploracion.modo = nueva_exploracion.CON_CITA;
			nueva_exploracion.paciente_id = null;
			nueva_exploracion.cita_id = null;
			nueva_exploracion.tipo_exploracion_id = null;
			nueva_exploracion.agenda_id = null;
			nueva_exploracion.SIHGA_servicio_id = null;
			nueva_exploracion.prestacion_id = null;

			if (reset_originales){
				nueva_exploracion.reset_valores_originales();
			}

			// Cargar la pantalla de citas
			nueva_exploracion._seleccionar_cita();
		}, // Siguiente funcion: nueva_exploracion._seleccionar_cita()


		_seleccionar_cita: function() {
			if (nueva_exploracion.exploracion_id_editandose){
				set_titulo_pantalla(null, _('Modificar la cita'));//IDIOMAOK	
			}else{
				set_titulo_pantalla(null, _('Seleccionar la cita'));//IDIOMAOK
			}
			

			//Muestra la pantalla de seleccion de Cita.
			contenido_principal.mostrar(gestion_citas, function() {
				
				// Funcionalidad especifica:
				// Doble click en cita: continuar
				gestion_citas.datatable_results.subscribe("rowDblclickEvent", function(oArgs) {
					$("#mainnav-continuar-btn").click();
				});
				
				set_atras(null);
				
				// ----------------------------------------------------------------------
				// Este continuar se mostrará en la pantalla de seleccion de cita. 
				// ESTE SET CONTINUAR CORRESPONDE DE SEL. DE CITAS -> TIPOS DE EXPLORACION	
				//si hay una exploracion que se esta editando muestra el boton continuar
				if (nueva_exploracion.exploracion_id_editandose){
					nueva_exploracion.set_continuar_seleccion_cita();
				}else{
					set_continuar(null);
				}
			});
		}, // Siguiente funcion: nueva_exploracion._seleccionar_cita_2()

		// Busca el paciente de la cita
		_seleccionar_cita_2: function() {
		
			if (gestion_citas.paciente_id) {
				nueva_exploracion._continuar_seleccionar_cita();
			} else {
				//	XXX	SIHGA
				//	si el paciente_id es null, buscar el paciente por el nhc.
				//	esto hara que se llame al ws de pacientes, se obtenga el paciente
				//	y se inserte en la bbdd, obteniendo asi un id
				//	NUEVO 13-9-2016: Se añade el parametro deshabilitado = 0 porque tal como se han hecho las integraciones
				//	del clinico san carlos y getafe, con plugins, entra a esta parte de código porque no crean los pacientes
				//	y no se tiene el paciente_id. Además, como el index por historia devuelve los deshabilitados por defecto,
				//	esto estaba causando un problema. Al poner este filtro deshabilitado=0 nos aseguramos de que solo se devuelva
				//	el paciente habilitado.
				Endosys.pacientes.index(TM.operaciones, {historia: gestion_citas.historia, deshabilitado: 0})
				  .done(function(pacientes) {
				  	gestion_citas.paciente_id = pacientes[0].id;
					nueva_exploracion._continuar_seleccionar_cita();
				  });
			}
		}, // Siguiente funcion: nueva_exploracion._continuar_seleccionar_cita()

		// Graba id de la cita y del paciente en nueva_exploracion
		_continuar_seleccionar_cita: function() {

			//si la cita esta libre
			if ( (!gestion_citas.flag_estado || gestion_citas.flag_estado == '00') && nueva_exploracion.is_exploracion_editandose()) {
				nueva_exploracion._dialog_confirmacion_cambio_cita(nueva_exploracion._pre_seleccionar_tipo_expl);

				/*if (nueva_exploracion.cita_id_original==gestion_exploracion.cita_id){
					nueva_exploracion.cita_id = gestion_citas.cita_id;
					nueva_exploracion.paciente_id = gestion_citas.paciente_id;
					nueva_exploracion._pre_seleccionar_tipo_expl();
				}else{
					
				}*/
			}else{
				
				nueva_exploracion.cita_id = gestion_citas.cita_id;
				nueva_exploracion.paciente_id = gestion_citas.paciente_id;
				nueva_exploracion._pre_seleccionar_tipo_expl();

			}
			
		},// Siguiente funcion: nueva_exploracion._pre_seleccionar_tipo_expl()


		// Este codigo anteriormente estaba en _continuar_seleccionar_cita, se cambio de lugar para poder usarlo
		// en otro sector (cuando se implemento el desarrollo de 'ir hacia atras') y no repetir codigo
		_pre_seleccionar_tipo_expl: function(){
			// Comprobar si la cita tiene tipo expl asociado. Si lo tiene, entonces permitir
			// o no cambiar el tipo de exploracion asociado segun la configuracion del servidor

			if (gestion_citas.tipo_exploracion_id){
				// gestion_citas tiene tipo_exploracion y no se permite cambiar el tipo
				if (!(opciones_config.PERMITIR_CAMBIAR_TIPO_EXPLORACION_DE_CITA)){
					tipos_exploracion.tipo_exploracion_id = gestion_citas.tipo_exploracion_id;
					nueva_exploracion.tipo_exploracion_id = gestion_citas.tipo_exploracion_id;
					nueva_exploracion._realizar_expl();
				}else{ // tiene tipo de exploracion y si se permite cmbiar el tipo
					tipos_exploracion.tipo_exploracion_id = gestion_citas.tipo_exploracion_id;
					nueva_exploracion._seleccionar_tipo_expl( gestion_citas.tipo_exploracion_id );
				}
			}else{
				tipos_exploracion.tipo_exploracion_id = null;
				nueva_exploracion._seleccionar_tipo_expl();
			}

			// - Antes de la 2.4.9.2
			/*if ((gestion_citas.tipo_exploracion_id) && !(opciones_config.PERMITIR_CAMBIAR_TIPO_EXPLORACION_DE_CITA)) {
				nueva_exploracion.tipo_exploracion_id = gestion_citas.tipo_exploracion_id;
				nueva_exploracion._realizar_expl();
			} else {
				nueva_exploracion._seleccionar_tipo_expl( gestion_citas.tipo_exploracion_id );
			}*/

		},// Siguiente funcion: nueva_exploracion._seleccionar_tipo_expl() o nueva_exploracion._realizar_expl()


		// Mostrar la pantalla de seleccion de tipo de exploracion
		_seleccionar_tipo_expl: function(tipo_exploracion_id) {
			
			//	si se indica un tipo_exploracion_id, será el seleccionado por defecto
			if (nueva_exploracion.exploracion_id_editandose){
				set_titulo_pantalla(null, _('Modificar el tipo de exploración'));/*IDIOMAOK*/
			}else{
				set_titulo_pantalla(null, _('Seleccionar el tipo de exploración'));/*IDIOMAOK*/	
			}
			
			contenido_principal.mostrar(tipos_exploracion, tipo_exploracion_id, {

				onBtnClick: function(id) {
					tipos_exploracion.tipo_exploracion_id = id;
					$("#mainnav-continuar-btn").click();

					//	comprobar antes que se haya seleccionado un tipo de expl
					//if (!tipos_exploracion.tipo_exploracion_id) {
					//	Endosys.statusbar.mostrar_mensaje(_('Debe seleccionar un tipo de exploración para continuar'), 1);/*IDIOMAOK*/
					//	return;
					//}
					//
					//nueva_exploracion._realizar_expl();
				},
					
				callback: function() {

					nueva_exploracion.info_cita_paciente(nueva_exploracion.cita_id,nueva_exploracion.paciente_id);

					// Boton continuar y atras
					set_atras(function() {
						// Vuelve a la seleccion de cita o a la seleccion de paciente
						if (nueva_exploracion.modo == nueva_exploracion.SIN_CITA) {
							if (opciones_config.INTEGRACION_SIHGA) {
								nueva_exploracion.agenda_id = null;
								nueva_exploracion.SIHGA_servicio_id = null;
								nueva_exploracion.prestacion_id = null;
								nueva_exploracion.tipoExploracion_id = gestion_agendas_chus.tipoExploracion_id;
								nueva_exploracion._seleccionar_agenda();
							} else {
								nueva_exploracion.paciente_id = null;
								nueva_exploracion._seleccionar_paciente();
							}
						} else if (nueva_exploracion.modo == nueva_exploracion.CON_CITA) {
							nueva_exploracion.cita_id = null;
							gestion_citas.cita_id = null
							nueva_exploracion._seleccionar_cita();
						}
					});

					set_continuar(function() {

						// va hacia realizar exploracion
						if (tipo_exploracion_id) {
							//Arreglo bug Num Pet #650 - si la cita tenia un tipo de exploración asignado no te permitia cambiarlo							
							if (tipos_exploracion.tipo_exploracion_id){
								nueva_exploracion.tipo_exploracion_id = tipos_exploracion.tipo_exploracion_id;
							}else{
								nueva_exploracion.tipo_exploracion_id = tipo_exploracion_id;
							}
							//FIN Arreglo bug Num Pet #650
							
							nueva_exploracion._realizar_expl();
						}else{
							// no se selecciono ninguno, pero checkea si tiene un
							// id original por la funcionalidad del ir hacia atras
							if (!tipos_exploracion.tipo_exploracion_id){
								// no se clickeo en el boton del tipo de exploracion, sino en la flecha
								if (nueva_exploracion.tipo_exploracion_id_original){
									// se clickeo en adelante, y estaba editando, por lo tanto se usa el mismo
									// tipo de exploracion que tenia
									tipos_exploracion.tipo_exploracion_id = nueva_exploracion.tipo_exploracion_id_original;
									nueva_exploracion._realizar_expl();
								}else{
									//si es una nueva, etonces si o si tiene que apretar el boton 
									//del tipo de exploracion
									Endosys.statusbar.mostrar_mensaje(_('Debe seleccionar un tipo de exploración para continuar'), 1);/*IDIOMAOK*/
									return;
								}
							}else{
								//se selecciono un tipo de exploracion presionando en un boton
								if (nueva_exploracion.tipo_exploracion_id_original){ 
									// si se estaba editando entonces tiene que checkear que la nueva que se 
									// selecciono no sea igual para preguntar si quiere hacer el cambio.
									if (nueva_exploracion.tipo_exploracion_id_original!=tipos_exploracion.tipo_exploracion_id){
										nueva_exploracion._dialog_confirmacion_cambio_tipo_exploracion(nueva_exploracion._realizar_expl);
									}else{
										//es igual, por lo tanto no pregunta la confirmacion del cambio
										nueva_exploracion.tipo_exploracion_id = tipos_exploracion.tipo_exploracion_id;
										nueva_exploracion._realizar_expl();	
									}
								}else{
									//console.log(tipos_exploracion.tipo_exploracion_id);
									//es nueva y apreto en el tipo de exploracion, por lo tanto va a realizarla
									nueva_exploracion.tipo_exploracion_id = tipos_exploracion.tipo_exploracion_id;
									nueva_exploracion._realizar_expl();	
								}

							}
						}
					});

				}
				
			});
		},



		//cuadro de dialogo para confirmar el cambio de paciente.
		_confirmacion_cambio_paciente: function(callback){

			// Viene de nueva exploracion
			if (!nueva_exploracion.paciente_id_original){
				nueva_exploracion.paciente_id = gestion_pacientes.paciente_id;
				if (callback) {callback();}

			// Viene de editar exploracion "ir hacia atras"
			}else{

				if (gestion_pacientes.paciente_id != nueva_exploracion.paciente_id_original){
					
					//muestra el dialog de confirmacion de cambio de paciente.
					nueva_exploracion._dialog_confirmacion_cambio_paciente(callback);

				}else{
					nueva_exploracion.paciente_id = nueva_exploracion.paciente_id_original;
					if (callback) {callback();}
				}
			}

		},

		//
		_seleccionar_paciente: function() {

			if (nueva_exploracion.exploracion_id_editandose){
				set_titulo_pantalla(null, _('Modificar el paciente'));/*IDIOMAOK*/
			}else{
				set_titulo_pantalla(null, _('Seleccionar el paciente'));/*IDIOMAOK*/
			}
			
			contenido_principal.mostrar(gestion_pacientes, function() {
				// funcionalidad especifica:
				// Doble click en paciente: continuar
				gestion_pacientes.datatable_results.subscribe("rowDblclickEvent", function(oArgs) {
					$("#mainnav-continuar-btn").click();
					//Y.one("#mainnav-continuar-btn").simulate("click"); error ie9
				});
				
				gestion_pacientes.datatable_results.subscribe("rowClickEvent", function(oArgs) {
					if (!gestion_pacientes.datatable_results.getRecord(oArgs.target)) return;	//	comprobar que la fila tiene record asignado (porque la fila con el mensaje 'no hay resultados' no tiene record y daria error)
					gestion_pacientes._seleccionar_row(oArgs.target);
					nueva_exploracion.set_continuar_seleccion_paciente();
				});

				// boton continuar y atras
				set_atras(null);
				
				//si hay una exploracion que se esta editando muestra el boton continuar
				if (nueva_exploracion.exploracion_id_editandose){
					nueva_exploracion.set_continuar_seleccion_paciente();
				}else{
					set_continuar(null);
				}
				
			}, {
				opcion_deshabilitados: false
			});
		},

		// SOLO SIHGA (SANTIAGO)
		_seleccionar_agenda: function(tipo_exploracion_id) {
			//	mostrar la pantalla de seleccionar agenda y prestacion
			//	esto es exclusivo de la integración de SIHGA (Santiago)
			if (!opciones_config.INTEGRACION_SIHGA) {
				alert(_('ERROR: se ha intentado ejecutar el paso "seleccionar agenda" pero no está activada la opción "INTEGRACION_SIHGA"'));/*IDIOMAOK*/
				return;
			}

			set_titulo_pantalla(null, _('Seleccionar la agenda y la prestación'));/*IDIOMAOK*/
			contenido_principal.mostrar(gestion_agendas_chus)
			.done(function() {
				//		doble click en agenda: continuar
				gestion_agendas_chus.datatable_prestaciones.subscribe("rowDblclickEvent", function(oArgs) {
							$("#mainnav-continuar-btn").click();
							//Y.one("#mainnav-continuar-btn").simulate("click"); ERROR IE9
						});
						
				//	botones continuar y atras
				set_atras(function() {
					nueva_exploracion.paciente_id = null;
					nueva_exploracion._seleccionar_paciente();
				});
				
				set_continuar(function() {
					//	comprobar antes que se haya seleccionado una agenda y prestación
					if (!gestion_agendas_chus.prestacion_id) {
						Endosys.statusbar.mostrar_mensaje(_('Debe seleccionar una prestación para continuar'), 1);/*IDIOMAOK*/
						return;
					}
					nueva_exploracion.agenda_id = gestion_agendas_chus.agenda_id;
					nueva_exploracion.SIHGA_servicio_id = gestion_agendas_chus.servicio_id;
					nueva_exploracion.prestacion_id = gestion_agendas_chus.prestacion_id;
					nueva_exploracion.tipoExploracion_id = gestion_agendas_chus.tipoExploracion_id;
					nueva_exploracion._seleccionar_tipo_expl(nueva_exploracion.tipoExploracion_id);
				});
			});
		},

		// Mostrar la pantalla de realizar expl	
		_realizar_expl: function() {
			
			// 2.4.7: es necesario un servicio activo para hacer una nueva exploración
			if (!Endosys.auth.servicio_activo) {
				alert(_("Se requiere un servicio activo para poder realizar una nueva exploración"));
				return;
			}
			
			// 2.4.8
			// Si esta editandose la exploración entonces envia un UPDATE 
			// con los parametros 3 parametros posibles: cita, paciente y tipoExploracion_id
			if (nueva_exploracion.is_exploracion_editandose()){
				
				Endosys.statusbar.mostrar_mensaje(_('La exploración se esta editando. Por favor espere...'), 0, 10000, "edicion-exploracion");//IDIOMAOK
										
				// Crea los parametros a enviar si han cambiado
				var campos_actualizados = {}
				if (nueva_exploracion.tipo_exploracion_id_original != nueva_exploracion.tipo_exploracion_id){
					campos_actualizados["tipoExploracion_id"] = nueva_exploracion.tipo_exploracion_id;
				}

				if (nueva_exploracion.cita_id_original != nueva_exploracion.cita_id){
					campos_actualizados["cita_id"] = nueva_exploracion.cita_id;
				}

				if (nueva_exploracion.paciente_id_original != nueva_exploracion.paciente_id){
					campos_actualizados["paciente_id"] = nueva_exploracion.paciente_id;
				}

				Endosys.exploraciones.update(TM.nueva_exploracion, nueva_exploracion.exploracion_id_editandose, campos_actualizados )
				.done(function(){
					set_informacion(null);
					nueva_exploracion._mostrar_exploracion(nueva_exploracion.exploracion_id_editandose);
					set_titulo_pantalla(null, _('Realizando exploración'));/*IDIOMAOK*/
					if (nueva_exploracion.modo == nueva_exploracion.CON_CITA){
						gestion_citas.flag_estado = "01";
					}
				})
				.error(function(){
					//console.log("ERROR");
				});

			}else{
				
				if (nueva_exploracion.modo==nueva_exploracion.CON_CITA){

					if (gestion_citas.flag_estado=="01"){

						// Se selecciona una cita que esta realizandose
						// y no se crea una nueva ya que no es necesario
						nueva_exploracion._mostrar_exploracion(gestion_citas.exploracion.id);


					}else{
						nueva_exploracion._crear_exploracion();	
					}
				}else{
					nueva_exploracion._crear_exploracion();
				}			
			}

		},//termina el realizar exploracion


		_ir_hacia_atras: function(exploracion_id){

			var confirm_perdida = confirm(_("La información introducida se perderá si va hacia atrás."));//IDIOMAOK
			if (confirm_perdida){

				// Grabar informacion que se puede editar usando el "hacia atras"
				nueva_exploracion.exploracion_id_editandose = exploracion_id;
				nueva_exploracion.cita_id_original = nueva_exploracion.cita_id;
				nueva_exploracion.tipo_exploracion_id_original = nueva_exploracion.tipo_exploracion_id;
				nueva_exploracion.paciente_id_original = nueva_exploracion.paciente_id;

				// Checkear si tiene capturas. 
				// SI: Ir hacia atras directamente
				// NO: Mostrar dialogo que pregunta si quiere descartar o ir hacia atras
				Endosys.imagenes.index(TM.nueva_exploracion, {'exploracion_id': nueva_exploracion.exploracion_id_editandose})
				.done(function(imagenes,response) {
					// >> Tiene capturas - Ir hacia atras
					// Nota sobre BORRADO LOGICO: en el futuro tendria que preguntar si quiere deshacer, pero 
					// para hacer esto es necesario implementar el borrado logico para
					// que no se pierdan las imagenes
					
					if (response != "error"){ 
						if (imagenes.length > 0)
						{	
							//tiene imagenes, directamente va hacia atras.
							set_informacion(nueva_exploracion._dialog_informacion_exploracion);
							set_informacion(nueva_exploracion._dialog_informacion_exploracion);
							nueva_exploracion._pre_seleccionar_tipo_expl();
						}
					}else{ //NO tiene imagenes

						//accion de descartar.
						var _si = function(){
							var confirm_dialog = confirm(_("¿Esta seguro?"));//IDIOMAOK
							if (confirm_dialog)
							{
						 		//Borrar la exploracion
								Endosys.exploraciones['delete'](TM.nueva_exploracion,nueva_exploracion.exploracion_id_editandose, {'borrado_motivo': 'Descartar'})
								.done(function()
								{
									//	vaciar la pantalla
									Endosys.statusbar.mostrar_mensaje(_('La exploración ha sido descartada'), 0);/*IDIOMAOK*/
									set_titulo_pantalla(" ", "");
									desactivar_asistente();
									set_atras(null);
									set_continuar(null);
									contenido_principal.cerrar('#mainlayout');
									mostrar_menu_principal();

						 		}).fail(function(data){
									if (data.responseText){
										error = parseError(data.responseText);
										Endosys.statusbar.mostrar_mensaje(error, 1);	
									}
								});
						 	}
						 	$(this).dialog('close');
						}

						// Acciones del ir hacia atrás
						var _no = function(){
							nueva_exploracion._pre_seleccionar_tipo_expl();
							set_informacion(nueva_exploracion._dialog_informacion_exploracion);
							$(this).dialog('close');
						}

						controles.modal_dialog.mostrar({
							title: _('Seleccionar Opción'),/*IDIOMAOK*/
							height: 180,
							width: 405, 
							buttons: [
								{
									text: _("Sí, quiero descartar"),/*IDIOMAOK*/
									click: _si
								},
								{
									text: _("No, ir hacia atrás"),/*IDIOMAOK*/
									click: _no
								}
							],
							resizable: false,
							enterAccept: false,
							
							result: function() {
																	
							},
							
							init: function(accept) {
								this.append( _('¿Desea descartar la exploración?'));/*IDIOMAOK*/						

							}

						});

									
					}
				}).fail(function(response)
				{
					//TODO: Mostrar mensaje de error
				});
			}

		},

		// agregada en 2.4.8 / Para reutilizar el codigo en _realizar_expl
		_crear_exploracion: function(imagenes){


			//	crea una nueva exploracion
			//	si se pasa un cita_id, se marcará la cita como realizada asignandole la nueva exploracion
			params = {	//	estos tres son solo para integración SIHGA
						'_agenda_id':		nueva_exploracion.agenda_id,
						'_servicio_id':		nueva_exploracion.SIHGA_servicio_id,
						'_prestacion_id':	nueva_exploracion.prestacion_id,
						///////////////////////////////////////
						'servicio_id':		Endosys.auth.servicio_activo.id,
						'paciente_id':		nueva_exploracion.paciente_id,
						'tipoExploracion_id': nueva_exploracion.tipo_exploracion_id,
						'cita_id':			nueva_exploracion.cita_id };

			Endosys.exploraciones.create(TM.nueva_exploracion,params)
			.done(function(exploracion) {
				
				Endosys.statusbar.cerrar_mensaje("edicion-exploracion");
				//si la exploracion era con citas entonces cambia el flag estado
				//console.log(exploracion)
				if (nueva_exploracion.modo == nueva_exploracion.CON_CITA){
					gestion_citas.flag_estado = "01";
				}
				set_informacion(null);
				set_titulo_pantalla(null, _('Realizando exploración'));/*IDIOMAOK*/
				nueva_exploracion._mostrar_exploracion(exploracion.id);
			})
			.fail(function(response) {
				if(response.status == 400){
					data = JSON.parse(response.responseText);
					
					if (data && data.error_code){
						if (data.error_code == "ERR_NUEVA_EXPL_SERVICIO_NO_INDICADO"){
							alert(data.data);	
						}else if (data.error_code == "ERR_NUEVA_EXPL_CITA_INICIADA" || 
								  data.error_code == "ERR_NUEVA_EXPL_CITA_CANCALEADA" ||
								  data.error_code == "ERR_NUEVA_EXPL_PACIENTE_NO_INDICADO" || 
								  data.error_code == "ERR_NUEVA_EXPL_TIPO_EXPL_NO_INDICADO" || 
								  data.error_code == "ERR_NUEVA_EXPL_PACIENTE_DESHABILITADO"){
							alert(data.data);
							$("#mainnav-atras-btn").click();
						}	
					}
					
				}else{
					Endosys.statusbar.mostrar_mensaje(_('Error al crear la exploración'), 1);/*IDIOMAOK*/	
				}
			});	//termina el create

		},


		_mostrar_exploracion: function(exploracion_id){
			nueva_exploracion.reset_valores_originales();
			if (opciones_config.MOSTRAR_ATRAS_EXPLORACION){
				//CONFIGURA LAS LA NAVEGACION HACIA ATRAS
				//---------------------------------------
				set_atras(function(){
					nueva_exploracion._ir_hacia_atras(exploracion_id);
				});
				//---------------------------------------
				
				set_continuar(null);
			}else{
				desactivar_asistente();
				set_atras(null);
				set_continuar(null);	
			}
			
			contenido_principal.mostrar(gestion_exploraciones.una, exploracion_id);
		},


		// Muestra el cuadro informativo de la cita y el paciente en 
		// la pantalla de seleccion de tipo de exploracion.
		// Funcion llamada desde: _seleccionar_tipo_expl
		info_cita_paciente: function(cita_id, paciente_id){
			//mostrar informacion de la cita o el paciente
			if (cita_id){
		
				Endosys.citas.show(TM.nueva_exploracion,cita_id).done(function(cita){
					$("#tipo_cita").show();
					//cita
					$("#tipo_exploracion_cita").html(cita.fecha + " - " + cita.hora);
					
					//nombre
					$("#tipo_exploracion_paciente_nombre").html((cita.paciente.nombre || "") + " " +  (cita.paciente.apellido1 || "") + " " +  (cita.paciente.apellido2 || ""));
					
					//edad

					if (cita.paciente.fechaNacimiento){
						$("#tipo_exploracion_paciente_edad").html(calcular_edad(cita.paciente.fechaNacimiento));	
					}else{
						$("#tipo_exploracion_paciente_edad").html("-");
					}

					
					//prestacion
					if ((cita.ex) && (cita.ex.prestacion_descr!=null)) {
						$("#tipo_exploracion_prestacion_cita").html(cita.ex.prestacion_descr);
					} else if ((cita.work) && (cita.work.schProcStepDescription != null)) {
						$("#tipo_exploracion_prestacion_cita").html(cita.work.schProcStepDescription);
					}else{
						$("#tipo_exploracion_prestacion_cita_label").hide();
						$("#tipo_exploracion_prestacion_cita").html("");
						$("#punto-prestacion").hide();
					}

					var centro_id = Endosys.auth.servicio_activo.centro_id;
					if (opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'IDUNICO' ||
						opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'IDUNICO+NHC') {
						$("#tipo_exploracion_paciente_historia_label").html(opciones_config.IDUNICO_LABEL+":");
						$("#tipo_exploracion_paciente_historia").html(cita.paciente.idunico);
					} else {
						$("#tipo_exploracion_paciente_historia_label").html(_('NHC')+":");
                        $("#tipo_exploracion_paciente_historia").html('');
                        if (!!cita.paciente.centros) {
                            for (var i=0; i < cita.paciente.centros.length; i++)  {
                                if (cita.pacientes.centros[i].id === centro_id) {
                                    $("#tipo_exploracion_paciente_historia").html(cita.paciente.centros[i].nhc);
                                    break;
                                }
                            }
                        }
					}
					$("#tipos_exploracion_datos").show();
				});

			}else{

				if (paciente_id) {

					$("#tipo_cita").hide();
					$("#tipo_exploracion_prestacion_cita_label").hide();
					$("#tipo_exploracion_prestacion_cita").html("");

					Endosys.pacientes.show(TM.nueva_exploracion,paciente_id).done(function(paciente){
						//nombre
						$("#tipo_exploracion_paciente_nombre").html((paciente.nombre || "") + " " +  (paciente.apellido1 || "") + " " + (paciente.apellido2 || ""));
						
						//edad

							
						if (paciente.fechaNacimiento){
							$("#tipo_exploracion_paciente_edad").html(calcular_edad(paciente.fechaNacimiento));	
						}else{
							$("#tipo_exploracion_paciente_edad").html("-");
						}
						

						var centro_id = Endosys.auth.servicio_activo.centro_id;
						if (opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'IDUNICO' ||
							opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'IDUNICO+NHC') {
							$("#tipo_exploracion_paciente_historia_label").html(opciones_config.IDUNICO_LABEL+":");
							$("#tipo_exploracion_paciente_historia").html(paciente.idunico);
						} else {
							$("#tipo_exploracion_paciente_historia_label").html(_('NHC')+":");
							if (!!paciente.centros) {
								for (var i=0; i < paciente.centros.length; i++) {
									if (paciente.centros[i].id === centro_id) {
										$("#tipo_exploracion_paciente_historia").html(paciente.centros[i].nhc);
										break;
									}
								}
							}
						}
						$("#tipos_exploracion_datos").show();
					});

				}

			}

			
		},

		//llamada desde exploraciones sin finalizar 
		reconstruir_nueva_exploracion: function(exploracion_id){

			nueva_exploracion.paciente_id = null;
			nueva_exploracion.cita_id = null;
			nueva_exploracion.tipo_exploracion_id = null;
			nueva_exploracion.agenda_id = null;
			nueva_exploracion.SIHGA_servicio_id = null;
			nueva_exploracion.prestacion_id = null;

			nueva_exploracion.reset_valores_originales();

			//reconstruyo nueva exploracion
			Endosys.exploraciones.show(TM.content_exploraciones,exploracion_id).done(function(exploracion){
				if (exploracion.cita==null){
					nueva_exploracion.modo=nueva_exploracion.SIN_CITA;
				}else{
					nueva_exploracion.modo=nueva_exploracion.CON_CITA;
					nueva_exploracion.cita_id = exploracion.cita.id;
				}

				nueva_exploracion.paciente_id = exploracion.paciente.id;
				nueva_exploracion.tipo_exploracion_id = exploracion.tipoExploracion_id;

				//set_titulo_pantalla(_("Exploración sin finalizar"), _("Realizando exploración"));//IDIOMAOK
				
				//FALTA INTEGRACION SIHGA
				/* nueva_exploracion.agenda_id = null;
				nueva_exploracion.SIHGA_servicio_id = null;
				nueva_exploracion.prestacion_id = null;
				*/

			});

		}, 

		set_continuar_seleccion_paciente: function(){

			set_continuar(function() {
				// Comprobar antes que se haya seleccionado un paciente
				if (!gestion_pacientes.paciente_id) {
					if (nueva_exploracion.paciente_id_original){
						gestion_pacientes.paciente_id = nueva_exploracion.paciente_id_original;
					}else{
						Endosys.statusbar.mostrar_mensaje(_('Debe seleccionar un paciente para continuar'), 1);//IDIOMAOK
						return;	
					}
				}
				
				if (opciones_config.INTEGRACION_SIHGA) {
					nueva_exploracion._confirmacion_cambio_paciente(nueva_exploracion._seleccionar_agenda);
				} else {
					nueva_exploracion._confirmacion_cambio_paciente(nueva_exploracion._seleccionar_tipo_expl);
				}
			});	

		},

		set_continuar_seleccion_cita: function(){

			set_continuar(function() {
	
					// Esta var se usa para cuando la exploracion esta sin finalizar
					// y no se esta editando una exploracion en ese momento.  
					// Del listado de expl. sin finalizar va directo al show de la exploracion 
					var ir_directo_exploracion = false;

					// cuando esta habilitado para abrir se hace el resolve(),
					// para poder seguir la ejecucion
					var habilitado_para_avanzar = $.Deferred();


					if (gestion_citas.cita_id){ 
						// Una cita se seleccionó. 
						habilitado_para_avanzar.resolve();
					}else{
						// No se selecciono cita, entonces puede ser que:
						// 1) Si se estaba editando use la cita original
						// 2) Lance un error 
						if (nueva_exploracion.cita_id_original) {
							
							//1) Completar la informacion de la cita en gestion_citas
							Endosys.citas.show(TM.nueva_exploracion, nueva_exploracion.cita_id_original)
							.done(function(cita){
								// Si no se selecciono una nueva cita pero tenia cita, se usa la misma cita que antes
								// Para hacer eso se tiene que llamar al rest de citas para pedir la informacion de la cita
								// completa la informacion de la cita
								gestion_citas.cita_id =				cita.id;							
								gestion_citas.tipo_exploracion_id =	cita.tipoexploracion_id;
								gestion_citas.paciente_id =			cita.paciente_id;
								gestion_citas.historia =			cita.historia;
								gestion_citas.paciente =			(cita.nombre || "" ) + " " + (cita.apellido1 || "" ) + " " + (cita.apellido2 || "" );
								if (cita.exploracion!=undefined){
									gestion_citas.exploracion = cita.exploracion;
									gestion_citas.medico_id_exploracion = cita.exploracion.medico_id;
									gestion_citas.flag_estado = ("0" + (cita.exploracion.estado+1)).slice(-2);
								}else{
									gestion_citas.exploracion = null;
									gestion_citas.medico_id_exploracion = null;
									gestion_citas.flag_estado = "00";
								}
								
								habilitado_para_avanzar.resolve();
							});
						}else{
							// 2) Lanza error y sale
							Endosys.statusbar.mostrar_mensaje(_('Debe seleccionar una cita para continuar'), 1);/*IDIOMAOK*/
							habilitado_para_avanzar.reject();
							return;	
						}	
					}
					
					//-------------------------------------
					//Prosigue luego de resolver el promise
					habilitado_para_avanzar.then(function(){

						if (gestion_citas.flag_estado && gestion_citas.flag_estado != '00') {
							if (gestion_citas.flag_estado == '01'){ //LA ELEGIDA ES SIN FINALIZAR
								
								if ( gestion_citas.medico_id_exploracion != userinfo.get_usuario().medico.id ){
									//cita iniciada y no es el mismo usuario que la creo
									Endosys.statusbar.mostrar_mensaje(_(
										'La cita selecciona se está realizando'), 1);/*IDIOMAOK*/
									return;
								}else{
									//la cita es del medico, entonces puede seleccionarla 

									if (nueva_exploracion.is_exploracion_editandose()){
										// checkea que la cita id sea la misma que la de la expl anterior
										// si es la misma entonces esta seleccionando la misma cita que antes.
										// si es otra, entonces no puede seleccionarla, porque quiere seleccionar una 
										// cita que esta siendo usada y ya tiene una exploracion asignada.
										if (nueva_exploracion.cita_id_original != gestion_citas.cita_id){
											Endosys.statusbar.mostrar_mensaje(_(
												'La cita selecciona se está realizando. \
												Seleccione una cita libre o la misma que esta editando'), 1);/*IDIOMAOK*/
											return;
										}
									}else{
										// Es nueva
										ir_directo_exploracion = true;
									}
								}

							}else if (gestion_citas.flag_estado == '02'){ //LA ELEGIDA ESTA TERMINADA
								//cita finalizada
								Endosys.statusbar.mostrar_mensaje(_(
									'La cita selecciona ya está realizada'), 1);/*IDIOMAOK*/
								return;
							}else if (gestion_citas.flag_estado == '03'){ //LA ELEGIDA ESTA CANCELANDA
								//cita cancelada
								Endosys.statusbar.mostrar_mensaje(_(
									'La cita seleccionada ha sido cancelada'), 1);/*IDIOMAOK*/
								return;
							}
							else if (gestion_citas.flag_estado == '04'){
								// Cita con exploración borrada
								Endosys.statusbar.mostrar_mensaje(_(
									'La exploración de esta cita ha sido borrada'), 1);/*IDIOMAOK*/
								return;
							}
						}

						if (ir_directo_exploracion){
							contenido_principal.mostrar(gestion_exploraciones.una, gestion_citas.exploracion.id);
							
							//reconstruir nueva exploracion para que funcione las el ir hacia atras.
							nueva_exploracion.reconstruir_nueva_exploracion(gestion_citas.exploracion.id);

							if (opciones_config.MOSTRAR_ATRAS_EXPLORACION){
								// Seteo ir hacia atras
								set_atras(function(){
									nueva_exploracion._ir_hacia_atras(gestion_citas.exploracion.id);
								});
								set_continuar(null);
							}else{
								desactivar_asistente();
								set_atras(null);
								set_continuar(null);
							}

						}else{
							
							//mostrar el dialogo con los datos del paciente
							if (opciones_config.CONFIRMACION_PACIENTE_CITAS ) {
								
								var params_dialog = { width: 450 };
								controles.confirm_dialog(_('Confirmación de paciente'), '<div style="line-height: 25px; text-align: center">' + _('Se dispone a realizar una exploración a') + ' <br><strong>' + gestion_citas.paciente +/*IDIOMAOK*/
														'</strong><br>, ' + _('con número de historia') + ' <br><strong>' + gestion_citas.historia + '</strong>.</div>', null, params_dialog)/*IDIOMAOK*/
								.done(function() {			
													
									nueva_exploracion._seleccionar_cita_2();
								})
								.fail(function() {								
									return;								
								});	

							}else{
								
								nueva_exploracion._seleccionar_cita_2();
							}
						}


					});
					// Fin de habilitado_para_avanzar
					//-------------------------------------											
								
				});// FIN DEL SET_CONTINUAR	

		},


		/************/
		/* DIALOGOS */
		/************/


		/* Dialogo de confirmacion de cambio de paciente
		   Usado en la funcionalidad de ir hacia atras cuando se selecciona
		   un paciente que es distinto al que tenia la exploración

		*/
		_dialog_confirmacion_cambio_paciente: function(callback){

			controles.modal_dialog.mostrar({
				title: _('Confirmación de cambio de paciente'),/*IDIOMAOK*/
				height: 230,
				width: 540, 
				buttons: [
					{
						text: _("Sí, deseo cambiarlo"),/*IDIOMAOK*/
						//CAMBIAR PACIENTE
						click: function(){

									nueva_exploracion.paciente_id = gestion_pacientes.paciente_id;
									if (callback) {callback();}
								 	$(this).dialog('close');

								}
					},
					{
						text: _("No, continuar con el original"),/*IDIOMAOK*/
						//CANCELAR CAMBIO
						click: function(){
									nueva_exploracion.paciente_id = nueva_exploracion.paciente_id_original;
									if (callback) {callback();}
									$(this).dialog('close');
								}
					}
				],
				resizable: false,
				enterAccept: false,	

				init: function(accept) {

					var content_dialog = this; 
					content_dialog.append( _('¿Esta seguro que desea cambiar el paciente?'));/*IDIOMAOK*/
					Endosys.pacientes.show(TM.nueva_exploracion,nueva_exploracion.paciente_id_original).done(function(paciente){
						
						var historia = paciente.idunico;

						var edad = calcular_edad(paciente.fechaNacimiento);
						
						content_dialog.append('<div class="dialog_primer_valor"></div>');
						content_dialog.append("<div class='dialog_valor_anterior'>" +historia + " &#8226; " + (paciente.nombre || "") + " " +  (paciente.apellido1 || "") + " " +  (paciente.apellido2 || + "") + " &#8226; " + edad + " " +_("años") + "</div>");//IDIOMAOK
						content_dialog.append("<div class='dialog_valor_flecha'><i class='fa fa-arrow-down'></div>");
						Endosys.pacientes.show(TM.nueva_exploracion,gestion_pacientes.paciente_id).done(function(paciente_nuevo){
							

							var historia = paciente_nuevo.idunico;


							var edad = calcular_edad(paciente_nuevo.fechaNacimiento);
							

							content_dialog.append("<div class='dialog_valor_nuevo'>" + historia + " &#8226; " + (paciente_nuevo.nombre || "") + " " +  (paciente_nuevo.apellido1 || "") + " " +  (paciente_nuevo.apellido2 || "") + " &#8226; " + edad + "</div>");
						
						});
					});
				}
			});


		},

		/* Dialogo de confirmacion de cambio de exploracion
		   Usado en la funcionalidad de ir hacia atras cuando se selecciona
		   una exploracion que es distinta al que tenia asignada

		*/

		_dialog_confirmacion_cambio_tipo_exploracion: function(callback){

			controles.modal_dialog.mostrar({
				title: _('Confirmación de cambio de tipo de exploración'),/*IDIOMAOK*/
				height: 230,
				width: 540,				
				buttons: [
					{
						text: _("Sí, deseo cambiarlo"),/*IDIOMAOK*/
						//CAMBIAR TIPO DE EXPL
						click: function(){

									nueva_exploracion.tipo_exploracion_id = tipos_exploracion.tipo_exploracion_id;
									if (callback) {callback();}
								 	$(this).dialog('close');

								}
					},
					{
						text: _("No, continuar con la original"),/*IDIOMAOK*/
						//CANCELAR CAMBIO
						click: function(){
									nueva_exploracion.tipo_exploracion_id = nueva_exploracion.tipo_exploracion_id_original;
									tipos_exploracion.tipo_exploracion_id = nueva_exploracion.tipo_exploracion_id_original;
									if (callback) {callback();}
									$(this).dialog('close');
								}
					}
				],
				resizable: false,
				enterAccept: false,	
				init: function(accept) {

					var content_dialog = this; 
					content_dialog.append( _('¿Esta seguro que desea cambiar el tipo de exploración?'));/*IDIOMAOK*/
					content_dialog.append('<div class="dialog_primer_valor"></div>');
					content_dialog.append("<div class='dialog_valor_anterior'>" + tipos_exploracion.values[nueva_exploracion.tipo_exploracion_id_original] + "</div>");
					content_dialog.append("<div class='dialog_valor_flecha'><i class='fa fa-arrow-down'></div>");
					content_dialog.append("<div class='dialog_valor_nuevo'>" + tipos_exploracion.values[tipos_exploracion.tipo_exploracion_id]+ "</div>");
					/*
					Endosys.tipos_exploracion.show(TM.nueva_exploracion,nueva_exploracion.tipo_exploracion_id_original).done(function(tipo_exploracion_anterior){
						content_dialog.append('<div class="dialog_primer_valor"></div>');
						content_dialog.append("<div class='dialog_valor_anterior'>" + tipo_exploracion_anterior.nombre + "</div>");
						content_dialog.append("<div class='dialog_valor_flecha'><i class='fa fa-arrow-down'></div>");
						Endosys.tipos_exploracion.show(TM.nueva_exploracion,tipos_exploracion.tipo_exploracion_id).done(function(tipo_exploracion_nueva){
							
							content_dialog.append("<div class='dialog_valor_nuevo'>" + tipo_exploracion_nueva.nombre+ "</div>");
						
						});
					});
					*/
				},

			});


		},

		/* Dialogo de confirmacion de cambio de paciente
		   Usado en la funcionalidad de ir hacia atras cuando se selecciona
		   un paciente que es distinto al que tenia la exploración

		*/
		_dialog_confirmacion_cambio_cita: function(callback){

			controles.modal_dialog.mostrar({
				title: _('Confirmación de cambio de cita'),/*IDIOMAOK*/
				height: 270,
				width: 600, 
				buttons: [
					{
						text: _("Sí, deseo cambiarla"),/*IDIOMAOK*/
						//CAMBIAR PACIENTE
						click: function(){

									nueva_exploracion.cita_id = gestion_citas.cita_id;
									nueva_exploracion.paciente_id = gestion_citas.paciente_id;
									if (callback) {callback();}
								 	$(this).dialog('close');

								}
					},
					{
						text: _("No, continuar con el original"),/*IDIOMAOK*/
						//CANCELAR CAMBIO
						click: function(){
									nueva_exploracion.cita_id = nueva_exploracion.cita_id_original;
									nueva_exploracion.paciente_id =nueva_exploracion.paciente_id_original;
									gestion_citas.cita_id = null;
									if (callback) {callback();}
									$(this).dialog('close');
								}
					}
				],
				resizable: false,
				enterAccept: false,	

				init: function(accept) {

					var content_dialog = this; 
					content_dialog.append( _('¿Esta seguro que desea cambiar la cita?'));/*IDIOMAOK*/
					content_dialog.append('<div class="dialog_primer_valor"></div>');
					Endosys.citas.show(TM.nueva_exploracion,nueva_exploracion.cita_id_original).done(function(cita){
						
						var historia="";
						var edad="";
						var nombre="";
						if (cita.paciente){
							historia = cita.paciente.idunico;
							
							edad = calcular_edad(cita.paciente.fechaNacimiento);
							
							content_dialog.append("<div class='dialog_valor_anterior'>" +historia + " &#8226; " + (cita.paciente.nombre || "") + " " +  (cita.paciente.apellido1 || "") + " " +  (cita.paciente.apellido2 || + "") + " &#8226; " + edad + " " +_("años") + "</div>");//IDIOMAOK
						}

						//prestacion
						var prestacion = "";
						if ((cita.ex) && (cita.ex.prestacion_descr!=null)) {
							prestacion = (cita.ex.prestacion_descr) ? (" &#8226; " + cita.ex.prestacion_descr) : "";							
						} else if ((cita.work) && (cita.work.schProcStepDescription != null)) {
							prestacion = (cita.work.schProcStepDescription) ? (" &#8226; " + cita.work.schProcStepDescription) : "";									
						}
						
					
						content_dialog.append("<div class='dialog_valor_anterior'>" + cita.fecha + " - " + cita.hora + prestacion + "</div>");
						content_dialog.append("<div class='dialog_valor_flecha'><i class='fa fa-arrow-down'></div>");
						
						Endosys.citas.show(TM.nueva_exploracion,gestion_citas.cita_id).done(function(cita_nueva){
						
							var historia="";
							var edad="";
							var nombre="";
							if (cita.paciente){
								historia = cita_nueva.paciente.idunico;

								edad = calcular_edad(cita_nueva.paciente.fechaNacimiento);
								
								content_dialog.append("<div class='dialog_valor_nuevo'>" +historia + " &#8226; " + (cita_nueva.paciente.nombre || "") + " " +  (cita_nueva.paciente.apellido1 || "") + " " +  (cita_nueva.paciente.apellido2 || + "") + " &#8226; " + edad + " " +_("años") + "</div>");//IDIOMAOK
							}
							//prestacion
							var prestacion = "";
							if ((cita_nueva.ex) && (cita_nueva.ex.prestacion_descr!=null)) {
								prestacion = (cita_nueva.ex.prestacion_descr) ? (" &#8226; " + cita_nueva.ex.prestacion_descr) : "";							
							} else if ((cita_nueva.work) && (cita_nueva.work.schProcStepDescription != null)) {
								prestacion = (cita_nueva.work.schProcStepDescription) ? (" &#8226; " + cita_nueva.work.schProcStepDescription) : "";									
							}
						
							
							content_dialog.append("<div class='dialog_valor_nuevo'>" + cita_nueva.fecha + " - " + cita_nueva.hora + prestacion+"</div>");
						});

					});
				}
			});


		},

		_dialog_informacion_exploracion: function(){

			controles.modal_dialog.mostrar({
				title: _('Información de la exploración que se está modificando'),/*IDIOMAOK*/
				height: 300,
				width: 540, 
				buttons: [
					{
						text: _("Aceptar"),/*IDIOMAOK*/
						click: function(){$(this).dialog('close');}
					}
				],
				resizable: false,
				enterAccept: true,	

				init: function(accept) {

					var content_dialog = this; 
					
					Endosys.exploraciones.show(TM.nueva_exploracion,nueva_exploracion.exploracion_id_editandose).done(function(exploracion){
						
						TM.content_exploraciones.load_content(content_dialog, "content/dialog_informacion_exploracion.html"+ew_version_param()).done(function(){

							if (exploracion.cita){
								$("#dialog_cita_hora").html(exploracion.cita.fecha + " - " + exploracion.cita.hora);
								
								//prestacion
								if ((exploracion.cita.ex) && (exploracion.cita.ex.prestacion_descr!=null)) {
									$("#dialog_cita_prestacion").html( (exploracion.cita.ex.prestacion_descr) ? (" &#8226; " + exploracion.cita.ex.prestacion_descr) : '-' );
								} else if ((exploracion.cita.work) && (exploracion.cita.work.schProcStepDescription != null)) {
									$("#dialog_cita_prestacion").html( (exploracion.cita.work.schProcStepDescription) ? (" &#8226; " + exploracion.cita.work.schProcStepDescription) : '-' );
								}
								
								$("#dialog_informacion_cita").show();
								content_dialog.height((content_dialog.height()+65) + "px");

								//obtiene el nombre de la agenda v2.4.9
								if (exploracion.cita.agenda_id){
									Endosys.agendas.show(TM.nueva_exploracion,exploracion.cita.agenda_id).done(function(agenda){
										if (agenda.nombre){
											$("#dialog_cita_agenda").html(agenda.nombre);
										}
										else{
											$("#dialog_cita_agenda").html("-");	
										}
									});	
								}else{
									$("#dialog_cita_agenda").html("-");	
								}
								
							}

							var centro_id = Endosys.auth.servicio_activo.centro_id;
							$("#dialog_historia_label").html(opciones_config.IDUNICO_LABEL);
							$("#dialog_historia").html(exploracion.paciente.idunico);

							$("#dialog_paciente").html((exploracion.paciente.nombre || '') + ' ' +  (exploracion.paciente.apellido1 || '') + ' ' +  (exploracion.paciente.apellido2 || + ''));
							$("#dialog_edad").html(exploracion.edad_paciente);
							$("#dialog_tipo_exploracion").html(exploracion.tipoExploracion.nombre);


						});
					});
				}
			});


		},


	}

}();