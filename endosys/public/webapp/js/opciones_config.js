var opciones_config = function() {
	
	return {
	
		inicializar_basicas: function() {
			/*
			Inicializa las opciones de config. que no requieren que haya un usuario autenticado
			*/
			return Endosys.opciones_config.index(TM.operaciones, {'basicas': true}).done(function(results) {
				//	guardarlas
				for (var n=0; n < results.length; n++) {
					var v = results[n].valor;
					if ($.isNumeric(v)) v = Number(v);
					opciones_config[results[n].id] = v;
					opciones_config[results[n].id.toLowerCase()] = v;
				}
			});
		}
		
		,inicializar: function() {
			/*
			Inicializa las opciones de config. para el usuario autenticado
			*/
			return Endosys.opciones_config.index(TM.operaciones).done(function(results) {
				//	guardarlas
				for (var n=0; n < results.length; n++) {
					var v = results[n].valor;
					if ($.isNumeric(v)) v = Number(v);
					opciones_config[results[n].id] = v;
					opciones_config[results[n].id.toLowerCase()] = v;
				}
				
				//	aplicar las de inicio
				opciones_config._aplicar_iniciales();
			});
		}
		
		,_aplicar_iniciales: function() {
			//	despues de cargarlas, aplicar algunas opciones
			//		MOSTRAR_BOTONES_MODIFICACION_PACIENTES
			//		MOSTRAR_OPCION_NUEVA_EXPLORACION
			//		MOSTRAR_OPCION_GESTION_CITAS
			//		FIRMA_ELECTRONICA.ACTIVO
			//		DEVELOPMENT
			$("#optional_styles").remove();	//	si ya existia el style, lo quita
			var css_style = "<style id='optional_styles' type='text/css'>";
			
			if (!opciones_config.MOSTRAR_BOTONES_MODIFICACION_PACIENTES) {
				css_style += "#nuevo_paciente_btn {display: none;}";
			}
			
			//	FIRMA_ELECTRONICA.ACTIVO: 0 - solo sin firmar, 1 - las dos posibilidades, 2 - solo firmados
			if (opciones_config['FIRMA_ELECTRONICA.ACTIVO'] == '2') {
				//	solo firmado
				css_style += "#exploracion-generar-btn {display: none;}";
			} else if (opciones_config['FIRMA_ELECTRONICA.ACTIVO'] == '0') {
				//	solo sin firma
				css_style += "#exploracion-generarfirmado-btn {display: none;}";
			}
			
			css_style += "</style>";					
			$(css_style).appendTo("head");
			
			//		FORMULARIOS.LABELS.MODO,
			//		FORMULARIOS.LABELS.ANCHO y
			//		FORMULARIOS.LABELS.FONTSIZE
			if (opciones_config['FORMULARIOS.LABELS.MODO']) {
				var n = parseInt(opciones_config['FORMULARIOS.LABELS.MODO'],10);
				GridPositioned.prototype.MODO_CAMPOS = n;
			}
			if (GridPositioned.prototype.MODO_CAMPOS == 2) {
				if (opciones_config['FORMULARIOS.LABELS.ANCHO']) {
					var n = parseInt(opciones_config['FORMULARIOS.LABELS.ANCHO'],10);
					$.rule('.tab_exploracion table.modo_campos_2 .titulo-campo').append('width:' + (n-6) + 'px');
					//	en IE 7 no poner este padding-left!
					//	XXX ojo, browser() ya no está disponible en jquery 1.9 ...
					if (!($.browser.msie && ($.browser.version == "7.0"))) {
						$.rule('.tab_exploracion table.modo_campos_2 div.modo_campos_2-wrapper').append('padding-left:' + n + 'px');
					}
				}
				if (opciones_config['FORMULARIOS.LABELS.FONTSIZE']) {
					$.rule('.tab_exploracion table.modo_campos_2 .titulo-campo').append('font-size:' + opciones_config['FORMULARIOS.LABELS.FONTSIZE']);
				}
			}

			// Gestiona la altura de la agenda segun parametro de configuración en el ini -- Por defecto 20px
			$("<style type='text/css'> .fc-agenda-slots td div { height: "+opciones_config["GESTION_AGENDA.CELDA.ALTURA"]+"px; } </style>").appendTo("head");

		}

	}


}();