var cierre_sesion = function() {

	return {

		_debug: false,				// Muestra los console.log
		_activo: true, 				// Activo por defecto
		_activo_aviso: true,		// True si se quiere dar aviso que se va a cerrar la session
		_tiempo: 0,  				// Cantidad de tiempo del timeout de cierre de sesión
		_tiempo_aviso: 0, 			// Cantidad de tiempo antes de que se cumpla el _tiempo, donde lanza un aviso
		_to_sesion: null, 			// TIMEOUT de la sesión
		_to_aviso: null,			// TIMEOUT del aviso de cierre de sesión
		_it_aviso_contador: null,	// INTERVAL Cuenta regresiva del aviso
		_estado_contador: 0,		// Cantidad de segundos que faltan para que termine el aviso de cierre.
		_dialog_aviso: null,


		// Activa el cierre automatico de sesion. Solo lo activa si CIERRE_SESION.ACTIVO=1
		activar: function(){
			// Desactivo primero
			
			cierre_sesion._activo = (opciones_config['CIERRE_SESION.ACTIVO']==1) ? true : false;
			
			if (cierre_sesion._activo){
				//Limpiar los TO y LO INT
				cierre_sesion.desactivar();

				// Por defecto 8 Horas.
				cierre_sesion._tiempo = (opciones_config['CIERRE_SESION.TIEMPO']) ? opciones_config['CIERRE_SESION.TIEMPO'] : 28800000;
				// Por defecto 30 Segundos antes
				cierre_sesion._tiempo_aviso = (opciones_config['CIERRE_SESION.TIEMPO_AVISO']) ? opciones_config['CIERRE_SESION.TIEMPO_AVISO'] : 30000;
				
				//	Lanza el timeout de la sesion
				cierre_sesion._to_sesion = setTimeout(cierre_sesion._lanzar_logout, cierre_sesion._tiempo);
				if (cierre_sesion._debug) console.log("ON: Cierre de sesión automática");

				// Si el aviso esta activo lanza el timeout del aviso
				if (cierre_sesion._activo_aviso){

					cierre_sesion._to_aviso = setTimeout(cierre_sesion._lanzar_aviso, cierre_sesion._tiempo - cierre_sesion._tiempo_aviso - 1000);
					if (cierre_sesion._debug) console.log("Aviso de cierre de sesión activada");
				}

			}else{

				cierre_sesion.desactivar();
				if (cierre_sesion._debug) console.log("El cierre de sesión automática esta desactivado");

			}

		},

		// Desactiva el cierre de sesion y limpia los interval y timeouts
		desactivar: function(){
			if (cierre_sesion._debug) console.log("OFF: Cierre de sesión automática");
			// Desactivar el cierre de sesion automatico y eliminar los INTERVALS y TIMEOUTS
			cierre_sesion._activo = false;
			clearTimeout(cierre_sesion._to_sesion);
			clearTimeout(cierre_sesion._to_aviso);
			clearInterval(cierre_sesion._it_aviso_contador);
		},

		// Ejecuta el logout 
		_lanzar_logout: function(){
			// Cierre de sesión
			if (cierre_sesion._debug) console.log("Cerrar Sesión");
			Endosys.auth.do_logout();
			set_titulo_pantalla("","");
						
			set_continuar(null);
			set_atras(null);
			set_informacion(null);

			if (cierre_sesion._activo_aviso){
				cierre_sesion._dialog_aviso.dialog('close');
			}

			//cerrar todo los dialogos
			$(".ui-dialog-content").each(function(){
				$(this).dialog("close");
			});

		},

		// Ejecuta el aviso de cierre de sesion
		_lanzar_aviso: function(){
			if (cierre_sesion._debug) console.log("Aviso de Cierre de Sesión Lanzado");

			// Cuenta regresiva del aviso.
			cierre_sesion._it_aviso_contador = setInterval(cierre_sesion._actualizar_aviso_contador, 1000);
			cierre_sesion._estado_contador = cierre_sesion._tiempo_aviso;

			// Muestra el dialog de aviso
			if ($("#sesion-dialog").length==0){
				$('<div id="sesion-dialog"/>').appendTo($('body'));	
			}

			$("#sesion-dialog" ).dialog({
				resizable: false,
				title: _("Cierre automático de sesión"),//IDIOMAOK
				height: 150,
				width:400,
				dialogClass: "dialog_cierre_sesion",
				closeOnEscape: false,
			    modal: true,
			    open: function(event, ui) { 
			    	$("#sesion-dialog .ui-dialog-titlebar-close").hide();
			    	var dialog = $('#sesion-dialog');
					dialog.html(_("Su sesión está por finalizar en: "));//IDIOMAOK
					dialog.append('<span id="sesion_contador">'+ cierre_sesion._estado_contador/1000 +'</span>')
					dialog.append(_(" segundo/s."));//IDIOMAOK
			    },
			 	buttons:[
					{
						text: _('Continuar conectado'),//IDIOMAOK
						click: cierre_sesion._btn_cancelar_cierre,
					}
				]
			});

			/*
			args_dialog = {
				title: _("Cierre automático de sesión"),//IDIOMAOK
				height: 150,
				dialogClass: "dialog_cierre_sesion",
				closeOnEscape: false,
				open: function(event, ui) { $(".ui-dialog-titlebar-close").hide(); },
			 	buttons:[
		    		{
						text: _('Continuar conectado'),//IDIOMAOK
						click: cierre_sesion._btn_cancelar_cierre,
					}
				],
				init: function(accept) 
			    {
					this.append(_("Su sesión está por finalizar en: "));//IDIOMAOK
					this.append('<span id="sesion_contador">'+ cierre_sesion._estado_contador/1000 +'</span>')
					this.append(_(" segundo/s."));//IDIOMAOK						
				},
			}

			controles.modal_dialog.mostrar(args_dialog);
			*/
			cierre_sesion._dialog_aviso = $('#sesion-dialog');
			
		},

		// Actualiza el contador de aviso. actualizado mediante el interval _it_aviso_contador
		_actualizar_aviso_contador: function(){
			cierre_sesion._estado_contador -= 1000;
			if (cierre_sesion._debug) console.log("La sesión se cerrará en " + cierre_sesion._estado_contador/1000 + " segundo/s");
			$("#sesion_contador").text(cierre_sesion._estado_contador/1000);
			if (cierre_sesion._estado_contador <= 0){
				clearInterval(cierre_sesion._it_aviso_contador);
			}
		},

		// Click del boton de cancelar cierre / reinicia el contador de la sesion.
		_btn_cancelar_cierre: function(){
			$(this).dialog("close");
			cierre_sesion.activar();
		}


	}

}();