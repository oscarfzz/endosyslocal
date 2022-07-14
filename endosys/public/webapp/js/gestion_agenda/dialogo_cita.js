var dialogo_cita = function() {

	return {

		is_nueva_cita: false,
		tipos_expl: null,
		paciente_modificado: false,

		completar_datos_paciente: function(content_form_cita,datos_paciente){
			var centro_id = Endosys.auth.servicio_activo.centro_id;
			//preparacion datos paciente
			content_form_cita.find("#campo-nhc-cip").val(datos_paciente.idunico);
			content_form_cita.find("#label-nhc-cip").html(opciones_config.IDUNICO_LABEL);
			content_form_cita.find("");
            if (!!datos_paciente.centros) {
                for (var i=0; i < datos_paciente.centros.length; i++) {
                    if (datos_paciente.centros[i].id === centro_id) {
                        content_form_cita.find("#campo-nhc-centro").val(datos_paciente.centros[i].nhc);
                        break;
                    }
                }
            }

			var nombre_completo = (datos_paciente.nombre || "") + " " + (datos_paciente.apellido1 || "" ) + " " + (datos_paciente.apellido2 || "")
			content_form_cita.find("#campo-nombre").val(nombre_completo);

			var aseguradora = "-";
			if (datos_paciente.aseguradora_id && datos_paciente.aseguradora){
				aseguradora = datos_paciente.aseguradora.nombre;
				if (datos_paciente.numAfiliacion){
					aseguradora = aseguradora + " (" + _("Nº Afil.") + ": " + (datos_paciente.numAfiliacion || "-")+ ")";//IDIOMAOK
				}
			}
			content_form_cita.find("#campo-aseguradora").val(aseguradora);

			var fecha_nacimiento = "-";
			if (datos_paciente.fechaNacimiento){
				fecha_nacimiento = datos_paciente.fechaNacimiento + " (" + _("Edad") + ": " + (calcular_edad(datos_paciente.fechaNacimiento) || "-")+ ")";//IDIOMAOK
			}
			content_form_cita.find("#campo-fecha-nacimiento").val(fecha_nacimiento);

			var telefonos = "-";
			if (datos_paciente.telefono1 || datos_paciente.telefono2){
				telefonos = (datos_paciente.telefono1 || "-") + " / " + (datos_paciente.telefono2 || "-") 
			}
			content_form_cita.find("#campo-telefonos").val(telefonos);
		},

		mostrar_dialogo_cita: function(datos_paciente, data_cita, agendas, datos_cita, params_default, tipos_expl, prioridades) {

			var mostrando_dialog = $.Deferred();
			var content_form_cita = $("<div id='content_form_cita'></div>");
			content_form_cita.load("content/dialog_cita.html"+ew_version_param(), function(data,textStatus) {
				if (textStatus == "success") {
					dialogo_cita.tipos_expl = tipos_expl;

					content_form_cita.i18n();
					dialogo_cita.completar_datos_paciente(content_form_cita,datos_paciente);

					content_form_cita.find("#button-ver-detalle-paciente").button().click(function(){
						opciones = {update_datatable:false, btn_eliminar: false};
						var result = gestion_pacientes.mostrar_paciente(datos_paciente.id, true, opciones);
						result.then(function(dialog){
							if (dialog.guardado){
								dialogo_cita.paciente_modificado=true;
							}

							datos_paciente_form = {
								CIP: dialog.find('.paciente-cip').val(),
								fechaNacimiento:  dialog.find('.paciente-fecha_nacimiento').val(),
								aseguradora_id:  dialog.find('.paciente-aseguradora').val(),
								aseguradora: {id: dialog.find('.paciente-aseguradora').val()},
								telefono1: dialog.find('.paciente-telefono1').val(),
								telefono2: dialog.find('.paciente-telefono2').val(),
								nombre: dialog.find('.paciente-nombre').val(),
								apellido1: dialog.find('.paciente-apellido1').val(),
								apellido2: dialog.find('.paciente-apellido2').val(),
								numAfiliacion: dialog.find('.paciente-afiliacion').val(),
							};
							if (datos_paciente_form.aseguradora_id){
								datos_paciente_form.aseguradora["nombre"] = $('.paciente-aseguradora option[value="'+datos_paciente_form.aseguradora_id+'"]').text();
							} 

							dialogo_cita.completar_datos_paciente(content_form_cita, datos_paciente_form);						
						});
						return false;
					});

					//preparacion datos cita
					var fecha_ini = ('0' + data_cita.dia).slice(-2)+"/"+('0' + data_cita.mes).slice(-2)+"/"+data_cita.year;
					var hora_ini = data_cita.hora_ini +":"+ data_cita.minuto_ini; 
					var hora_fin = data_cita.hora_fin +":"+ data_cita.minuto_fin;
					content_form_cita.find("#campo-fecha").val(fecha_ini);
					content_form_cita.find("#campo-fecha").datepicker({ defaultDate: fecha_ini, minDate: new Date() });
					content_form_cita.find("#campo-hora-ini").val(hora_ini);
					content_form_cita.find("#campo-hora-fin").val(hora_fin);
					if (opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'IDUNICO' ||
						opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'IDUNICO+NHC' ||
						opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'NHC+IDUNICO') {
						content_form_cita.find('#div-nhc-cip').show();
					}

					if (opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'NHC' ||
						opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'IDUNICO+NHC' ||
						opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'NHC+IDUNICO') {
						content_form_cita.find('#div-nhc-centro').show();
					}

					//preparacion agendas
					//
					var select_agenda = content_form_cita.find("#agenda-list");
					var select_medico = content_form_cita.find("#medico-list");
					var select_sala = content_form_cita.find("#sala-list");
					var select_tipo_expl = content_form_cita.find("#tipo_exploracion-list");
					var select_prioridad = content_form_cita.find("#priority-list");
					select_agenda.append($('<option value="-1">' + _('Seleccione') + '</option>'));/*IDIOMAOK*/
					for (var i=0; i<agendas.length; i++) {
						var option = $('<option value=' + agendas[i].agenda_id + '>' + agendas[i].agenda_nombre + '</option>');
						option.data("datos_agenda", agendas[i]);
						option.appendTo(select_agenda);
					}
					var select_aseguradora = content_form_cita.find("#aseguradora-list");
					select_aseguradora.append($('<option value="">' + _('Seleccione') + '</option>'));
					Endosys.aseguradoras.index(TM.operaciones, {'activo': 1} )
					.done(function(aseguradoras) {
						for (var i=0; i < aseguradoras.length; i++) {
							if (select_aseguradora.find('option[value="' + aseguradoras[i].id + '"]').length < 1)
								select_aseguradora.append($('<option value="' + aseguradoras[i].id + '">' + aseguradoras[i].nombre + '</option>'));
						}
						if ( datos_cita && datos_cita.aseguradora_id ) {
							select_aseguradora.val(datos_cita.aseguradora_id);
						} else {
							if ( datos_paciente.aseguradora_id ) select_aseguradora.val(datos_paciente.aseguradora_id);
						}
						/*coment pro
						$paciente_aseguradora.selectBoxIt('refresh');*/
					});
					select_agenda
					.add(select_medico)
					.add(select_sala)
					.add(select_tipo_expl)
					.add(select_prioridad)
					.add(select_aseguradora);
					/*.addClass('selectboxit-small')
					.selectBoxIt({
						copyClasses: "container",	//	necesario para aplicar el estilo
						autoWidth:	false,
						theme:		"jqueryui"
					});*/

					select_agenda.change(function() {
						var datos_agenda = $(this).find("option:selected").data().datos_agenda;
						dialogo_cita.pintar_select_medicos(content_form_cita, datos_agenda);
						dialogo_cita.pintar_select_salas(content_form_cita, datos_agenda);
					});
					
					if (datos_cita) {
						dialogo_cita.is_nueva_cita = false;

						//para un modificar, los valores de los datos son los guardados en bbdd
						content_form_cita.find("#observaciones").val(datos_cita.observaciones);
						select_agenda.find("option[value='" + datos_cita.agenda_id + "']").attr("selected", true);
						var datos_agenda = $(this).find("option:selected").data().datos_agenda;
						dialogo_cita.pintar_select_medicos(content_form_cita, datos_agenda, datos_cita.medico_id);
						dialogo_cita.pintar_select_salas(content_form_cita, datos_agenda, datos_cita.sala_id);
						dialogo_cita.pintar_select_tipos_expl(content_form_cita, tipos_expl, datos_cita.tipoExploracion_id );
						dialogo_cita.pintar_select_prioridades(content_form_cita, prioridades, datos_cita.prioridad_id );
						$("body").off("change", "#tipo_exploracion-list", dialogo_cita.change_select_tipo_expl);
						
					} else if ( params_default ) {
						dialogo_cita.is_nueva_cita = true;

						if(params_default.agenda_id){
							//para un nueva cita, si existen valores por defecto importados del valor de los filtros en pantalla gestion_agenda
							select_agenda.find("option[value='" + params_default.agenda_id + "']").attr("selected",true);
							select_agenda.change();
							if (params_default.medico_id) {
								select_medico.find("option[value='"+params_default.medico_id+"']").attr("selected", true);
							}
							if (params_default.sala_id) {
								select_sala.find("option[value='"+params_default.sala_id+"']").attr("selected", true);
							}

						}

						if ( datos_paciente.aseguradora_id ) select_aseguradora.val(datos_paciente.aseguradora_id);

						
						dialogo_cita.pintar_select_tipos_expl(content_form_cita, tipos_expl, params_default.tipoExploracion_id );
						dialogo_cita.pintar_select_prioridades(content_form_cita, prioridades, params_default.prioridad_id );
						
						$("body").on("change", "#tipo_exploracion-list", dialogo_cita.change_select_tipo_expl);

					}
					
					$('body').append(content_form_cita);

					$("#agenda-list")
					.add("#medico-list")
					.add("#sala-list");
					/*.selectBoxIt('refresh');*/
					
					var botones = [{
						text: _('Save'),/*IDIOMAOK*/
						click: function() {
							dialogo_cita.paciente_modificado=false; // Asi el close no interfiere
							var params = {};
							params.paciente_id = datos_paciente.id;								
							params.fecha = content_form_cita.find("#campo-fecha").val();
							params.hora = content_form_cita.find("#campo-hora-ini").val();
							params.hora_fin = content_form_cita.find("#campo-hora-fin").val();
							if ( content_form_cita.find("#aseguradora-list").val() !== "" ) {
								params.aseguradora_id = content_form_cita.find("#aseguradora-list").val();
							} else {
								params.aseguradora_id = null;
							}
							
							if (content_form_cita.find("#agenda-list").val() != "-1") {
								params.agenda_id = content_form_cita.find("#agenda-list").val();
							} else {
								alert(_('Debe seleccionar una agenda'));/*IDIOMAOK*/
								return;
							}
							if (content_form_cita.find("#sala-list").val() != "-1") {
								params.sala_id = content_form_cita.find("#sala-list").val();
							}else{
								params.sala_id = null;
							}
							if (content_form_cita.find("#medico-list").val() != "-1") {
								params.medico_id = content_form_cita.find("#medico-list").val();
							}else{
								params.medico_id = null;
							}
							
							if (content_form_cita.find("#tipo_exploracion-list").val() != "-1") {
								params.tipoExploracion_id = content_form_cita.find("#tipo_exploracion-list").val();
							}else{
								params.tipoExploracion_id = null;
							}
							
							if (content_form_cita.find("#priority-list").val() != "-1") {
								params.prioridad_id = content_form_cita.find("#priority-list").val();
							}else{
								params.prioridad_id = null;
							}
							
							params.observaciones = content_form_cita.find("#observaciones").val();
							
							if (datos_cita) {
								//modificar cita
								Endosys.citas.update(TM.gestion_agenda, datos_cita.id, params)
								.done(function() {
									Endosys.statusbar.mostrar_mensaje(_('La cita se ha modificado correctamente'));/*IDIOMAOK*/
									mostrando_dialog.resolve();
								})
								.fail(function(r) {
									if (r.status != 400) {
										Endosys.statusbar.mostrar_mensaje(_('Error al modificar la cita'), 1);/*IDIOMAOK*/
									} else {
										Endosys.statusbar.mostrar_mensaje(_('Los datos de la cita no son válidos'));/*IDIOMAOK*/
									}
								});
							} else {
								//nueva cita
								Endosys.citas.create(TM.gestion_agenda, params)
								.done(function() {
									mostrando_dialog.resolve();
								})
								.fail(function() {
									mostrando_dialog.reject();
								});
							}
							$( this ).dialog( "close" );
						}
					}, {
						text: _('Cancel'),/*IDIOMAOK*/
						click: function() {
							$( this ).dialog( "close" );
						}
					}]
					
					if (datos_cita) {
						botones.push({
                            text: _('Delete'),/*IDIOMAOK*/
                            click:  function() {/*IDIOMAOK*/
                                if(datos_cita){
                                    //eliminar cita
                                    Endosys.citas['delete'](TM.gestion_agenda, datos_cita.id)
                                    .done(function() {
                                        mostrando_dialog.resolve();
                                    });
                                }
                                $( this ).dialog( "close" );
                            }
                        });

					}
					
					$('#content_form_cita').dialog({ 
						modal: true,
						autoOpen: false,
						resizable: false,						
						title: _('Datos de la cita'),/*IDIOMAOK*/
						//show: 'clip', 
						//hide: 'clip',
						//height: 'auto', comentado provisionalmente xq contiene unos selects que se desbordan
						height: 'auto',
						//width: 450,
						width: 860,
						close: function() {
							$('#content_form_cita').dialog( "destroy" );
							$('#content_form_cita').remove();
							//console.log(dialogo_cita.paciente_modificado);
							if (dialogo_cita.paciente_modificado){
								mostrando_dialog.resolve();
							}
						},
						open: function( event, ui ) {
						  	dialogo_cita.paciente_modificado=false;
						},
						buttons: botones
						
					});
					
					$('#content_form_cita').dialog( "open" );

					// Si es nueva cita e
					if (dialogo_cita.is_nueva_cita){
						dialogo_cita.change_select_tipo_expl();	
					}
					
				} else {
					alert(_('Error loading file') + ' nueva_cita.html');/*IDIOMAOK*/
				}
			});
			
			return mostrando_dialog.promise();
		},
		
		pintar_select_prioridades: function(content_form_cita, prioridades ,prioridad_id) {
			var select_prioridad = content_form_cita.find("#priority-list");
			select_prioridad.find("option").remove();
			select_prioridad.append($('<option value="-1">' + _('Seleccione') + '</option>'));	/*IDIOMAOK*/
			if(prioridades){
				for (var i=0; i < prioridades.length; i++) {
					var option = $('<option value='+prioridades[i].id+'>'+prioridades[i].nombre+'</option>');
					option.data("datos_prioridad", prioridades[i]);
					option.appendTo( select_prioridad );
				}
			}
			if (prioridad_id) {
				select_prioridad.find("option[value='" + prioridad_id + "']").attr("selected", true);
			}			
			//select_prioridad.selectBoxIt('refresh');
		},
		pintar_select_tipos_expl: function(content_form_cita, tipos_expl ,tipo_expl_id) {
			var select_tipo_expl = content_form_cita.find("#tipo_exploracion-list");
			select_tipo_expl.find("option").remove();
			select_tipo_expl.append($('<option value="-1">' + _('Seleccione') + '</option>'));	/*IDIOMAOK*/
			if(tipos_expl){
				for (var i=0; i < tipos_expl.length; i++) {
					var option = $('<option value='+tipos_expl[i].id+'>'+tipos_expl[i].nombre+'</option>');
					option.data("datos_tipo_expl", tipos_expl[i]);
					option.appendTo( select_tipo_expl );
				}
			}

			// Hay un tipo de exploracion preseleccionada
			if (tipo_expl_id) {
				select_tipo_expl.find("option[value='" + tipo_expl_id + "']").attr("selected", true);
			}			
			//select_tipo_expl.selectBoxIt('refresh');
		},		
		pintar_select_medicos: function(content_form_cita, datos_agenda, medico_id){
			var select_medico = content_form_cita.find("#medico-list");
			select_medico.find("option").remove();
			select_medico.append($('<option value="-1">' + _('Seleccione') + '</option>'));/*IDIOMAOK*/
			if ( datos_agenda && datos_agenda.medicos) {					
				for (var i=0; i < datos_agenda.medicos.length; i++) {
					var option = $('<option value=' + datos_agenda.medicos[i].id + '>' + datos_agenda.medicos[i].nombre + '</option>');
					option.data("datos_medico", datos_agenda.medicos[i]);
					option.appendTo(select_medico);
				}
			}
			if (medico_id) {
				select_medico.find("option[value='" + medico_id + "']").attr("selected", true);
			}
			//select_medico.selectBoxIt('refresh');
		},
		
		pintar_select_salas: function(content_form_cita, datos_agenda, sala_id){
			var select_sala = content_form_cita.find("#sala-list");
			select_sala.find("option").remove();
			select_sala.append($('<option value="-1">' + _('Seleccione') + '</option>'));/*IDIOMAOK*/
			if ( datos_agenda && datos_agenda.salas) {	
				for (var i=0; i < datos_agenda.salas.length; i++) {
					var option = $('<option value=' + datos_agenda.salas[i].id + '>' + datos_agenda.salas[i].nombre + '</option>');
					option.data("datos_sala", datos_agenda.salas[i]);
					option.appendTo(select_sala);
				}
			}
			if (sala_id) {
				select_sala.find("option[value='" + sala_id + "']").attr("selected", true);
			}
			//select_sala.selectBoxIt('refresh');
		},

		change_select_tipo_expl: function(){
			//console.log("entro");
			var content_form_cita = $("<div id='content_form_cita'></div>");

			tipo_expl_seleccionada = $("#tipo_exploracion-list").val();
			
			for (var i = dialogo_cita.tipos_expl.length - 1; i >= 0; i--) {
				if (dialogo_cita.tipos_expl[i].id==tipo_expl_seleccionada){
					
					// leo la duracion del tipos_expl, si no esta definida me quedo con la 
					// duracion por defecto configurada en el ini, si no esta definida se configura
					// en 30 minutos
					var duracion = dialogo_cita.tipos_expl[i].duracion;
					if (!duracion){
						duracion = opciones_config["GESTION_AGENDA.CITA.TIEMPO_POR_DEFECTO"];
					}

					
					if (duracion){
						
						//Crea una nueva fecha con la hora de inicio - no importa el dia
						var cita_inicio = $("#campo-hora-ini").val();
						cita_inicio = cita_inicio.split(":");
						var hora_ini = cita_inicio[0];
						var minuto_ini = cita_inicio[1];

						hora = new Date();
						hora.setHours(hora_ini);
						hora.setMinutes(minuto_ini);
						hora.setMinutes(hora.getMinutes()+parseInt(duracion,10));
						
						// asigna la hora de inicio mas la duracion al input de hora
						$("#campo-hora-fin").val(hora.getHours() + ":" + hora.getMinutes() );

					}
				}
			}

		},



		
	}


}();	
