var dialogo_hora = function() {

	

	return {		
	

		crear_dialogo_hora: function() {
		
			var deferred = $.Deferred();

			var content_form_hora = $("<div id='content_form_hora'></div>");
			content_form_hora.load("content/dialog_hora.html"+ew_version_param(), function(data, textStatus) {
			    
				if (textStatus == "success") {
					content_form_hora.i18n();
					$('body').append(content_form_hora);

					/*$('#campo-diasemana').addClass('selectboxit-small').selectBoxIt({
						copyClasses: "container",	//	necesario para aplicar el estilo
						autoWidth:	true,
						theme:		"jqueryui",
						native:		true	//	al ser el dialog muy pequeño, el dropdown del selectBoxIt no se mostraba entero.
					});*/
					
					var ok = false;
					
					var botones = [{
						text: _('Save'),/*IDIOMAOK*/
						click: function() {
							ok = true;
							$( this ).dialog( 'close' );
						}
					}, {
						text: _('Cancel'),/*IDIOMAOK*/
						click: function() {
							ok = false;
							$( this ).dialog( 'close' );
						}
					}]
					

					
					$('#content_form_hora').dialog({ 
						modal: true,
						autoOpen: false,
						resizable: false,						
						title: _('Datos de la sala'),/*IDIOMAOK*/
						//show: 'clip', 
						//hide: 'clip',
						height: 'auto',
						width: 500,
						close: function() {
							
							if (ok) {
								if (content_form_hora.find("#campo-diasemana").val() != "-1" &&
									content_form_hora.find("#campo-horaini").val() != "" &&
									content_form_hora.find("#campo-horafin").val() != "" ) {
									
									var new_hora = {};
									
									new_hora.dia = {};
									new_hora.dia.codigo = content_form_hora.find("#campo-diasemana").val();
									new_hora.dia.descr = content_form_hora.find("#campo-diasemana option:selected").html();
									new_hora.hora_ini = content_form_hora.find("#campo-horaini").val();
									new_hora.hora_fin = content_form_hora.find("#campo-horafin").val();
									
									deferred.resolve( new_hora );
									

								}else{
									deferred.reject();
									alert(_('Debe rellenar los campos correctamente'));/*IDIOMAOK*/
									
								}
								
							} else {
						
								deferred.reject();

							}
							
							$('#content_form_hora').dialog( "destroy" );
							$('#content_form_hora').remove();
							
							
						},
						buttons: botones
						
					});
					
					$('#content_form_hora').dialog( "open" );
					
	
					
				}else{
					alert(_('Error al cargar el fichero') + ' dialog_hora.html');/*IDIOMAOK*/
				}
			
				
			});
			
			return deferred.promise();
		}



		
	}


}();	