var dialogo_condicion = function () {
	var content_form_condition = null;

	return {
		existe_dialog: function () {
			var exist = false;

			if ($('#content_form_condition').length != 0) {
				exist = true;
			}

			return exist;
		},

		crear_dialogo_condicion: function (datos_campo, campo_gen_modificar) {
			if (content_form_condition) return;

			content_form_condition = $("<div id='content_form_condition'></div>");
			content_form_condition.load("content/condicion.html" + ew_version_param(), function (data, textStatus) {
				if (textStatus == "success") {
					content_form_condition.i18n();

					$('body').append(content_form_condition);
					$('#content_form_condition').dialog({
						modal: true,
						autoOpen: false,
						resizable: false,
						title: _('Nueva Condición'),	// IDIOMAOK
						// show: 'clip',
						// hide: 'clip',
						height: 'auto',
						width: 600,
						close: function () {
							$('#content_form_condition').dialog("destroy").remove();
							content_form_condition = null;
						},
						buttons: [{
							text: _('Accept'),	// IDIOMAOK
							click: function () {
								// OJO q cuando sea un modificar se tendra que modificar y no añadir
								var campo_gen = dialogo_condicion.interpretar_dialogo_condicion(datos_campo);
								// console.log(campo_gen.valores);

								// eliminar los que estan vacios
								for (var j = 0; j < campo_gen.valores.length; j++) {
									//si text=="" es de tipo texto 
									//si es undefined es pq es un valor select
									//console.log(campo_gen.valores[j].text);
									if (campo_gen.valores[j].text == undefined || campo_gen.valores[j].text == "") {
										campo_gen.valores.splice(j);
									}
								}

								if (campo_gen.valores.length == 0) {
									//si son todos vacios alerta al usuario y no graba
									alert("Debe completar al menos un valor");	// IDIOMAOK
								} else {
									var exist = false;

									for (var i = 0; i < editor_busqueda2.lista_campos_gen.length; i++) {
										var campo_aux = editor_busqueda2.lista_campos_gen[i].campo;

										if (campo_aux.id_camp == campo_gen.campo.id_camp && campo_aux.id_conjunto == campo_gen.campo.id_conjunto) {
											//modificar campo
											editor_busqueda2.lista_campos_gen[i] = campo_gen;
											exist = true;
										}
									}

									if (!exist) {
										// nuevo campo
										editor_busqueda2.lista_campos_gen.push(campo_gen);
										editor_busqueda2.pintar_condicion(campo_gen);
									} else {
										editor_busqueda2.pintar_condicion(campo_gen, true);
									}

									$(this).dialog("close");
								}

								// return campo_gen;
							}
						}, {
							text: _('Cancel'),	// IDIOMAOK
							click: function () {
								$(this).dialog("close");
							}
						}]
					});

					dialogo_condicion.rellenar_dialogo_condicion(datos_campo, content_form_condition, campo_gen_modificar);
					$('#content_form_condition').dialog("open");
				} else {
					alert(_('Error al cargar el fichero') + ' concicion.html');	// IDIOMAOK
				}
			});
		},

		interpretar_dialogo_condicion: function (datos_campo) {
			var datos_op = $(".operacion-list option:selected").data().datos_op;
			var zona_valores = estructura.get(datos_op.tipo, datos_campo);
			var valores = [];

			if (zona_valores) {
				valores = zona_valores.interpretar();
			}

			campo_gen = {
				campo: datos_campo,
				operacion: datos_op,
				valores: valores
			}

			return campo_gen;
		},

		rellenar_dialogo_condicion: function (datos_campo, form_condicion, campo_gen_modificar) {
			var campo_seleccionado = datos_campo;

			form_condicion.find('.campo-nombre').html(campo_seleccionado.desc_camp);

			// recuperamos las operaciones que se puede realizar con el campo seleccionado "igual", "diferente"...
			var operaciones = Endosys.busqueda_avanzada.get_operaciones(campo_seleccionado.tipo_camp, campo_seleccionado.tipo_control || campo_seleccionado.tipo_cont);

			//montar el select de las operaciones disponibles igual, diferente...
			var select_operaciones = form_condicion.find('.operacion-list');

			for (var i = 0; i < operaciones.length; i++) {
				var option = $('<option value=' + operaciones[i].id + '>' + operaciones[i].valor + '</option>');
				option.data("datos_op", operaciones[i]);
				option.appendTo(select_operaciones);
			}

			if (campo_gen_modificar) {
				/* $("select option[value='" + campo_gen_modificar.operacion.id + "']").attr("selected", true);
				var datos_op = $("select option:selected").data().datos_op;
				select_operaciones.find("select option[value='" + campo_gen_modificar.operacion.id + "']").attr("selected", true);
				var datos_op = select_operaciones.find("select option:selected").data().datos_op; */

				select_operaciones.find("option[value='" + campo_gen_modificar.operacion.id + "']").attr("selected", true);
				var datos_op = select_operaciones.find("option:selected").data().datos_op;

				$('.zona_valores').empty();
				$('.zona_button').empty();

				var zona_valores = estructura.get(datos_op.tipo, campo_gen_modificar.campo);
				if (zona_valores) {
					zona_valores.pintar_existente(campo_gen_modificar.valores);
				}
			}

			select_operaciones.change(function () {
				//var datos_op = $("select option:selected").data().datos_op; // XXX NOTA DE CARLOS: No puedes usar un selector tan genérico!!! si en el DOM hay cualquier otro SELECT ya la has liado... (me ha pasado, entonces no funciona)
				//es necesario pasar los datos relacionados a la operacion para disponer del tipo de campo
				//dependiendo del tipo la zona de valores se muestra de una forma u otra
				//dialogo_condicion.pintar_zona_valores($("select option:selected").data(datos_op),datos_campo);
				//solucion A LA XXX NOTA DE RUBEN:
				var datos_op = $(this).find("option:selected").data().datos_op;

				$('.zona_valores').empty();
				$('.zona_button').empty();

				var zona_valores = estructura.get(datos_op.tipo, datos_campo);
				if (zona_valores) {
					zona_valores.pintar();
				}
			});

			select_operaciones.addClass('selectboxit-small');/*.selectBoxIt({
				copyClasses: "container",	//	necesario para aplicar el estilo
				autoWidth:	true,
				theme:		"jqueryui",
				native:		true
			});*/
		}
	}
}();		