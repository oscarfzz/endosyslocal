set_prevenir_refresco_manual();
//alert("test");

/* 	RESET PANTALLA
	==============
	Function que limpia la pantalla de la:
		- Nav. atras y adelante
		- Titulos
		- Informacion

	Y activa  el cierre de sesion automativo si esta activado desde INI,
	salvo que se pase el parametro not_cerrar_sesion que desactiva el cierre
	de sesion.
*/
function reset_pantalla(not_cerrar_sesion) {

	if (not_cerrar_sesion) {
		cierre_sesion.desactivar();
	} else {
		cierre_sesion.activar();
	}

	set_titulo_pantalla(" ", "");
	desactivar_asistente();
	set_informacion(null);
	set_atras(null);
	set_continuar(null);
}


function set_titulo_pantalla(titulo, subtitulo) {
	if (titulo) $("#maintitle-texto-titulo").html(titulo);
	$("#maintitle-texto-subtitulo").html(subtitulo || '');
}

function activar_asistente() {
	$("#mainnav").show();
}

function desactivar_asistente() {
	$("#mainnav").hide();
}


function set_continuar(callback) {
	$("#mainnav-continuar-btn").off('click');
	if (callback) {
		//	habilitar
		$("#mainnav-continuar-btn").button("enable").click(callback);
	} else {
		//	deshabilitar
		$("#mainnav-continuar-btn").button("disable");
	}
}

function set_atras(callback) {
	$("#mainnav-atras-btn").off('click');
	if (callback) {
		//	habilitar
		$("#mainnav-atras-btn").button("enable").click(callback);
	} else {
		//	deshabilitar
		$("#mainnav-atras-btn").button("disable");
	}
}

function set_informacion(callback) {
	$("#maintitle-icon-information").off('click');
	if (callback) {
		//	habilitar
		$("#maintitle-icon-information").show();
		$("#maintitle-icon-information").click(callback);
	} else {
		$("#maintitle-icon-information").hide();
	}
}

function init_asistente() {
	/*$("#mainnav-continuar-btn").button();
	$("#mainnav-atras-btn").button();*/
	$("#mainnav-continuar-btn").button({ icons: { primary: "ui-icon-triangle-1-e" }, text: false });
	$("#mainnav-atras-btn").button({ icons: { primary: "ui-icon-triangle-1-w" }, text: false });
	desactivar_asistente();
}
var __theme_loaded_ie7_8 = false;

function set_endosys_theme(themename) {
	//	quitar CSS links previos


	//	añadir CSS links correspondientes al theme de EndoSys

	if (!($.browser.msie && ($.browser.version == "8.0" || $.browser.version == "7.0"))) {

		$('head link.endosys-theme-link-tag').remove();

		if (themename) {
			//se carga el tema indicado
			$('#ubicacion-theme-css')
				//			.after('<link class="endosys-theme-link-tag" type="text/css" rel="stylesheet" href="themes/' + themename + '/jqueryui/jquery-ui-' + $.ui.version + '.custom.css" />')//jquery-ui <= 1.10
				.after('<link class="endosys-theme-link-tag" type="text/css" rel="stylesheet" href="themes/' + themename + '/jqueryui/jquery-ui.css" />')//jquery-ui 1.11
				.after('<link class="endosys-theme-link-tag" type="text/css" rel="stylesheet" href="themes/' + themename + '/pure-endosys.css" />')
				.after('<link class="endosys-theme-link-tag" type="text/css" rel="stylesheet" href="themes/' + themename + '/endosys.css" />')
				.after('<link class="endosys-theme-link-tag" type="text/css" rel="stylesheet" href="themes/' + themename + '/yui2-datatable-skin.css" />')
				.after('<link class="endosys-theme-link-tag" type="text/css" rel="stylesheet" href="themes/' + themename + '/Jquery-datatable-skin.css" />');
		} else {
			//se carga un tema por defecto
			$('#ubicacion-theme-css').after('<link class="endosys-theme-link-tag" type="text/css" rel="stylesheet" href="/lib/jquery-ui-' + $.ui.version + '.custom/css/smoothness/jquery-ui-' + $.ui.version + '.custom.css" />');// XXX jquery-ui 1.11?
		}
	} else {
		//IE8 IE7
		//condicion de seguridad
		if (!document.createStyleSheet) throw new Error('createStyleSheet method does not exist');

		if (__theme_loaded_ie7_8) throw new Error('Theme already set');
		//lanzar excepcion de que el tema esta cargado y solo se permite cargar una vez para ie7, ni ie8

		if (themename) {
			//cargar tema que se especifica
			//			document.createStyleSheet('themes/' + themename + '/jqueryui/jquery-ui-' + $.ui.version + '.custom.css');//jquery-ui <= 1.10
			document.createStyleSheet('themes/' + themename + '/jqueryui/jquery-ui.css');//jquery-ui 1.11
			document.createStyleSheet('themes/' + themename + '/pure-endosys.css');
			document.createStyleSheet('themes/' + themename + '/endosys.css');
			document.createStyleSheet('themes/' + themename + '/yui2-datatable-skin.css');
			document.createStyleSheet('themes/' + themename + '/Jquery-datatable-skin.css');
		} else {
			//cargar tema por defecto
			document.createStyleSheet('/lib/jquery-ui-' + $.ui.version + '.custom/css/smoothness/jquery-ui-' + $.ui.version + '.custom.css');// XXX jquery-ui 1.11?
		}

		__theme_loaded_ie7_8 = true;

	}

	//	XXX	alguna cosa que va por JS no se actualiza, p.ej. el fondo del header de los datatable YUI2
}

//	MENU PRINCIPAL	//////////////////////

var menu_principal = null;

function _check_effect_wrapper() {
	/*	!!! el div.ui-effects-wrapper se crea durante la animación del menu.
		si se destruye el menu y aun estaba abriendose o cerrandose, no se destruye
		este div, y luego da problemas.
		Esta funcion se asegura de destruirlo.
		OJO: si se añaden otras animaciones podría dar conflictos, ya que esto elimina
		todos los .ui-effects-wrapper
	*/
	$('.ui-effects-wrapper').remove();
}

function mostrar_menu_principal() {
	if (!menu_principal) return false;
	menu_principal.show('slide', { direction: 'left', easing: 'easeOutCubic' }, 300, _check_effect_wrapper);
	$(document).on('mousedown.cierra_menu_principal', function (e) {
		if (!menu_principal.has(e.target).length) {
			ocultar_menu_principal();
		}
	});
	return true;
}

function ocultar_menu_principal() {
	$(document).off('.cierra_menu_principal');
	menu_principal.find('ul').hide();
	menu_principal.hide('slide', { direction: 'left', easing: 'easeOutCubic' }, 300, _check_effect_wrapper);
}

function destruir_menu_principal() {
	if (!menu_principal) return;
	menu_principal.menu('destroy').remove();
	menu_principal = null;
}


function crear_menu_principal(opciones_menu, busquedas_avanzadas) {
	/*
		busquedas_avanzadas	todas las busquedas avanzadas
		opciones_menu		array, ver userinfo.js:_relacionar_menu_permisos()

		Además en <opciones_config está la configuración, para saber
		qué opciones mostrar o ocultar.
	*/

	//	10-2-2015: en el menu de jqueruui 1.11 NO hay que poner el <a> en los items. antes: <li><a href="#">opcion</a></li> , ahora: <li>opcion</li>
	var content = sprintf(
		'<ul id="menu-principal">' +

		//		'<li id="menu-principal-citaspendientes"><a href="#"><span class="endo-icon ui-icon" />%s</a></li>' +/*IDIOMAOK*/
		`<li id="menu-principal-citaspendientes" class="element-list">
			${icons.citas_pendientes}
			<span>%s</span>
		</li>` +/*IDIOMAOK*/
		`<li id="menu-principal-nuevaexpl" class="element-list">
			${icons.nueva_exploracion}
			<span>%s</span>
		</li>` +/*IDIOMAOK*/

		`<li id="menu-principal-buscarexpl" class="element-list">
			${icons.buscar_exploraciones}
			<span>%s</span>
			<ul>
			<li id="menu-principal-buscarexpl-fecha" class="element-list">
				${icons.buscar_exploraciones_fecha}
				<span>%s</span>
			</li>
			<li id="menu-principal-buscarexpl-paciente" class="element-list">
				${icons.buscar_exploraciones_paciente}
				<span>%s</span>
			</li>
			<li id="menu-principal-buscarexpl-nexpl" class="element-list">
				${icons.buscar_exploraciones_numero_exploracion}
				<span>%s</span>
			</li>
			<li id="menu-principal-buscarexpl-sinfinalizar" class="element-list">
				${icons.buscar_exploraciones_sin_finalizar}
				<span>%s</span>
			</li>
			</ul>
		</li>` +

		`<li id="menu-principal-gestioncitas" class="element-list">
			${icons.gestion_agenda}
			<span>%s</span>
		</li>` +/*IDIOMAOK*/
		`<li id="menu-principal-gestionpacientes" class="element-list">
			${icons.gestion_paciente}
			<span>%s</span>
		</li>` +/*IDIOMAOK*/

		`<li id="menu-principal-group-administracion" class="element-list">
			${icons.administacion}
			<span>%s</span>
		<ul>
		<li id="menu-principal-tablas" class="element-list">
		${icons.administacion_tablas}
			<span>%s</span>
		</li>
		<li id="menu-principal-usuarios" class="element-list">
		${icons.administacion_usuarios}
			<span>%s</span>
		</li>
		<li id="menu-principal-administracion" class="element-list">
		${icons.administacion_general}
			<span>%s</span>
		</li>

		<li id="menu-principal-editortiposexpl" class="element-list">
		${icons.administacion_tipos_exploracion}
			<span>%s</span>
		</li>
		<li id="menu-principal-tareas" class="element-list">
		${icons.administacion_tareas}
			<span>%s</span>
		</li>
		<li id="menu-principal-mensaje" class="element-list">
		${icons.administacion_mensajes}
			<span>%s</span>
		</li>
		</ul>
		</li>` +

		//'<li id="menu-principal-tablas"><span class="endo-icon ui-icon" />%s</li>' +/*IDIOMAOK*/
		//'<li id="menu-principal-usuarios"><span class="endo-icon ui-icon" />%s</li>' +/*IDIOMAOK*/
		//'<li id="menu-principal-administracion"><span class="endo-icon ui-icon" />%s</li>' +/*IDIOMAOK*/

		//'<li id="menu-principal-editortiposexpl"><span class="endo-icon ui-icon" />%s</li>' +/*IDIOMAOK*/
		//'<li id="menu-principal-tareas"><span class="endo-icon ui-icon" />%s</li>' +/*IDIOMAOK*/

		'<!--li class="ui-state-disabled">disabled</li-->' +

		'</ul>',
		_("Citas pendientes"),
		_("Nueva exploración"),
		_("Buscar exploraciones"),
		_("Por fecha"),
		_("Por paciente"),
		_("Por número de exploración"),
		_("Sin finalizar"),
		_("Gestión de agenda"),
		_("Gestión de pacientes"),
		_("Administración"),
		_("Tablas"),
		_("Usuarios"),
		_("General"),
		_("Tipos de exploración"),
		_("Tareas"),
		_("Enviar Mensaje")
	);

	menu_principal = $(content).hide().zIndex(2000).appendTo($('body'));

	//	Ocultar todas las opciones y mostrar solo las indicadas en "opciones_menu"
	$('#menu-principal>li').hide();
	$('#menu-principal-group-administracion>ul>li').hide(); //oculta las del submenu administracion
	for (var i = 0; i < opciones_menu.length; i++) {
		$('#' + opciones_menu[i].id).show();
	}

	//	aplicar algunas opciones de configuración
	//		MOSTRAR_OPCION_NUEVA_EXPLORACION
	//		MOSTRAR_OPCION_GESTION_CITAS
	//		DEVELOPMENT
	if (!opciones_config.MOSTRAR_OPCION_NUEVA_EXPLORACION) $('#menu-principal-nuevaexpl').hide();
	if (!opciones_config.MOSTRAR_OPCION_GESTION_CITAS) $('#menu-principal-gestioncitas').hide();
	if (!opciones_config.MOSTRAR_OPCION_CITAS_PENDIENTES) $('#menu-principal-citaspendientes').hide();
	if (!opciones_config.DEVELOPMENT) {
		//	desactivar opciones que aun están en desarrollo
		//$('#menu-principal-administracion').hide();	//	TERMINADO
	}

	if (opciones_config.ENTORNO == "PRUEBAS") $('#mainheader').addClass("entorno-pruebas");

	//	AÑADIR LAS BUSQUEDAS AVANZADAS
	for (var i = 0; i < busquedas_avanzadas.length; i++) {
		switch (parseInt(busquedas_avanzadas[i].nivel, 10)) {
			case 1: // publico servicio
			case 3: // protegida servicio
				if (!!busquedas_avanzadas[i].servicio_id && !!Endosys.auth && !!Endosys.auth.servicio_activo &&
					busquedas_avanzadas[i].servicio_id !== Endosys.auth.servicio_activo.id) continue;
				break;
			case 4: // privada
				if (!!busquedas_avanzadas[i].username && !!Endosys.auth &&
					busquedas_avanzadas[i].username !== Endosys.auth.username) continue;
				break;
			default: // publica
				break;
		}
		// $('#menu-principal-buscarexpl-avanzadas>ul')
		// 	.append($('<li class="menu-principal-busqueda" id="menu-principal-busqueda-' + busquedas_avanzadas[i].id + '">' +
		// 		'<span class="endo-icon ui-icon" />' + busquedas_avanzadas[i].descripcion + '</li>'));
	}

	menu_principal = menu_principal
		.menu()
		.position({	//	OK para jQueryUI >= 1.10
			my: "left bottom",
			at: "left top-10",
			of: $('#menu-principal-btn')
		});

	// EVENTOS:
	//	GESTION DE CITAS (AGENDA)
	$('#menu-principal-gestioncitas').click(function () {
		reset_pantalla();
		set_titulo_pantalla(_('Gestión de agenda'));/*IDIOMAOK*/
		contenido_principal.mostrar(gestion_agenda);
	});
	//	CITAS PENDIENTES (NUEVA EXPLORACION CON CITA)
	$('#menu-principal-citaspendientes').click(function () {
		reset_pantalla();
		nueva_exploracion.mostrar_con_cita(true);
	});
	//	NUEVA EXPLORACION
	$('#menu-principal-nuevaexpl').click(function () {
		reset_pantalla();
		nueva_exploracion.mostrar_sin_cita(true);
	});
	//	GESTION PACIENTES
	$('#menu-principal-gestionpacientes').click(function () {
		reset_pantalla();
		set_titulo_pantalla(_('Gestión de pacientes'));/*IDIOMAOK*/
		contenido_principal.mostrar(gestion_pacientes, null, { opcion_deshabilitados: true });
	});
	//	BUSCAR EXPLORACIONES POR FECHA
	$('#menu-principal-buscarexpl-fecha').click(function () {
		reset_pantalla();
		set_titulo_pantalla(_('Exploraciones'), _('Buscar por fecha'));/*IDIOMAOK*/
		contenido_principal.mostrar(gestion_exploraciones.por_fecha);
	});
	//	BUSCAR EXPLORACIONES POR PACIENTE
	$('#menu-principal-buscarexpl-paciente').click(function () {
		reset_pantalla();
		busqueda_por_paciente.mostrar();
	});
	//	BUSCAR EXPLORACIONES POR Nº EXPL
	$('#menu-principal-buscarexpl-nexpl').click(function () {
		reset_pantalla();
		gestion_exploraciones.mostrar_numero_expl_dialog()
			.done(function (exploracion) {
				set_titulo_pantalla(_('Exploraciones'), _('Buscar por número de exploración'));/*IDIOMAOK*/
				contenido_principal.mostrar(gestion_exploraciones.una, exploracion.id);
			});
	});
	// //	NUEVA BUSQUEDA AVANZADA
	// $('#menu-principal-nuevabusqueda').click(function () {
	// 	reset_pantalla();
	// 	ejecutar_busqueda.mostrar_ejecutar_busqueda_no_exist();
	// });
	//	BUSCAR EXPLORACIONES SIN FINALIZAR
	$('#menu-principal-buscarexpl-sinfinalizar').click(function () {
		reset_pantalla();
		contenido_principal.cerrar('#mainlayout');
		gestion_exploraciones.sin_finalizar.mostrar_popup();
		//contenido_principal.mostrar(gestion_exploraciones.sin_finalizar);
	});
	//	GESTION TABLAS
	$('#menu-principal-tablas').click(function () {
		reset_pantalla();
		set_titulo_pantalla(_('Tablas'));/*IDIOMAOK*/
		contenido_principal.mostrar(gestion_tablas);
	});
	// //GESTION BUSQUEDAS AVANZADAS
	// $('#menu-principal-busquedas').click(function () {
	// 	reset_pantalla();
	// 	set_titulo_pantalla(_('Administrar búsquedas'));/*IDIOMAOK*/
	// 	contenido_principal.mostrar(gestion_busquedas);
	// });
	//	EDITOR DE TIPOS DE EXPL.
	$('#menu-principal-editortiposexpl').click(function () {
		reset_pantalla();
		set_titulo_pantalla(_('Editor de tipos de exploración'));/*IDIOMAOK*/
		contenido_principal.mostrar(editor_tipos_expl);
	});
	//	ADMIN USUARIOS
	$('#menu-principal-usuarios').click(function () {
		reset_pantalla();
		set_titulo_pantalla(_('Gestión de usuarios'));/*IDIOMAOK*/
		contenido_principal.mostrar(gestion_usuarios);
	});
	//	CONFIGURACIÓN ENDOSYS
	$('#menu-principal-administracion').click(function () {
		reset_pantalla();
		set_titulo_pantalla(_('Administración de EndoSys'));/*IDIOMAOK*/
		contenido_principal.mostrar(administracion);
	});

	// //	BUSQUEDAS AVANZADAS
	// $('.menu-principal-busqueda').click(function () {
	// 	reset_pantalla();
	// 	var busqueda_id = $(this).attr('id').slice("menu-principal-busqueda-".length);
	// 	set_titulo_pantalla("Exploraciones", $(this).text());
	// 	ejecutar_busqueda.mostrar_ejecutar_busqueda_exist(busqueda_id);
	// });

	//	TAREAS
	$('#menu-principal-tareas').click(function () {
		reset_pantalla();
		set_titulo_pantalla(_('Tareas'));//IDIOMAOK
		contenido_principal.mostrar(gestion_tareas);
	});

	//	TAREAS
	$('#menu-principal-mensaje').click(function () {
		reset_pantalla();
		set_titulo_pantalla(_('Enviar Mensaje'));//IDIOMAOK
		gestion_notificaciones.mostrar_creador_mensaje();
	});

	var $submenus = $('#menu-principal li').has('ul');
	$('#menu-principal li').not($submenus).click(function () {
		ocultar_menu_principal();
	});

	$('#menu-principal li').click(function () {
		ejecutar_busqueda.activo = false;
	});


	if (Endosys.auth.username !== 'sysadmin') {
		$("#menu-principal-administracion").remove()
		$("#menu-principal-editortiposexpl").remove()
		$("#menu-principal-tareas").remove()
		$("#menu-principal-mensaje").remove()
	}

	return menu_principal;
}

//	XXX	plugin de jQuery (ui) para tener un buttonset en vertical.
//	(https://gist.github.com/edersohe/760885)
$.fn.buttonsetv = function () {
	$(':radio, :checkbox', this).wrap('<div style="margin: 1px"/>');
	$(this).buttonset();

	$('label:first', this).removeClass('ui-corner-left').addClass('ui-corner-top');
	$('label:last', this).removeClass('ui-corner-right').addClass('ui-corner-bottom');
	mw = 0; // max witdh
	$('label', this).each(function (index) {
		w = $(this).width();
		if (w > mw) mw = w;
	})
	$('label', this).each(function (index) {
		$(this).width(mw);
	})

};
