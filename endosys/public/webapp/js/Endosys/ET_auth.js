Endosys.auth = function () {

	return {

		medico_id: null,
		medico_nombre: null,
		username: null,

		servicio_activo: null,	//	Este es el servicio en el que se está trabajando durante toda la sesión de este login
		//workstation:	esta como global en main.html

		init: function () {
			//	boton logout
			$("#loggedin-salir-btn").button().click(function () {
				Endosys.auth.do_logout();
			});

			//	comprueba si esta autenticado o no y muestra el login o logout segun corresponda
			$.get("/auth/remote_user")

				.done(function (data) {
					//	si esta autenticado hacer login sin pasar nombre ni password para
					//	obtener los datos, si no mostrar box para login.
					//				Endosys.auth[data ? 'do_login' : 'show_login']();
					if (data) {
						//	aunque es raro, podría fallar, por ejemplo si el usuario se ha eliminado.
						//	en ese caso se tiene que hacer un logout para que lo olvide (a nivel de cookies)
						//	si no no hay maneraq de hacer un login, a no ser que se borren las cookies desde el navegador.
						Endosys.auth.do_login()
							.fail(function () {
								Endosys.auth.do_logout();
							});
					} else {
						Endosys.auth.show_login();
					}
				})

				.fail(function (jqXHR, textStatus, errorThrown) {
					alert("Error /auth/remote_user" + jqXHR.status + ": " + textStatus);
				});
		},

		show_login: function () {
			//	ocultar logout
			$("#mainheader-loggedin").html('');

			//	mostrar login
			var login = "";
			login += "<div class=\"container-login-form\">";
			login += "    <div class=\"row\">";
			login += "        <div id=\"login-form\" class=\"col-sm-9 col-md-7 col-lg-5 mx-auto\">";
			login += "            <form class=\"form-horizontal my-5\">";
			login += "                <span class=\"heading\">Log In<\/span>";
			login += "";
			login += "                <div class=\"form-group\">";
			login += "                    <input type=\"text\" class=\"form-control\" id=\"login-form-user\" placeholder=\"Username\" \/>";
			login += "                    <i class=\"fa fa-user\"><\/i>";
			login += "                <\/div>";
			login += "";
			login += "                <div class=\"form-group help\">";
			login += "                    <input type=\"password\" class=\"form-control\" id=\"login-form-pass\" placeholder=\"Password\" \/>";
			login += "                    <i class=\"fa fa-lock\"><\/i>";
			login += "                <\/div>";
			login += "";
			login += "                <div class=\"form-group pb-1\">";
			login += "                    <button id=\"login-form-entrar-btn\" class=\"btn btn-default\">log in<\/button>";
			login += "                <\/div>";
			login += "            <\/form>";
			login += "        <\/div>";
			login += "    <\/div>";
			login += "<\/div>";
			login += "";


			mainlayout.html(sprintf(login,
				_('Autenticación de usuario'),
				_('Usuario'),
				_('Contraseña'),
				_('Iniciar sesión')
			));
			//	asignar a la tecla return en el edit del password
			$("#login-form-pass").keydown(function (event) {
				if (event.which == 13) $("#login-form-entrar-btn").click();
			});
			//	asignar a la tecla return en el edit del usuario para que vaya al password
			$("#login-form-user").keydown(function (event) {
				if (event.which == 13) $("#login-form-pass").focus();
			});

			$("#login-form")
				.position({	//	OK para jQueryUI >= 1.10
					my: "center",
					at: "center center-100",
					of: mainlayout
				});
			$("#login-form-user").focus();

			$('#login-form-entrar-btn').button().click(function () {
				if ($(this).attr('disabled')) return;
				Endosys.auth.do_login($("#login-form-user").val(), $("#login-form-pass").val());
			});
		},

		show_logout: function () {
			//	ocultar login
			mainlayout.html('');

			//	mostrar logout
			$("#mainheader-loggedin").html(sprintf(
				'<div id="loggedin-usuario">' +
				'<div>' + Endosys.auth.medico_nombre + '</div>' +
				'</div>'/*IDIOMAOK*/
			));

			$("#mainheader_logout").html(sprintf(
				`<div id="loggedin-salir-btn" class="icon-button icon-button-primary">
				<svg xmlns="http://www.w3.org/2000/svg" aria-hidden="true" role="img" width="24px" height="24px" preserveAspectRatio="xMidYMid meet" viewBox="0 0 1024 1024"><path fill="currentColor" d="M868 732h-70.3c-4.8 0-9.3 2.1-12.3 5.8c-7 8.5-14.5 16.7-22.4 24.5a353.84 353.84 0 0 1-112.7 75.9A352.8 352.8 0 0 1 512.4 866c-47.9 0-94.3-9.4-137.9-27.8a353.84 353.84 0 0 1-112.7-75.9a353.28 353.28 0 0 1-76-112.5C167.3 606.2 158 559.9 158 512s9.4-94.2 27.8-137.8c17.8-42.1 43.4-80 76-112.5s70.5-58.1 112.7-75.9c43.6-18.4 90-27.8 137.9-27.8c47.9 0 94.3 9.3 137.9 27.8c42.2 17.8 80.1 43.4 112.7 75.9c7.9 7.9 15.3 16.1 22.4 24.5c3 3.7 7.6 5.8 12.3 5.8H868c6.3 0 10.2-7 6.7-12.3C798 160.5 663.8 81.6 511.3 82C271.7 82.6 79.6 277.1 82 516.4C84.4 751.9 276.2 942 512.4 942c152.1 0 285.7-78.8 362.3-197.7c3.4-5.3-.4-12.3-6.7-12.3zm88.9-226.3L815 393.7c-5.3-4.2-13-.4-13 6.3v76H488c-4.4 0-8 3.6-8 8v56c0 4.4 3.6 8 8 8h314v76c0 6.7 7.8 10.5 13 6.3l141.9-112a8 8 0 0 0 0-12.6z"/></svg>
				</div>`,
			))

			$("#loggedin-salir-btn").button(
			)
				.click(function () {
					Endosys.auth.do_logout();
				});
		},

		do_login: function (username, password) {
			/*
			devuelve una promise
			*/

			//variables de checkeo
			var success_login = false;


			// Limpia las tablas de ese usuario para que en el proximo login se carguen bien
			gestion_tablas.cargando_tablas = null;

			var centro_id_seleccionado = null;
			var centro_desc_seleccionado = null;
			Endosys.statusbar.mostrar_mensaje(_('Autenticando usuario...'));/*IDIOMAOK*/
			$("#login-form-entrar-btn").attr('disabled', true);

			//	se intenta autenticar y si se ejecuta correctamente muestra el logout
			return $.post("/auth2/signin", { 'username': username, 'password': password })

				.done(function (data) {
					Endosys.auth.medico_id = $(data).find('medico').attr('id');
					Endosys.auth.medico_nombre = $(data).find('nombre').text();
					Endosys.auth.username = $(data).find('username').text();
					Endosys.statusbar.mostrar_mensaje(_('Usuario autenticado correctamente'));/*IDIOMAOK*/
					success_login = true;
					Endosys.auth.show_logout();
				})

				.fail(function () {
					Endosys.statusbar.mostrar_mensaje(_('Error en la autenticación de usuario'), 1);/*IDIOMAOK*/
				})

				.always(function () {
					$("#login-form-entrar-btn").attr('disabled', false);
				})

				.then(function () {
					// Obtiene el workstation
					return get_workstation();
				})

				.then(null, function (data, textStatus, jqXHR) {
					// workstation es una variable global del sistema
					if (success_login && workstation == null) {
						username = Endosys.auth.username;
						if (username && username.toUpperCase() == "SYSADMIN") {
							// Solamente deja autoregistro al usuario sysadmin
							// Abre un dialogo que sirve para registrar un nuevo puesto.
							return dialog_crear_workstation();
						} else {
							error_text = _("Este puesto no tiene acceso al sistema Endosys App.")
							alert(error_text);//IDIOMAOK
							return $.Deferred().reject(jqXHR, data, error_text).promise();
						}
					}

				})

				// Si viene del dialogo y ha creado un workstation hay que hacer un show de nuevo,
				// para asignarlo en la variable global "workstation"
				// la funcion get_workstation hace eso y luego sigue con el flujo de inicializacion
				.always(function () {
					if (workstation == undefined || workstation == null) {
						return get_workstation()
					}
				})
				//	si el login es correcto, obtener la info del usuario incluyendo sus servicios
				.then(function () {
					return userinfo.inicializar(Endosys.auth.username);
				})

				//	Obtener el servicio activo, comparando los del usuario y los del workstation. Si hay mas de uno lo
				//	tiene que seleccionar el usuario.
				//	El promise devuelve el servicio.
				.then(function (opciones_menu) {	//	xxx	creo que no sirve de nada que userinfo.inicializar() devuelva opciones_menu
					//	Comprobar de todos los servicios para este puesto, a cuales pertenece el medico.
					var servicios_medico = userinfo.get_usuario().medico.servicios;
					var resultado = [];
					for (var i = 0; i < workstation.servicios.length; i++) {
						$.merge(resultado,
							$.grep(servicios_medico, function (servicio_medico) { return servicio_medico.id == workstation.servicios[i].id })
						);
					}

					//	si no hay ninguno, la funcionalidad es limitada/o no se puede entrar
					if (resultado.length == 0) {
						Endosys.statusbar.mostrar_mensaje(_('El usuario no pertenece a ninguno de los servicios disponibles en este puesto de trabajo'), 1);/*IDIOMAOK*/

						//	de momento se deja para que igualmente se pueda entrar, porque si no seria imposible entrar
						//	al menos para asignar servicios al workstation, ni con el sysadmin
						//	XXX	queda pendiente hacer que el sysadmin sea especial, o que se pueda entrar pero con funcionalidad limitada
						//return $.Deferred().reject().promise();	//	esto provoca el fail()
						return null;
					}
					//	si solo es uno, hacer éste el servicio activo
					else if (resultado.length == 1) {
						return resultado[0];
					}
					//	si hay más de uno, el usuario tiene que seleccionarlo
					else if (resultado.length > 1) {
						//	mostrar dialog para seleccionar el servicio
						return controles.modal_dialog.mostrar({
							title: _('Seleccionar servicio'), width: 240, height: 'auto', buttons: [],/*IDIOMAOK*/
							enterAccept: false,
							init: function (accept) {
								var $dialog = $(this);
								//	mostrar los servicios que hay en 'resultado' (pertenecen al usuario y al workstation)
								for (var i = 0; i < resultado.length; i++) {
									var servicio = resultado[i];
									$('<button value="' + servicio.id + '" type="button">' + servicio.nombre + '</button>')
										.data('servicio', servicio)
										.css('width', '100%')
										.button()
										.appendTo($dialog)
										.click(function () {
											accept($(this).data('servicio'));
										});
								}
							},
							result: function ($dialog, servicio) {
								return servicio;
							}
						})
					}

				})

				//	si no se consigue un servicio, hacer logout
				.fail(function () {
					Endosys.auth.do_logout();
				})

				.then(function (_servicio) {
					Endosys.auth.servicio_activo = _servicio;
					$('#mainfooter #info_servicio').html(" - " + (Endosys.auth.servicio_activo ? Endosys.auth.servicio_activo.nombre : "(" + _('Ningún servicio activo') + ")"));//IDIOMAOK
				})

				//	****************************************************

				.then(function () {
					return $.when(
						Endosys.busqueda_avanzada.index(TM.operaciones).then(function (busquedas_avanzadas) { return busquedas_avanzadas }),
						opciones_config.inicializar()
					)
				})

				.done(function (busquedas_avanzadas) {
					crear_menu_principal(userinfo.get_opciones_menu(), busquedas_avanzadas);
					$('#menu-principal-btn').click();

					// mostrar el div de notificaciones si ya existe
					if (gestion_notificaciones.es_visible()) {
						gestion_notificaciones.mostrar_notificaciones();
					} else {
						gestion_notificaciones.init();
					}

					// ACTIVA EL CIERRE DE SESION
					cierre_sesion.activar();
				});

		},

		do_logout: function () {
			//	se intenta desautenticar y si se ejecuta correctamente muestra el login
			$("#loggedin-salir-btn").attr('disabled', true);

			$.post("/auth/signout")

				.done(function (data) {
					$('#mainfooter #info_servicio').html("");
					//$("#info_puesto").html(workstation.nombre);

					if (gestion_notificaciones.es_visible()) {
						gestion_notificaciones.ocultar_notificaciones();
					}

					destruir_menu_principal();
					set_titulo_pantalla(" ", "");
					desactivar_asistente();
					set_atras(null);
					set_continuar(null);
					contenido_principal.cerrar('#mainlayout');
					Endosys.auth.show_login();

					// Borrar datos especificos del usuario
					gestion_agenda.agendas = null;
					workstation = null; // quita información de workstation

					// DESACTIVA EL CIERRE DE SESION
					cierre_sesion.desactivar();
					Endosys.auth._finalizar_transacciones_activas();
				})

				/*.fail(function (jqXHR, textStatus, errorThrown) {
				})*/

				.always(function () {
					$("#loggedin-salir-btn").attr('disabled', false);
				});

		},

		_finalizar_transacciones_activas: function () {
			TM.operaciones.abort();
			TM.nueva_exploracion.abort();
			TM.buscar_citas.abort();
			TM.content_tablas.abort();
			TM.content_pacientes.abort();
			TM.content_agendas_chus.abort();
			TM.content_citas.abort();
			TM.content_exploraciones.abort();
			TM.content_tiposExploracion.abort();
			TM.content_editorFormularios.abort();
			TM.content_editorTiposExpl.abort();
			TM.content_usuarios.abort();
			TM.content_editor_busqueda.abort();
			TM.gestion_busquedas.abort();
			TM.gestion_agenda.abort();
			TM.content_test.abort();
			TM.content_administracion.abort();
			TM.tareas.abort();
			TM.notificaciones.abort();
			TM.content_tablas.detalles.abort();
			TM.content_pacientes.detalles.abort();
			TM.content_pacientes.buscar.abort();
			TM.content_agendas_chus.detalles.abort();
			TM.content_citas.agendas_chus.abort();
			TM.content_citas.detalles.abort();
			TM.content_citas.agendas.abort();
			TM.content_exploraciones.detalles.abort();
			TM.content_exploraciones.buscar.abort();
			TM.content_exploraciones.detalles.elementoscampos.abort();
			TM.content_exploraciones.detalles.textospredefinidos.abort();
			TM.content_exploraciones.detalles.informes.abort();
			TM.content_exploraciones.detalles.imagenes.abort();
			TM.content_exploraciones.detalles.cita.abort();
			TM.content_editorFormularios.campos.abort();
			TM.content_editorFormularios.gruposcampos.abort();
			TM.content_editorFormularios.formulario.abort();
			TM.content_editorTiposExpl.tiposexploracion.abort();
			TM.content_editorTiposExpl.detalles.abort();
			TM.content_usuarios.servicios.abort();
			TM.content_usuarios.detalles.abort();
			TM.gestion_busquedas.busquedas.abort();
			TM.gestion_busquedas.detalles.abort();
			TM.content_editor_busqueda.arbol.abort();
			TM.content_editor_busqueda.detalles.abort();
			TM.content_editor_busqueda.elementos.abort();
			TM.content_administracion.arbol.abort();
			TM.content_administracion.detalles.abort();
		},

	}
}();
