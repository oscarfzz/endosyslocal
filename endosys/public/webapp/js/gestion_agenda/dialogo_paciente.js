var dialogo_paciente = function () {
	return {
		existe_dialog: function () {
			var exist = false;

			if ($('#content_form_paciente').length != 0) {
				exist = true;
			}

			return exist;
		},

		mostrar_dialogo_paciente: function (btn_nuevo_paciente) {
			//	XXX	usar dialog en controles.js
			var datos_paciente;
			var content_form_paciente = $("<div id='content_form_paciente' class='layout-background'></div>");
			var mostrando_dialog = $.Deferred();
			var boton_nuevo_paciente;

			if (btn_nuevo_paciente) {
				boton_nuevo_paciente = true;
			} else {
				boton_nuevo_paciente = false;
			}

			$('body').append(content_form_paciente);
			gestion_pacientes.mostrar_para_dialogo(function () {
				$('#content_form_paciente').dialog({
					modal: true,
					autoOpen: false,
					resizable: false,
					title: _('Seleccionar paciente'),/*IDIOMAOK*/
					height: 720,
					width: 1280,
					close: function () {
						$('#content_form_paciente').dialog("destroy");
						$('#content_form_paciente').remove();
					},
					buttons: [{
						text: _('Seleccionar'),/*IDIOMAOK*/
						click: function () {
							if (gestion_pacientes.paciente_id == null) {
								alert(_('Debe seleccionar un paciente'));//IDIOMAOK
							} else {
								datos_paciente = gestion_pacientes.datos_paciente_seleccionado;
								$(this).dialog("close");
								mostrando_dialog.resolve(datos_paciente);
							}
						}
					}, {
						text: _('Cancelar'),/*IDIOMAOK*/
						click: function () {
							$(this).dialog("close");
							mostrando_dialog.reject();
						}
					}]
				});

				$('#content_form_paciente').dialog("open");
			},
			content_form_paciente, {
				opcion_deshabilitados: false,
				nuevo_paciente: boton_nuevo_paciente
			});

			return mostrando_dialog.promise();
		}
	}
}();