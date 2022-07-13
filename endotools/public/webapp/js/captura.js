/*
*/

function ff_activex_host_logger_func(msg) {
	//	el control ff-activex-host puede enviar sus mensajes de log a
	//	javascript mediante esta función.
	if (console && console.log) {
		console.log('ff-activex-host log: ' + msg);
	}
}

function etcapcontrol_finishcapture() {
	gestion_captura.finishCaptureEvent();
};

function etcapcontrol_finishpost() {
	gestion_captura.finishPostEvent();
};

var gestion_captura = function() {
	
	return {
	
		etcapcontrol: null,
		
		finishCaptureEvent: function() {
			//	Al finalizar la captura enviar las imágenes al servidor
			
			///////gestion_captura.etcapcontrol.enviar_imagenes(gestion_exploraciones.exploracion_id, '/rest/capturas');			
			// De esta forma se indica el protocolo, http: o https: Esto requiere el etcapcontrol 0.4.0
			gestion_captura.etcapcontrol.protocol = document.location.protocol;
			gestion_captura.etcapcontrol.enviar_imagenes2(gestion_exploraciones.exploracion_id, '/rest/capturas');
			
			//	Y recoger los valores de TIEMPO TOTAL y TIEMPO DE RETIRADA
			gestion_exploraciones.set_tiempos_captura(gestion_captura.etcapcontrol.tiempo_total, gestion_captura.etcapcontrol.tiempo_retirada);
		},
		
		finishPostEvent: function() {
			Endotools.statusbar.mostrar_mensaje(_('Se ha finalizado el envío de las imágenes capturadas'));/*IDIOMAOK*/
			
			//	obtener las miniaturas, SOLO SI ESTA EN LA PANTALLA DE EXPLORACIONES!!!
			
			var $tab_imagenes = $('#exploracion-tab-imagenes>.ui-layout-center>ul');
			//var $tab_imagenes = $('#exploracion-tab-imagenes');
			if ($tab_imagenes.length) {
				imagenes_expl.set_transactionmanager(TM.content_exploraciones.detalles.imagenes);
				imagenes_expl.obtener_thumbs(gestion_exploraciones.exploracion_id, $tab_imagenes);
			}
		},
		
		cargarEtCapControl: function($container, ancho, alto, debug_mode) {
			ancho = ancho || 256;
			alto = alto || 80;
			debug_mode = debug_mode ? '1' : '0';
			$container = $container || $('#et-capture-control-container');
			
			var html = null;
			if ($.browser.msie) {
//			if (YA HOO.env.ua.ie) {
				html =			
					'<object	id =		"etCapControl" ' +
					'			classid =	"CLSID:51AD998D-DAC3-43E4-A276-E80A3F1EC70C" ' +
					'			width =		"' + ancho + '" ' +
					'			height =	"' + alto + '" ' +
					'			> ' +
					'	<param name="Debug"		value="' + debug_mode + '"	/> ' +
					'</object> ' +
					
					'<script type="text/javascript" for="etCapControl" event="OnFinishCapture()"> ' +
					'	etcapcontrol_finishcapture(); ' +
					'</script>' + 
					
					'<script type="text/javascript" for="etCapControl" event="OnFinishPost()"> ' +
					'	etcapcontrol_finishpost(); ' +
					'</script>';
			} else {
				html =
					'<object	id = 		"etCapControl" ' +
					'			type = 		"application/x-itst-activex" ' +
					'			width =		"' + ancho + '" ' +
					'			height =	"' + alto + '" ' +
					'			clsid = 					"{51AD998D-DAC3-43E4-A276-E80A3F1EC70C}" ' +
					'			event_OnFinishCapture = 	"etcapcontrol_finishcapture" ' +
					'			event_OnFinishPost = 		"etcapcontrol_finishpost" ' +
					'			param_Debug =				"' + debug_mode + '" ' +
					'			logger = 					"ff_activex_host_logger_func" ' +
					'			debugLevel = 					"5" ' +
					'			> ' +
					'<div></div>' +	//	si se pone algun contenido alternativo al plugin, no aparece el mensaje de firefox indicando que se necesita el plugin
					'</object>';			
			}
			//	IMPORTANTE:	el metodo de jQuery .html() evalua los <script> que hay en html, lo cual
			//				en este caso es incorrecto. Por lo tanto, mejor uso innerHTML().
			//$container.html(html);
			$container.get(0).innerHTML = html;
			gestion_captura.etcapcontrol = document.getElementById('etCapControl');
		},
		
		configurar: function(cfg) {
			//		configurar el etcapcontrol
			if (cfg.port) gestion_captura.etcapcontrol.Port = cfg.port;
			if (cfg.host) gestion_captura.etcapcontrol.Host = cfg.host;
		},
		
		ejecutar_captura: function() {
			gestion_captura.etcapcontrol.ejecutar_captura(gestion_exploraciones.exploracion_id);
		}
		
	}


}();
