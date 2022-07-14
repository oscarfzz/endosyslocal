var tipos_exploracion = function() {

	var datatable_results;
	
	return {
	
		tipo_exploracion_id: null,
		datatable_results: undefined,
		values: {},

		_crear_boton: function(tipoexploracion_id, nombre, es_mini, $contenedor, o, multiples_columnas) {
			//	es_mini: boolean indicando si se le añade la clase 'mini' para hacerlo mas pequeño
			var btn = $('<button id="' + 'tipos-exploracion-btn-' + tipoexploracion_id + '">' + nombre + '</button>').appendTo($contenedor).button();
			if (es_mini) btn.addClass('mini');
			btn.addClass(multiples_columnas ? 'multiples-columnas' : 'una-columna');
			btn.click(function() {
				$("#tipos_exploracion button").removeAttr("disabled");
				$("#tipos_exploracion button").removeClass("ui-state-focus");
				$("#tipos_exploracion button").removeClass("ui-state-hover");
				$(this).attr("disabled", true);
				$(this).addClass("ui-state-focus");
				tipos_exploracion.tipo_exploracion_id = tipoexploracion_id;
				if (o && o.onBtnClick) o.onBtnClick(tipoexploracion_id);
			});
		},
		
		mostrar: function(default_tipo_exploracion_id, o) {
				//	o.onBtnClick, o.callback
				//	si se indica un default_tipo_exploracion_id, será el seleccionado por defecto
				TM.content_tiposExploracion.activate();
				Endosys.statusbar.mostrar_mensaje(_('Cargando tipos de exploración...'));/*IDIOMAOK*/
				
				TM.content_tiposExploracion.load_content(mainlayout, "content/tipos_exploracion.html"+ew_version_param())
				
				.then(function() {

					var params = {activo:1, servicio_id:''};
					if ( Endosys.auth.servicio_activo && Endosys.auth.servicio_activo.id){
						params.servicio_id = Endosys.auth.servicio_activo.id;
					}

					return Endosys.tipos_exploracion.index(TM.content_tiposExploracion, params)
				})
				
				.done(function(tiposexpl) {
					//	crear un boton por cada tipo de expl.
					//		si se ha indicado un default_tipo_exploracion_id, primero crear ese en un div y luego el resto en otro
					var $container = $('#tipos_exploracion');
					if (default_tipo_exploracion_id) {
						var $defaultbtn_container = $('<div><p style="text-align: center">' + _('Éste es el tipo de exploración programado') + '</p></div>');/*IDIOMAOK*/
						$('#tipos_exploracion').append($defaultbtn_container);
						
						$container = $('<div><p style="text-align: center">' + _('Puede seleccionar otro tipo de exploración diferente') + '</p></div>');/*IDIOMAOK*/
						$('#tipos_exploracion').append($container);

						for (var n=0; n < tiposexpl.length; n++) {
							if (tiposexpl[n].id == default_tipo_exploracion_id) {
								tipos_exploracion._crear_boton(tiposexpl[n].id, tiposexpl[n].nombre, false, $defaultbtn_container, o, false);
								break;
							}
						}
					}
					
					//		crear el resto de botones
					var multiples_columnas = (opciones_config['TIPOS_EXPLORACION.BOTONES.MULTIPLES_COLUMNAS'] == '1');
					for (var n=0; n < tiposexpl.length; n++) {
						// graba los valores en un estructura de diccionario para luego ser consultada en otros lugares del sistema
						// ejemplo: Ir hacia Atras
						tipos_exploracion.values[tiposexpl[n].id] =tiposexpl[n].nombre;
	
						if ((default_tipo_exploracion_id) && (tiposexpl[n].id == default_tipo_exploracion_id)) continue;
						tipos_exploracion._crear_boton(tiposexpl[n].id, tiposexpl[n].nombre, (default_tipo_exploracion_id), $container, o, multiples_columnas);
					}
					
					Endosys.statusbar.mostrar_mensaje(_('Ready'));	/*IDIOMAOK*/
					if (o && o.callback) o.callback();
				});
		}

	}


}();