var editor_busqueda2 = function () {
	return {
		lista_campos_gen: [],
		desc_busqueda: undefined,
		id_busqueda: undefined,
		nivel: undefined,
		username: undefined,
		comentario: undefined,
		campos_variables: undefined,

		mostrar: function () {
			editor_busqueda2.lista_campos_gen = [];
			TM.content_editor_busqueda.activate();
			TM.content_editor_busqueda.detalles.activate();
			TM.content_editor_busqueda.elementos.activate();
			Endosys.statusbar.mostrar_mensaje('Cargando busqueda avanzada...');	// IDIOMAOK

			return TM.content_editor_busqueda.load_content(mainlayout, "content/edicion_busqueda2.html" + ew_version_param()).then(function () {
				$('.layout_main_content').layout({
					west__size: 290,
					east__slidable: false,
					east__closable: false,
					east__size: 290,
					spacing_closed: 10,
					slideTrigger_open: "click",
					initClosed: false,
					resizable: false
				});

				$("#guardar_btn").button().click(function (event) {
					editor_busqueda2.guardar_busqueda();
				});

				$("#guardar_como_btn").button().click(function (event) {
					//se le pasa true para saber que debe de hacer un guardar como
					editor_busqueda2.guardar_busqueda(true);
				});

				$("#ejecutar_btn").button().click(function (event) {
					$('#mainnav-continuar-btn').click();
				});

				$('.creador-input').val(Endosys.auth.username);

				if (!editor_busqueda2.desc_busqueda) {
					//la busqueda no existe por lo que ocultamos el boton de guardar como
					$("#guardar_como_btn").hide();
				}

				return editor_busqueda2.construir_menu_campos();
			});
		},

		_get_campos: function (tm) {
			//metodo que obtiene todos los campos para las buquedas avanzadas.
			var temptablas = {};
			var camposVariables = [];
			var camposFijos = [];

			var procesar_camposFijos = function (campos) {
				for (var i = 0; i < campos.length; i++) {
					if (camposFijos.length > 0) {
						//existe alguno campo, es decir identificar si es el primero para arrancar 
						//verificamos que no exista ninguno que pertenezca a su mismo conjunto
						var exist_conjunto = false;
						var posicion = 0;

						//miramos si ya existe algun campo añadido que pertenezca al mismo conjunto para agruparlo
						for (var e = 0; e < camposFijos.length; e++) {
							if (camposFijos[e].conjunto == campos[i].desc_conjunto) {
								exist_conjunto = true;
								posicion = e;
							}
						}

						if (exist_conjunto) {
							//existe uno campo de su propia familia
							camposFijos[posicion].camps.push(campos[i]);

						} else {
							//no existe ningun campo de su propia familia
							camposFijos.push({
								conjunto: campos[i].desc_conjunto,
								camps: [campos[i]]
							});
						}

					} else {
						//esta vacio es el primero
						camposFijos.push({
							conjunto: campos[i].desc_conjunto,
							camps: [campos[i]]
						});
					}
				}
			}

			//	Campos tipo seleccion y multi:
			//	obtener todos los campos de cada formulario y filtrar solo los de seleccion y multi (en la funcion procesar)
			//	primero obtiene los formularios y luego los campos de cada uno.
			var procesar = function (formulario) {
				var tempcampos = {
					conjunto: undefined,
					camps: []
				};

				for (var j = 0; j < formulario.gruposCampos.length; j++) {
					var campos = formulario.gruposCampos[j].campos;

					for (var i = 0; i < campos.length; i++) {
						if ((j == 0) && (i == 0)) {
							tempcampos.conjunto = formulario.titulo;
						}

						//filtrar campos migrados de tipo "titulo"
						if (campos[i].tipo != 6) {
							auxcampo = {
								id_conjunto: formulario.id,
								desc_conjunto: formulario.titulo,
								id_camp: campos[i].id,
								nom_camp: campos[i].nombre,
								desc_camp: campos[i].titulo,
								tipo_camp: campos[i].tipo,
								tipo_cont: campos[i].tipo_control || 0
							};
							tempcampos.camps.push(auxcampo);
						}
					}
				}

				camposVariables.push(tempcampos);
			}

			editor_busqueda2.campos_variables = undefined;

			return Endosys.formularios.index(tm, null).then(function (formularios) {
				//	encadenar todas las llamadas al show de cada formulario para obtener los campos, una tras otra.
				var chain = $.when();

				$(formularios).each(function (i, form) {
					chain = chain.then(function () {
						return Endosys.formularios.show(tm, form.id, { '_showmode': '1' }).done(function (formulario) {
							procesar(formulario);
						});
					})
				});

				return chain;
			}).then(function () {
				//	al final, la llamada para obtener los campos fijos
				return Endosys.camposFijos.index(tm);
			}).then(function (results) {
				procesar_camposFijos(results);
				editor_busqueda2.campos_variables = camposFijos.concat(camposVariables);
			});
		},

		construir_menu_campos: function () {
			return editor_busqueda2._get_campos(TM.content_editor_busqueda).done(function () {
				var campos = editor_busqueda2.campos_variables;

				for (var i = 0; i < campos.length; i++) {
					var nivel1 = '<h3>' + campos[i].conjunto + '</h3>';
					$("#accordion_menu").append(nivel1);

					var div_submenu = $("<div style='padding:1em 0em;'><ul></ul></div>");
					div_submenu.appendTo("#accordion_menu");

					for (var e = 0; e < campos[i].camps.length; e++) {
						var nivel2 = $('<li>' + campos[i].camps[e].desc_camp + '</li>');

						$(nivel2).data("campo", campos[i].camps[e]);
						$(nivel2).data("conjunto", campos[i].conjunto);

						nivel2.appendTo(div_submenu.find('ul'));
					}
				}

				$("#accordion_menu").accordion({ heightStyle: "content" });

				$('#accordion_menu li').click(function (event) {
					var datos_campo = $(this).data();
					var exist = false;
					var campo_gen_modificar;

					for (var i = 0; i < editor_busqueda2.lista_campos_gen.length; i++) {
						if (editor_busqueda2.lista_campos_gen[i].campo.id_camp == datos_campo.campo.id_camp
							&& editor_busqueda2.lista_campos_gen[i].campo.id_conjunto == datos_campo.campo.id_conjunto) {
							exist = true;
							campo_gen_modificar = editor_busqueda2.lista_campos_gen[i];
						}
					}

					if (!exist) {
						//el campo no existe ---> crear nueva condicion
						dialogo_condicion.crear_dialogo_condicion(datos_campo.campo);
					} else {
						//el campo SI existe ---> modificar condicion
						dialogo_condicion.crear_dialogo_condicion(datos_campo.campo, campo_gen_modificar);
					}
				});

				$("#accordion_menu li").hover(function () {
					$(this).addClass('ui-state-hover');
				}, function () {
					$(this).removeClass('ui-state-hover');
				});

				$('#accordion_menu li').css("cursor", "default");

				var servicios = userinfo.get_usuario().medico.servicios;
				for (var i = 0; i < servicios.length; i++) {
					var $op = $('<option value="' + servicios[i].id + '">' + servicios[i].nombre + '</option>');

					if (servicios[i].id === Endosys.auth.servicio_activo.id) {
						$op.attr('selected', '');
					}

					$('.servicio-list').append($op);
				}

				$('.nivel-list').change(function () {
					switch (parseInt($('.nivel-list').val(), 10)) {
						case 1:
						case 3:
							$("#servicio-group").show();
							break;
						default:
							$("#servicio-group").hide();
					}
				});

				$('.nivel-list').change();
			});
		},

		pintar_condicion: function (campo_gen, modificar) {
			var listado_condiciones = $('#listado_condiciones');
			var portlet = $('<div class="portlet"></div>');
			portlet.data("campo_gen", campo_gen);

			var header = $('<div class="portlet-header"></div>');
			header.html(campo_gen.campo.desc_camp).appendTo(portlet);

			var content = $('<div class="portlet-content"></div>');
			var str_content = "<div class='portlet-operacion'>" + campo_gen.operacion.valor + "</div>";

			for (var i = 0; i < campo_gen.valores.length; i++) {
				str_content = str_content + "<span class='portlet-valor'>" + campo_gen.valores[i].text

				if (!!campo_gen.valores[i].cantidad && !!campo_gen.valores[i].oper) {
					str_content += " (";
					if (campo_gen.valores[i].oper === "MAYOR") {
						str_content += ">";
					} else if (campo_gen.valores[i].oper === "MAYORIGUAL") {
						str_content += ">=";
					} else if (campo_gen.valores[i].oper === "IGUAL") {
						str_content += "=";
					} else if (campo_gen.valores[i].oper === "MENORIGUAL") {
						str_content += "<=";
					} if (campo_gen.valores[i].oper === "MENOR") {
						str_content += "<";
					}
					str_content += campo_gen.valores[i].cantidad + ") ";
				}

				str_content += "</span></br>";
			}

			content.html(str_content).appendTo(portlet);

			if (modificar) {
				//substituir en pantalla en la posicion del antiguo
				$('#listado_condiciones .portlet').each(function (index) {
					if ($(this).data().campo_gen.campo.id_camp == campo_gen.campo.id_camp && $(this).data().campo_gen.campo.id_conjunto == campo_gen.campo.id_conjunto) {
						$(this).replaceWith(portlet);
					}

					//var valor = leer_elemento(campo,index,$(this));
					//valores.push(valor);
				});
			} else {
				//añadir en pantalla donde toque
				portlet.appendTo(listado_condiciones);
			}

			portlet.addClass("ui-widget ui-widget-content ui-helper-clearfix ui-corner-all")
				.find(".portlet-header")
				.addClass("ui-widget-header ui-corner-all")
				// .prepend( "<span class='ui-icon ui-icon-minusthick'></span>")
				.prepend("<span class='ui-icon ui-icon-pencil'></span>")
				.prepend("<span class='ui-icon ui-icon-close'></span>")
				.end()
				.find(".portlet-content");

			/* header.find(".ui-icon-minusthick").click(function() {
				$(this).toggleClass( "ui-icon-minusthick" ).toggleClass( "ui-icon-plusthick" );
				$(this).parents( ".portlet:first" ).find( ".portlet-content" ).toggle();
			}); */

			header.find(".ui-icon-close").click(function () {
				var pregunta_eliminar = confirm("¿Esta seguro que desea eliminar el filtro?");	// IDIOMAOK

				if (pregunta_eliminar) {
					var campo_gen = $(this).parents(".portlet:first").data().campo_gen;

					for (var i = 0; i < editor_busqueda2.lista_campos_gen.length; i++) {
						if (editor_busqueda2.lista_campos_gen[i].campo.id_camp == campo_gen.campo.id_camp && editor_busqueda2.lista_campos_gen[i].campo.id_conjunto == campo_gen.campo.id_conjunto) {
							editor_busqueda2.lista_campos_gen.splice(i, 1);
						}
					}

					$(this).parents(".portlet:first").remove();
				}
			});

			header.find(".ui-icon-pencil").click(function () {
				var exist = dialogo_condicion.existe_dialog();
				if (exist) return;

				var datos_campo = $(this).parents(".portlet:first").data().campo_gen.campo;
				var campo_gen_modificar = $(this).parents(".portlet:first").data().campo_gen;
				dialogo_condicion.crear_dialogo_condicion(datos_campo, campo_gen_modificar);
			});
		},

		reconstruir_listado_condiciones: function (lista_campos) {
			for (var i = 0; i < lista_campos.length; i++) {
				var campo_gen = lista_campos[i];
				editor_busqueda2.pintar_condicion(campo_gen);
			}

			editor_busqueda2.lista_campos_gen = lista_campos;
		},

		guardar_busqueda: function (guardar_como) {
			if (editor_busqueda2.lista_campos_gen.length == 0) {
				alert(_('No existe ningun criterio de busqueda, debes introducir uno'));	// IDIOMAOK
			} else {
				var xml_return = editor_busqueda2.construir_xml();

				if (editor_busqueda2.desc_busqueda
					&& editor_busqueda2.id_busqueda
					&& guardar_como != true
					&& (
						(editor_busqueda2.nivel === "2" && editor_busqueda2.username === Endosys.auth.username)
						|| (editor_busqueda2.nivel === "3" && editor_busqueda2.username === Endosys.auth.username)
						|| (editor_busqueda2.nivel === "4" && editor_busqueda2.username === Endosys.auth.username)
						|| Endosys.auth.username === "sysadmin")
				) {
					//la busqueda existe, por lo que, el boton guardar hace la funcion de modificar
					Endosys.busqueda_avanzada.update(TM.content_editor_busqueda, editor_busqueda2.id_busqueda, {
						'xml': xml_return,
						'nivel': $('.nivel-list').val(),
						'username': $('.creador-input').val() || Endosys.auth.username,
						'comentario': $('.comentario-text').val() || null,
						'servicio_id': $('#servicio-group:visible').length === 1 ? $('.servicio-list').val() : null
					}).done(function () {
						Endosys.statusbar.mostrar_mensaje(_('La búsqueda se ha guardado correctamente'));	// IDIOMAOK
					}).then(function () {
						return Endosys.busqueda_avanzada.index(TM.gestion_busquedas)
					}).done(function (busquedas_avanzadas) {
						var opciones_menu = userinfo.get_opciones_menu();
						gestion_busquedas.refrescar_menu_busquedas(opciones_menu, busquedas_avanzadas);
					});
				} else {
					var titulo = _('Guardar la búsqueda');	// IDIOMAOK
					var desc_campo = _('Descripción de la búsqueda');	// IDIOMAOK
					var el_nuevo_valor = null;

					controles.input_dialog.mostrar(titulo, desc_campo, '').then(function (nuevo_valor) {
						el_nuevo_valor = nuevo_valor;
						el_nuevo_username = Endosys.auth.username;

						return Endosys.busqueda_avanzada.create(TM.content_editor_busqueda, {
							'descripcion': el_nuevo_valor,
							'xml': xml_return,
							'nivel': $('.nivel-list').val(),
							'username': Endosys.auth.username,
							'comentario': $('.comentario-text').val() || null,
							'servicio_id': $('#servicio-group:visible').length === 1 ? $('.servicio-list').val() : null
						})
					}).then(function (busqueda) {
						set_titulo_pantalla(null, el_nuevo_valor);
						editor_busqueda2.desc_busqueda = el_nuevo_valor;
						editor_busqueda2.id_busqueda = busqueda.id;
						editor_busqueda2.username = el_nuevo_username;

						$('.creador-input').val(el_nuevo_username);
						$("#guardar_como_btn").show();

						Endosys.statusbar.mostrar_mensaje(_('La búsqueda se ha guardado correctamente'));	// IDIOMAOK

						return Endosys.busqueda_avanzada.index(TM.content_editor_busqueda);
					}).done(function (busquedas_avanzadas) {
						var opciones_menu = userinfo.get_opciones_menu();
						gestion_busquedas.refrescar_menu_busquedas(opciones_menu, busquedas_avanzadas);
					}).then(function () {
						return Endosys.busqueda_avanzada.index(TM.gestion_busquedas);
					}).done(function (busquedas_avanzadas) {
						var opciones_menu = userinfo.get_opciones_menu();
						gestion_busquedas.refrescar_menu_busquedas(opciones_menu, busquedas_avanzadas);
					});
				}
			}
		},

		construir_xml: function () {
			var campos = "";

			for (var j = 0; j < editor_busqueda2.lista_campos_gen.length; j++) {
				// modificion xq en ie7 no funciona la funcion de jquery.html()
				var lista_valores_str = "";

				for (var i = 0; i < editor_busqueda2.lista_campos_gen[j].valores.length; i++) {
					var valor = "";

					if (editor_busqueda2.lista_campos_gen[j].campo.tipo_camp == '3') {
						valor = "<valor orden='" + i + "'>" + "<id>" +
							editor_busqueda2.lista_campos_gen[j].valores[i].id + "</id>" +
							"<descripcion>" + editor_busqueda2.lista_campos_gen[j].valores[i].text + "</descripcion>";

						if (editor_busqueda2.lista_campos_gen[j].campo.tipo_cont == '2') {
							valor += "<oper>" + editor_busqueda2.lista_campos_gen[j].valores[i].oper + "</oper>" +
								"<cantidad>" + editor_busqueda2.lista_campos_gen[j].valores[i].cantidad + "</cantidad>";
						}

						valor += "</valor>";
						/*	
							# ESTE CODIGO FUNCIONA MAL, presente en las versiones 2.4.10 a 2.4.11.1 inclusive
							# Es para que las busquedas avanzadas tengas busqueda por cantidades					
							valor = "<valor orden='"+i+"'>"+
										"<id>"+editor_busqueda2.lista_campos_gen[j].valores[i].id+"</id>"+
										"<descripcion>"+editor_busqueda2.lista_campos_gen[j].valores[i].text+"</descripcion>"+
										"<operacion>IGUAL</operacion>" + 
										"<valores>" + 
											"<valor orden='1'>1</valor>" + 
											"<valor orden='2'>1</valor>" + 
										"</valores>"+
									"</valor>";
						*/
					} else if (editor_busqueda2.lista_campos_gen[j].campo.tipo_camp == '2') {
						valor = "<valor orden='" + i + "'>" +
							"<id>" + editor_busqueda2.lista_campos_gen[j].valores[i].id + "</id>" +
							"<descripcion>" + editor_busqueda2.lista_campos_gen[j].valores[i].text + "</descripcion>" +
							"</valor>";
					} else {
						valor = "<valor orden='" + i + "'>" + editor_busqueda2.lista_campos_gen[j].valores[i].text + "</valor>";
					}

					lista_valores_str = lista_valores_str + valor;
				}

				var campo = "<campo>" +
					"<conjunto_id>" + editor_busqueda2.lista_campos_gen[j].campo.id_conjunto + "</conjunto_id>" +
					"<descripcion_conjunto>" + editor_busqueda2.lista_campos_gen[j].campo.desc_conjunto + "</descripcion_conjunto>" +
					"<campo_id>" + editor_busqueda2.lista_campos_gen[j].campo.id_camp + "</campo_id>" +
					"<nombre_campo>" + editor_busqueda2.lista_campos_gen[j].campo.nom_camp + "</nombre_campo>" +
					"<titulo_campo>" + editor_busqueda2.lista_campos_gen[j].campo.desc_camp + "</titulo_campo>" +
					"<tipo_campo>" + editor_busqueda2.lista_campos_gen[j].campo.tipo_camp + "</tipo_campo>" +
					"<tipo_control>" + editor_busqueda2.lista_campos_gen[j].campo.tipo_cont + "</tipo_control>" +
					"<operacion>" + editor_busqueda2.lista_campos_gen[j].operacion.id + "</operacion>" +
					"<valores>" + lista_valores_str + "</valores>" +
					"</campo>";

				campos = campos + campo;
			}

			var xml_busqueda = "<campos>" + campos + "</campos>";
			return xml_busqueda;
		},

		cargar_busqueda_existente: function (id) {
			Endosys.busqueda_avanzada.show(TM.content_editor_busqueda, id).done(function (busqueda) {
				var busqueda_request = {};
				busqueda_request.id_busqueda = busqueda.id;
				busqueda_request.descripcion = busqueda.descripcion;
				busqueda_request.nivel = busqueda.nivel;
				busqueda_request.username = busqueda.username;
				busqueda_request.servicio_id = busqueda.servicio_id;
				busqueda_request.comentario = busqueda.comentario;
				editor_busqueda2.nivel = busqueda.nivel;
				editor_busqueda2.username = busqueda.username;
				editor_busqueda2.servicio_id = busqueda.servicio_id;
				editor_busqueda2.comentario = busqueda.comentario;

				$('.nivel-list').val(busqueda.nivel).change();
				if (!!busqueda.servicio_id) $('.servicio-list').val(busqueda.servicio_id);
				if (!!busqueda.username) $('.creador-input').val(busqueda.username);
				if (!!busqueda.servicio_id) $('.servicio-list').val(busqueda.servicio_id);
				if (!!busqueda.comentario) $('.comentario-text').val(busqueda.comentario);

				var xmlDoc = $.parseXML(busqueda.xml);
				var $busqueda_xml = $(xmlDoc);

				busqueda_request.campos = [];
				$busqueda_xml.find('campo').each(function (i, el) {
					var campo_request = {};
					var $campo = $(el);

					campo_request.id_conjunto = $campo.find("conjunto_id").text();
					campo_request.desc_conjunto = $campo.find("descripcion_conjunto").text();
					campo_request.id_camp = $campo.find("campo_id").text();
					campo_request.nom_camp = $campo.find("nombre_campo").text();
					campo_request.desc_camp = $campo.find("titulo_campo").text();
					campo_request.tipo_camp = $campo.find("tipo_campo").text();
					campo_request.tipo_cont = $campo.find("tipo_control").text() || null;
					campo_request.operacion_id = $campo.find("operacion").text();
					campo_request.valores = [];

					$campo.find("valores > valor").each(function (i, el) {
						var $valor = $(el);
						var valor = null;

						if (campo_request.tipo_camp == "3") {
							valor = {
								text: $valor.find("descripcion").text(),
								value: $valor.find("id").text(),
								cantidad: $valor.find("cantidad") ? $valor.find("cantidad").text() : null,
								oper: $valor.find("oper") ? $valor.find("oper").text() : null
							};
							/*
								# ESTE CODIGO FUNCIONA MAL, presente en las versiones 2.4.10 a 2.4.11.1 inclusive
								# Es para que las busquedas avanzadas tengas busqueda por cantidades
								valor = {
									text:	$valor.find("descripcion").text(),
									value:	$valor.find("id").text(),
									cantidad:	$valor.find("cantidad").text() //2.4.10
								};
							*/
						} else if (campo_request.tipo_camp == "2") {
							valor = {
								text: $valor.find("descripcion").text(),
								value: $valor.find("id").text()
							};
						} else {
							valor = $valor.text();
						}

						campo_request.valores.push(valor);
					});

					busqueda_request.campos.push(campo_request);
				});

				editor_busqueda2.cargar_busqueda_en_pantalla(busqueda_request);
			});
		},

		cargar_busqueda_en_pantalla: function (busqueda_request) {
			lista_campos = busqueda_request.campos;

			for (var j = 0; j < lista_campos.length; j++) {
				// limpiar variables
				campo_gen = {
					campo: {
						id_conjunto: lista_campos[j].id_conjunto,
						desc_conjunto: lista_campos[j].desc_conjunto,
						id_camp: lista_campos[j].id_camp,
						nom_camp: lista_campos[j].nom_camp,
						desc_camp: lista_campos[j].desc_camp,
						tipo_camp: lista_campos[j].tipo_camp,
						tipo_cont: lista_campos[j].tipo_cont || null,
					},
					operacion: {
						id: lista_campos[j].operacion_id,
						valor: undefined,
						tipo: undefined,
						logico: undefined
					},
					valores: []
				}

				var operaciones = Endosys.busqueda_avanzada.get_operaciones(lista_campos[j].tipo_camp);
				var op;

				for (var e = 0; e < operaciones.length; e++) {
					if (operaciones[e].id == lista_campos[j].operacion_id) {
						op = operaciones[e];
					}
				}

				campo_gen.operacion.valor = op.valor;
				campo_gen.operacion.logico = op.logico;
				campo_gen.operacion.tipo = op.tipo;

				for (var i = 0; i < lista_campos[j].valores.length; i++) {
					if (lista_campos[j].tipo_camp == "3" || lista_campos[j].tipo_camp == "2") {
						valor = {};
						valor.id = lista_campos[j].valores[i].value;
						valor.text = lista_campos[j].valores[i].text;

						if (!!lista_campos[j].valores[i].cantidad) {
							valor.cantidad = lista_campos[j].valores[i].cantidad;
						}

						if (!!lista_campos[j].valores[i].oper) {
							valor.oper = lista_campos[j].valores[i].oper;
						}

						campo_gen.valores.push(valor);
					} else {
						valor = {};
						valor.id = i;
						valor.text = lista_campos[j].valores[i];
						campo_gen.valores.push(valor);
					}
				}

				// lista_campos_gen.push(campo_gen);
				editor_busqueda2.pintar_condicion(campo_gen);
				editor_busqueda2.lista_campos_gen.push(campo_gen);
			}
		}
	}
}();
