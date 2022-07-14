/*
Dialogo para mostrar lista de plantillas. Utiliza controles.modal_dialog.

TODO:
	-Al cargar las plantillas guardarlas en una cache para no pedirlas cada vez al servidor.
*/

var plantillas_dialog = function() {

	return {
		
		mostrar: function(exploracion_id) {
			return controles.modal_dialog.mostrar({
				title: _('Plantillas de informes'), width: 580, height: 500,/*IDIOMAOK*/
				
				init: function(accept) {
					//	inicializar el contenido
					this.append( $('<div><label>' + _('Comentarios') + '</label></div>') );
					this.append( $('<div><input style="width: 100%;" name="input_comentarios" /></div><br>') );
					this.append( $('<div><label>' + _('Seleccione una plantilla para generar el informe') + '</label></div>') );/*IDIOMAOK*/
					this.append( $('<div><select style="width: 100%;" name="select_plantillas" size="8" /></div><br>') );
					this.append($(
						'<div style="padding: 0 .7em;" class="ui-state-error ui-corner-all">' +
							'<p><span style="float: left; margin-right: .3em;" class="ui-icon ui-icon-alert"></span>' +
							'<strong>' + _('Atención') + ': </strong>' + _('Antes de generar el informe se guardará cualquier cambio realizado en los datos de la exploración') + '</p>' +/*IDIOMAOK*/
						'</div>'
					));
	
					var $select = this.find('select');
					$select.dblclick(function() {
						//	xxx 	simular click en el Aceptar
						accept();
					});
					
					//	cargar plantillas
					$select.html('<option value="">' + _('Cargando...') + '</option>');/*IDIOMAOK*/
					Endosys.plantillas.obtener(TM.operaciones, exploracion_id)
					.done(function(results) {
						$select.html('');
						for (var n=0; n < results.length; n++) {
							var v = results[n].plantilla;
							//	xxx no se si puede dar problemas poner en el 'value' del option el nombre de la plantilla
							//	quizas seria mejor indexarlos y poner el indice
							//	parece que no hay problema: http://stackoverflow.com/questions/6064135/valid-characters-in-option-value
							var $option = $('<option value="' + v + '">' + informes.nombre_sin_extension(informes.nombre_sin_ruta(v)) + '</option>');
							$select.append($option);
						}
						//reasignar el ancho por un bug en ie8 y ie9
						//$select.css('width', '441px');
						$select.css('width', '100%');
						//$select.width("100%");
						
					});
				},
				
				check: function() {
					result = {}
					result.plantilla = this.find('select').val();
					result.comentarios = this.find('input').val();
					return result;
				},
				
				result: function() {
					result = {}
					result.plantilla = this.find('select').val();
					result.comentarios = this.find('input').val();
					return result;
				}
				
			});
		}
	}


}();