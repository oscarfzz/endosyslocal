/* Gestionar la barra que muestra el estado de la aplicación, 
 * Para mostrar la barra usar:
 * Endotools.statusbar.mostrar_mensaje()
 * Parametros:
 *	- Titulo: Texto que se mostrara
 *  - Tipo: 0 Estado normal (informacion) - Por defecto
 *			1 Estado de error
 *  - Duración: Tiempo que se mostrara el mensaje. Por defecto 4000
 *  - id: Para identificar el mensaje con un ID
 */
Endotools.statusbar = function() {
 
	var $overlay;
	var counter = 0;
	var last_hide = 0;
	
	// Inicia un interval que, pasados 10 segundos desde la ultima 
	// vez que se ocultó el statusbar, resetea el counter a 0
	setInterval(function() {
					if (last_hide == 0) return;
					if ( (new Date()).getTime() - last_hide >= 10000 ) {
						last_hide = 0;
						counter = 0;
						$overlay.fadeOut(500);
					}
				}, 10000);


	return {
   
   		duracion: 4000,
		
		init: function() {
			$overlay = $('<div id="mainstatusbar" style="position: absolute; left: 0; top: 0; width: 100%; z-index: 3000"><div>' + _('Ready') + '</div></div>')/*IDIOMAOK*/
			.hide().appendTo($('body'));
		},
		
		mostrar_mensaje: function(msg, tipo, duracion, id) {
			var data_id = (id == undefined ? 0: id);  

			$overlay.attr("data-id", data_id);
			$overlay.removeClass('statusbar-normal').removeClass('statusbar-error');
			if (!tipo){
				$overlay.addClass('statusbar-normal');
			}
			else if (tipo == 1) {
				$overlay.addClass('statusbar-error');
			}
			$overlay.html('<div>' + msg + '</div>');

			if (counter == 0) $overlay.fadeIn(500);
			counter++;
			var d = duracion ? duracion : Endotools.statusbar.duracion;
			setTimeout(function() {				
				counter--;
				if (counter <= 0) {
					$overlay.fadeOut(500);
					counter = 0;
				}else{
					last_hide = (new Date()).getTime();
				}
			}, d);
		},

		cerrar_mensaje: function(id){
			var div = $('#mainstatusbar[data-id="'+id+'"]');
			counter--;				
			if (counter == 0) div.fadeOut(500);
			else last_hide = (new Date()).getTime();
		}

   }
}();
