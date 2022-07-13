var busqueda_por_paciente = function() {

	return {

		paciente_id: null,
		
		mostrar: function() {
			set_titulo_pantalla(_('Exploraciones'));/*IDIOMAOK*/
			activar_asistente();
			//	cargar la pantalla de pacientes
			busqueda_por_paciente._seleccionar_paciente();
		},

		_seleccionar_paciente: function() {
			set_titulo_pantalla(null, _('Seleccionar el paciente'));/*IDIOMAOK*/
			contenido_principal.mostrar(gestion_pacientes, function() {
					//	funcionalidad especifica:				
					//		doble click en paciente: continuar
					gestion_pacientes.datatable_results.subscribe("rowDblclickEvent", function(oArgs) {
								$("#mainnav-continuar-btn").click();
							});
					//		boton continuar y atras
					set_atras(null);
					set_continuar(function() {
									//	comprobar antes que se haya seleccionado un paciente
									if (!gestion_pacientes.paciente_id) {
										Endotools.statusbar.mostrar_mensaje(_('Debe seleccionar un paciente para continuar'), 1);/*IDIOMAOK*/
										return;
									}
									busqueda_por_paciente.paciente_id = gestion_pacientes.paciente_id;									
									busqueda_por_paciente._mostrar_exploraciones();
								});
				}, {
					opcion_deshabilitados: true
				});
		},
		
		_mostrar_exploraciones: function() {
			//	mostrar la pantalla de realizar expl
			set_titulo_pantalla(null, _('Búsqueda por paciente'));/*IDIOMAOK*/
			
			set_atras(function() {
							busqueda_por_paciente.paciente_id = null;
							busqueda_por_paciente._seleccionar_paciente();
					});					
			set_continuar(null);
			
//			gestion_exploraciones.mostrar_por_paciente(busqueda_por_paciente.paciente_id);
//			gestion_exploraciones.por_paciente.mostrar(busqueda_por_paciente.paciente_id);
			contenido_principal.mostrar(gestion_exploraciones.por_paciente, busqueda_por_paciente.paciente_id);
		}
		
	}

}();