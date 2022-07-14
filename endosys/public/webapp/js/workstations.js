// Funciones relativas a los workstations

function get_workstation() {
	//	obtener la info del workstation por la IP (no requiere auth)
	//	devuelve promise
	workstation=null;

	return Endotools.workstations.show(TM.operaciones, 'auto')
	.done(function(_workstation) {
		workstation = _workstation;
		$("#info_puesto").html(workstation.nombre);
	})

	.fail(function(arg) {
		if (arg.status == 404) {
			$("#info_puesto").html("(Puesto no registrado)");
		} else {
			$("#info_puesto").html("(Error identificando el puesto)");
		}
	});

}

function dialog_crear_workstation(){

	return controles.modal_dialog.mostrar({
				title: _('Nuevo puesto'),/*IDIOMAOK*/
				height: 275,
				width: 350,
				dialogClass: "dialog_nuevo_puesto",
				resizable: false,
				enterAccept: false,
				check: function() {
					var container = $("#generic-dialog");
					var nombre = container.find("#workstation-nombre").val();
					if (nombre==null || nombre=='' || nombre==undefined){
						alert(_("El nombre no puede estar vacio"));//IDIOMAOK
						return false;
					}
					return true;
				},
				result: function() {

					// Si elige guardar entonces crea el puesto
					var container = $("#generic-dialog");
					var multiselect_control = container.find("#workstation-servicios");
					var nombre = container.find("#workstation-nombre").val();
					var servicios = multiselect_control.val();
					if (servicios) servicios = multiselect_control.val().join(",");
					
					return {
						'nombre': nombre,
						'servicios': servicios
					}
				},	
				init: function(accept) {
					var container = $("#generic-dialog");
					TM.content_exploraciones.load_content(container, "content/dialog_asignar_servicios_puesto.html"+ew_version_param())
					.done(function() {
						// crear control multiselect
						var multiselect_control = container.find("#workstation-servicios");

						multiselect_control.multiselect({
							header: false,
							minWidth: 300,
							maxWidth: 300,
							selectedList: 3,
							noneSelectedText: _('Ninguno'),/*IDIOMAOK*/
							selectedText: _('# servicios seleccionados...'),/*IDIOMAOK*/
							click: function(event, ui) {},
							cssClass: "multiselect-servicios-autoregistro"
						});

						// cargar los servicios de cada centro
						Endotools.centros.index(TM.operaciones)
						.then(function(centros){
							cargar_multiselect_servicios(multiselect_control, centros, {servicios: []});
						});
						
					});
				}

	})
	// si viene por el done quiere decir que se apreto "aceptar", por lo tanto se
	// crea el workstation con los servicios seleccionados. 
	.then(function(params){
		return Endotools.workstations.create(TM.operaciones, params)
	});


}