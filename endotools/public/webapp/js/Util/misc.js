function is_HTMLElement(e) {
	// En IE no existe la clase HTMLElement, asi que se ha de comprobar asi
	// en firefox funcionaria esto: if (e instanceof HTMLElement) ...
	return ("nodeType" in e && "tagName" in e);
}

function parseEndotoolsBool(oData) {
	// interpretar los 'sí' y 'no' del campo activo como true y false
	/*
		Y.log(oData);
		Y.log(oData.toUpperCase);

		if (oData.toUpperCase) {
			Y.log(oData.toUpperCase());
		}
	*/

	if ((oData == true) || (oData == '1') || (oData == 'sí') || (oData == 'Sí')) {
		return true;
		// } else if ((oData.toUpperCase) && (oData.toUpperCase() == 'SI')) {
		// return true;
	} else if (oData.toUpperCase) {
		if (oData.toUpperCase() == 'SI') return true;
	} else if ((oData == false) || (oData == '0')) {
		return false;
		// } else if ((oData.toUpperCase) && (oData.toUpperCase() == 'NO')) {
		// return false;
	} else if (oData.toUpperCase) {
		if (oData.toUpperCase() == 'SI') return false;
	}

	return false;
}

function seconds_to_hhmmss(segundos) {
	// convierte un numero de segundos en un string HH:MM:SS
	// el param segundos debe ser un numero, si no se dará error
	var mins = Math.floor(segundos / 60);
	var secs = String(segundos % 60);
	var hours = String(Math.floor(mins / 60));
	var mins = String(mins % 60);

	secs = (secs.length == 1) ? '0' + secs : secs;
	mins = (mins.length == 1) ? '0' + mins : mins;

	return hours + ':' + mins + ':' + secs;
}

function loadCss(url) {
	// cargar de forma dinámica un archivo CSS
	// XXX	de momento no se usa, se hace con un plugin de RequireJS (CSSLoader)
	var link = document.createElement("link");
	link.type = "text/css";
	link.rel = "stylesheet";
	link.href = url;

	document.getElementsByTagName("head")[0].appendChild(link);
}

function Yto$(e) {
	// convierte un elemento de YUI 2 o 3 (Y.Node, etc...)
	// a uno de jQuery. A malas, lo trata como un HTMLElement o
	// selector. Siempre devuelve un objeto jquery
	if (e && e._node) {
		// si es de YUI 3, usar e._node
		return $(e._node);
	} else if (e && e.get) {
		// si no es de YUI 3 comprobar si es de YUI 2 mirando
		// si tiene la funcion get()
		return $(e.get('element'));
	} else {
		return $(e);
	}
}

// DataSource de YUI para usar con los DataTables que realmente no lo llegan a utilizar.
// Esta situación se da con el paso a jQuery.
var dummyDataSource = new YAHOO.util.DataSource();

function calcular_edad(fecha_nacimiento, dia_actual) {
	// calcula la edad (en años) dada una fecha de nacimiento y el dia actual.
	// fecha_nacimiento	string (DD/MM/YYYY)
	// dia_actual			string (DD/MM/YYYY) si se omite se utiliza el dia de hoy
	if (fecha_nacimiento) {
		var f = fecha_nacimiento.split('/');
		f = new Date(f[2], f[1] - 1, f[0]);

		var d = new Date();
		if (dia_actual) {
			d = dia_actual.split('/');
			d = new Date(d[2], d[1] - 1, d[0]);
		}

		// la diferencia entre 2 fechas devuelve los milisegundos transcurridos,
		// que se convierten a años... pensandolo bien, esto no permite calcular una edad precisa!
		// (d - f) / (1000*60*60*24*...);

		// mejor restar directamente el año y luego comprobar por dia y mes si ya ha cumplido el actual o no
		var edad = d.getFullYear() - f.getFullYear();
		if (d.getMonth() < f.getMonth()) {
			edad = edad - 1;
		} else if (d.getMonth() == f.getMonth()) {
			if (d.getDate() < f.getDate()) {
				edad = edad - 1;
			}
		}

		return edad;
	} else {
		return '';
	}
}

/*
 *
 * Base64 encode / decode
 * http://www.webtoolkit.info/
 * 
 * 
 *
 */

/*
var Base64 = {
	// private property
	_keyStr : "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=",

	// public method for encoding
	encode : function (input) {
		var output = "";
		var chr1, chr2, chr3, enc1, enc2, enc3, enc4;
		var i = 0;

		input = Base64._utf8_encode(input);

		while (i < input.length) {
			chr1 = input.charCodeAt(i++);
			chr2 = input.charCodeAt(i++);
			chr3 = input.charCodeAt(i++);

			enc1 = chr1 >> 2;
			enc2 = ((chr1 & 3) << 4) | (chr2 >> 4);
			enc3 = ((chr2 & 15) << 2) | (chr3 >> 6);
			enc4 = chr3 & 63;

			if (isNaN(chr2)) {
				enc3 = enc4 = 64;
			} else if (isNaN(chr3)) {
				enc4 = 64;
			}

			output = output +
			this._keyStr.charAt(enc1) + this._keyStr.charAt(enc2) +
			this._keyStr.charAt(enc3) + this._keyStr.charAt(enc4);
		}

		return output;
	},

	// public method for decoding
	decode : function (input) {
		var output = "";
		var chr1, chr2, chr3;
		var enc1, enc2, enc3, enc4;
		var i = 0;

		input = input.replace(/[^A-Za-z0-9\+\/\=]/g, "");

		while (i < input.length) {
			enc1 = this._keyStr.indexOf(input.charAt(i++));
			enc2 = this._keyStr.indexOf(input.charAt(i++));
			enc3 = this._keyStr.indexOf(input.charAt(i++));
			enc4 = this._keyStr.indexOf(input.charAt(i++));

			chr1 = (enc1 << 2) | (enc2 >> 4);
			chr2 = ((enc2 & 15) << 4) | (enc3 >> 2);
			chr3 = ((enc3 & 3) << 6) | enc4;

			output = output + String.fromCharCode(chr1);

			if (enc3 != 64) {
				output = output + String.fromCharCode(chr2);
			}
			if (enc4 != 64) {
				output = output + String.fromCharCode(chr3);
			}
		}

		output = Base64._utf8_decode(output);
		return output;
	},

	// private method for UTF-8 encoding
	_utf8_encode : function (string) {
		string = string.replace(/\r\n/g,"\n");
		var utftext = "";

		for (var n = 0; n < string.length; n++) {
			var c = string.charCodeAt(n);

			if (c < 128) {
				utftext += String.fromCharCode(c);
			}
			else if((c > 127) && (c < 2048)) {
				utftext += String.fromCharCode((c >> 6) | 192);
				utftext += String.fromCharCode((c & 63) | 128);
			}
			else {
				utftext += String.fromCharCode((c >> 12) | 224);
				utftext += String.fromCharCode(((c >> 6) & 63) | 128);
				utftext += String.fromCharCode((c & 63) | 128);
			}
		}

		return utftext;
	},

	// private method for UTF-8 decoding
	_utf8_decode : function (utftext) {
		var string = "";
		var i = 0;
		var c = c1 = c2 = 0;

		while ( i < utftext.length ) {
			c = utftext.charCodeAt(i);

			if (c < 128) {
				string += String.fromCharCode(c);
				i++;
			}
			else if((c > 191) && (c < 224)) {
				c2 = utftext.charCodeAt(i+1);
				string += String.fromCharCode(((c & 31) << 6) | (c2 & 63));
				i += 2;
			}
			else {
				c2 = utftext.charCodeAt(i+1);
				c3 = utftext.charCodeAt(i+2);
				string += String.fromCharCode(((c & 15) << 12) | ((c2 & 63) << 6) | (c3 & 63));
				i += 3;
			}
		}

		return string;
	}
}
*/

// mensaje en pantalla que indica que la tarea ha sido creada con exito
function crear_alerta(contenido, time) {
	// time puede ser false, y queda visible para siempre
	if (time == undefined) {
		time = 5000;
	}

	var defaults = {
		layout: 'bottomRight',
		theme: opciones_config.THEME_ENDOTOOLS,
		type: 'information',
		text: contenido,
		dismissQueue: true,
		template: '<div class="noty_message"><span class="noty_text"></span><div class="noty_close"></div></div>',
		timeout: time,
		force: false,
		modal: false,
		maxVisible: 10,
		killer: false,
		closeWith: ['click'],
		callback: {
			onShow: function () { },
			afterShow: function () { },
			onClose: function () { },
			afterClose: function () { },
			onCloseClick: function () { },
		},
		buttons: false // an array of buttons
	};

	n = noty(defaults);
}

// --------------- Refresco Manual ---------------------
//se llama desde main.js
var handler_refresco = function () {
	return "You work will be lost.";
};

function set_prevenir_refresco_manual() {
	$(window).bind('beforeunload', handler_refresco);
}

function unset_prevenir_refresco_manual(retorno_milisegundos) {
	$(window).unbind('beforeunload', handler_refresco);

	if (retorno_milisegundos != undefined) {
		setTimeout(function () {
			set_prevenir_refresco_manual();
		}, retorno_milisegundos);
	}
}

/*
 *	Captura LInk endotools web client
 *	Evitar que aparezca el cartel de cierre de ventana por x tiempo
 *	Sirve para abrir un link y que no aparezca el cartel y se active
 *	automaticamente de nuevo.
 */
$("body").on("click", "#captura_link", function (e) {
	unset_prevenir_refresco_manual(1000);

	return true;
});

// --------------- Refresco Manual ---------------------
var cargando = function () {
	return {
		_debug: false,
		_peticiones_vivas: 0,
		_url_excluidas: [
			'/rest/notificaciones.json?',
			'/rest/capturas.json',
		],

		show: function (url) {
			var url_admitida = true;

			for (var i = 0; i < cargando._url_excluidas.length; i++) {
				if (url.indexOf(cargando._url_excluidas[i]) != -1) {
					//if (cargando._url_excluidas[i].indexOf(url) != -1){
					url_admitida = false;
				}
			}

			if (url_admitida) {
				cargando._peticiones_vivas += 1;

				if (cargando._peticiones_vivas) {
					cargando.crear_si_no_existe();
				}

				if (cargando._debug) {
					console.log(cargando._peticiones_vivas);
				}

				cargando._elemento.show();
			}
		},

		hide: function (url) {
			var url_admitida = true;

			for (var i = 0; i < cargando._url_excluidas.length; i++) {
				if (url.indexOf(cargando._url_excluidas[i]) != -1) {
					//if (cargando._url_excluidas[i].indexOf(url) != -1){
					url_admitida = false;
				}
			}

			if (url_admitida) {
				cargando._peticiones_vivas -= 1;

				if (cargando._peticiones_vivas <= 0) {
					if (cargando._elemento) {
						cargando._elemento.hide();
					}

					cargando._peticiones_vivas -= 1;

					if (cargando._peticiones_vivas <= 0) {
						cargando._peticiones_vivas = 0;
					}
				}
			}

			if (cargando._debug) {
				console.log(cargando._peticiones_vivas);
			}
		},

		crear_si_no_existe: function () {
			if ($("#cargando").length == 0) {
				$('<div id="cargando"><span>' + _('Cargando...') + '</span></div>').appendTo("body");
			}

			// TODO: sacar esto despues ponerlo en css
			// $("#cargando").attr("style","background-color: red; color: white; font-weight: bold; padding:5px; position:fixed; top:0; left:0;z-index:9999999; display:none")
			cargando._elemento = $("#cargando");
		},
	}
}();


/* SANAR html*/
String.prototype.sanitizeHTML = function (white, black) {
	if (!white) white = "b|i|p|br";	// allowed tags
	if (!black) black = "script|object|embed";	// complete remove tags

	var e = new RegExp("(<(" + black + ")[^>]*>.*</\\2>|(?!<[/]?(" + white + ")(\\s[^<]*>|[/]>|>))<[^<>]*>|(?!<[^<>\\s]+)\\s[^</>]+(?=[/>]))", "gi");
	return this.replace(e, "");
}

// convierte un color hexadecimal a rgb - usado para gestion de citas
function hexToRgb(hex) {
	// Expand shorthand form (e.g. "03F") to full form (e.g. "0033FF")
	var shorthandRegex = /^#?([a-f\d])([a-f\d])([a-f\d])$/i;

	hex = hex.replace(shorthandRegex, function (m, r, g, b) {
		return r + r + g + g + b + b;
	});

	var result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
	return result ? {
		r: parseInt(result[1], 16),
		g: parseInt(result[2], 16),
		b: parseInt(result[3], 16)
	} : null;
}

function textColorForBg(bg_rgb) {
	// Color brightness is determined by the following formula:
	// ((Red value X 299) + (Green value X 587) + (Blue value X 114)) / 1000
	if (bg_rgb) {
		var lightness = Math.round(((parseInt(bg_rgb.r) * 299) + (parseInt(bg_rgb.g) * 587) + (parseInt(bg_rgb.b) * 114)) / 1000);

		if (lightness > 125) {
			return "#222222";
		} else {
			return "white";
		}
	} else {
		return "white";
	}
}

function ew_version_param(format) {
	if (format == undefined) {
		return "?v=" + version;
	} else if (format == 1) {
		return "v=" + version;
	} else {
		return "?v=" + version;
	}
}

// Imprimir un datatable
var gestion_imprimir = function () {
	return {
		opciones: {
			fuente: '10pt',
			titulo: '',
			ocultar_columnas: [],
		},

		tabla_el: undefined,

		_obtener_tabla: function () {
			// Extraer la tabla
			var tabla_el = document.getElementById("datatable_busqueda_result");
			tabla_el = tabla_el.getElementsByClassName("yui-dt-bd")[0];
			tabla_el = tabla_el.getElementsByTagName("table")[0];
			gestion_imprimir.tabla_el = tabla_el;
		},

		imprimir: function () {
			gestion_imprimir._obtener_tabla();

			if (gestion_imprimir.opciones.titulo == "") {
				gestion_imprimir.opciones.titulo = _('Resultados');	// IDIOMAOK
			}

			// Escribir la tabla
			newWin = window.open("");
			newWin.document.write(gestion_imprimir.tabla_el.outerHTML);
			newWin.document.title = gestion_imprimir.opciones.titulo;

			// Asignarle estilos
			var style = "<style> " +
				"	body, html{ margin:0px } " +
				"	table, td, th{ font-family: 'Arial'; font-size: " + gestion_imprimir.opciones.fuente + ";} " +
				"	table td, table th{border:1px solid black;} " +
				"	table {border-spacing:0px; border:1px solid black;} " +
				"	th, td {padding:3px} " +
				"   table, tr, td, th { page-break-inside: avoid !important;  page-break-before: avoid !important; page-break-after: avoid !important;} " +
				"   @media print{ html, body, table, td, th{ background:white; font-family: 'Arial'; font-size: " + gestion_imprimir.opciones.fuente + ";} " + "}";

			if (gestion_imprimir.opciones.ocultar_columnas) {
				for (var i = 0; i < gestion_imprimir.opciones.ocultar_columnas.length; i++) {
					style += " th:nth-child(" + gestion_imprimir.opciones.ocultar_columnas[i] + "), ";
					style += " td:nth-child(" + gestion_imprimir.opciones.ocultar_columnas[i] + ") ";
					style += " {display:none;}";
				}
			}

			style += "</style>";

			newWin.document.write(style);
			newWin.document.close();
			newWin.print();
			gestion_imprimir.opciones.ocultar_columnas = [];
			newWin.close();
		},

		imprimir_con_dialog: function (new_opciones) {
			// si vienen opciones, sobreescribir las por defecto
			for (var opcion in new_opciones) {
				gestion_imprimir.opciones[opcion] = new_opciones[opcion];
			}

			controles.modal_dialog.mostrar({
				title: _('Configuración de impresión'),	// IDIOMAOK
				width: 400,
				height: "auto",
				buttons: { Aceptar: _("Imprimir") },	// IDIOMAOK
				resizable: true,
				enterAccept: false,
				result: function () {
					gestion_imprimir.imprimir();
				},
				init: function (accept) {
					gestion_imprimir._obtener_tabla();
					tabla_cols = gestion_imprimir.tabla_el.getElementsByTagName("thead")[0];
					tabla_cols = gestion_imprimir.tabla_el.getElementsByTagName("tr")[0];
					tabla_cols = gestion_imprimir.tabla_el.getElementsByTagName("th");

					// Mostrar las columnas
					columnas_html = '';
					columnas_html += '<div class="col-imprimir">';
					columnas_html += '<p class="p-imprimir"><strong>' + _("Columnas") + '</strong></p>';	// IDIOMAOK

					for (var i = 0; i < tabla_cols.length; i++) {
						var col_index = parseInt(i + 1);

						if (gestion_imprimir.opciones.ocultar_columnas.indexOf(col_index) == -1) {
							if ($(tabla_cols[i].outerHTML).text() == "") {
								gestion_imprimir.opciones.ocultar_columnas.push(col_index);
							} else {
								columnas_html += '<label><input type="checkbox" class="col_seleccionadas" name="col_seleccionadas" value="' + (i + 1) + '" checked /> ' + $(tabla_cols[i].outerHTML).text() + "</label><br/>";
							}
						}
					}

					columnas_html += '</div>';

					this.append(columnas_html);

					// configurar el tamaño de la fuente
					tamanio_fuente_html = '<div class="col-imprimir">';
					tamanio_fuente_html += '<p class="p-imprimir"><strong>' + _("Tamaño de fuente") + '</strong></p>';	// IDIOMAOK
					tamanio_fuente_html += '<label><input type="radio" class="imprimir-tamanio" name="tamanio" value="8pt"> ' + _("Pequeño") + '</label><br>';
					tamanio_fuente_html += '<label><input type="radio" class="imprimir-tamanio" name="tamanio" value="10pt" checked> ' + _("Mediano") + '</label><br>';
					tamanio_fuente_html += '<label><input type="radio" class="imprimir-tamanio" name="tamanio" value="12pt"> ' + _("Grande") + '</label><br>';

					ayuda_html = '<div class="ui-state-highlight ui-corner-all ayuda-imprimir" style="padding: 0 .7em;"><p><strong>' + _("Ayuda") + ': </strong>' + _("Para una mejor impresión use orientación horizontal, seleccione menos columnas, y configure el tamaño de la fuente.") + '</p></div>';	// IDIOMAOK
					ayuda_html += '</div>';

					this.append(tamanio_fuente_html + ayuda_html);

					$("body").off("change", ".col_seleccionadas", gestion_imprimir.evento_change_columna);
					$("body").on("change", ".col_seleccionadas", gestion_imprimir.evento_change_columna);
					$("body").off("change", ".imprimir-tamanio", gestion_imprimir.evento_change_fuente);
					$("body").on("change", ".imprimir-tamanio", gestion_imprimir.evento_change_fuente);
				}
			});
		},

		evento_change_columna: function (e) {
			el = $(e.target);
			var col_index = parseInt(el.val());

			if (el.prop("checked") == false) {
				if (gestion_imprimir.opciones.ocultar_columnas.indexOf(col_index) == -1) {
					gestion_imprimir.opciones.ocultar_columnas.push(col_index);
				}
			} else {
				if (gestion_imprimir.opciones.ocultar_columnas.indexOf(col_index) != -1) {
					gestion_imprimir.opciones.ocultar_columnas.splice(gestion_imprimir.opciones.ocultar_columnas.indexOf(col_index), 1);
				}
			}
		},

		evento_change_fuente: function (e) {
			gestion_imprimir.opciones.fuente = $('input[name="tamanio"]:checked').val();
			// console.log($('input[name="tamanio"]:checked').val());
		},
	}
}();

function parseError(responseText) {
	if (responseText) {
		data = JSON.parse(responseText);

		if (data && data.data) {
			return data.data;
		} else {
			return _("Ocurrió un error");	// IDIOMAOK
		}
	}
}

// Para Test
function peticion_rest(cantidad, params) {
	if (!cantidad) {
		cantidad = 1;
	}

	if (!params) {
		params = {
			'estado': '1',
			'fecha_min': '01/01/2015',
			'fecha_max': '31/10/2016',
			'servicio_activo': '1',
			'_pagina': '1'
		};
	}

	for (var i = 0; i < cantidad; i++) {
		console.log(i);
		var t0 = performance.now();

		Endotools.exploraciones.index(TM.operaciones, params).then(function () {
			var t1 = performance.now();
			console.log("Exploraciones: " + (t1 - t0) + " milliseconds.");
			// var t0 = performance.now();
			// Endotools.servicios.index(TM.operaciones, {});
		});
	}
}

function cargar_multiselect_servicios(el_multiselect, centros, workstation) {
	/*
	 *	Parametros:
	 *	el_multiselect: el elemnto que es el control multiselect (ej. $("#elmultiselect") )
	 *	centros: Rest index de centros
	 *	workstation: el workstation con sus servicios. Es importante que tenga un .servicios
	 */
	for (var i = 0; i < centros.length; i++) {
		var $op_group = $('<optgroup value="' + centros[i].id + '" label="' + centros[i].nombre + '"></optgroup>');

		for (var j = 0; j < centros[i].servicios.length; j++) {
			var $op = $('<option value="' + centros[i].servicios[j].id + '">' + centros[i].servicios[j].nombre + '</option>');

			// marcar los seleccionados
			if ($.grep(workstation.servicios, function (s) { return s.id == centros[i].servicios[j].id }).length) {
				$op.attr('selected', '');
			}

			$op_group.append($op);
		}

		el_multiselect.append($op_group);
	}

	el_multiselect.multiselect('refresh');
}

// TOGGLE INPUTS
$(document).on("change", ".toggle input", function () {
	if ($(this).is(':checked')) {
		$(this).closest(".toggle").removeClass("off");
	} else {
		$(this).closest(".toggle").addClass("off");
	}
});