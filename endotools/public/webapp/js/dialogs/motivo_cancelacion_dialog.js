var motivo_cancelacion_dialog = function() {

	return {

		mostrar: function(exploracion_id) {
			return controles.modal_dialog.mostrar({
				title: _('Motivo de cancelación'), width: '360px', height: 'auto',/*IDIOMAOK*/
				
				init: function(accept) {
					//	inicializar el contenido
					//this.addClass('motivocancelacion-dialog');
					this.append( $('<select id="motivos-cancelacion-select" size="10" multiple="multiple"></select>') );
					var $select = $('#motivos-cancelacion-select');
					$select.dblclick(function() { accept(); });
					
					//	llenar la lista con los motivos de fallo
					$select.empty();
					Endotools.motivos_cancelacion.index(TM.operaciones)
					.done(function(results) {
						for (var i=0; i < results.length; i++) {
							$select.append( $('<option  value="' + results[i].id + '">' + results[i].nombre + '</option>') );
						}
						$select.width("100%"); // linea especifica para solucinar un BUG de IE 9, el select no coge los anchos
											   // hay que repintar, suele pasar en las cargas dinamicas
					});					
				}
				
				,check: function() {
					return $('#motivos-cancelacion-select').val() && ($('#motivos-cancelacion-select').val().length == 1);
				}
				
				,result: function() {
					return $('#motivos-cancelacion-select').val()[0];
				}
				
			});
		}

	}

}();