var ESTRUCTURA_ENTRE = 3;
var ESTRUCTURA_SIMPLE = 2;
var ESTRUCTURA_VARIOS = 1;

var CAMPO_TEXTO = 1;
var CAMPO_SELEC = 2;
var CAMPO_CHECK = 4;

var estructura = function () {
	var entre = function (campo) {
		return {
			pintar: function () {
				crear_elemento(campo, false);
				crear_elemento(campo, false);
			},

			pintar_existente: function (valores) {
				if (valores[0]) crear_elemento(campo, false, valores[0]);
				if (valores[1]) crear_elemento(campo, false, valores[1]);
			},

			interpretar: function () {
				// leer_elemento(campo);
				var valores = [];

				$('.zona_valores p').each(function (index) {
					var valor = leer_elemento(campo, index, $(this));
					valores.push(valor);
				});

				return valores;
			}
		}
	};

	var simple = function (campo) {
		return {
			pintar: function () {
				crear_elemento(campo, false);
			},
			pintar_existente: function (valores) {
				if (valores[0]) {
					crear_elemento(campo, false, valores[0]);
				}
			},
			interpretar: function () {
				var valor = leer_elemento(campo, 0, $('.zona_valores p'));
				var valores = [];

				valores.push(valor);
				return valores;
			}
		}
	};

	var varios = function (campo) {
		return {
			pintar: function () {
				crear_elemento(campo, true);
				pintar_boton_mas(campo);
			},
			pintar_existente: function (valores) {
				for (var i = 0; i < valores.length; i++) {
					crear_elemento(campo, true, valores[i]);
				}

				pintar_boton_mas(campo);
			},
			interpretar: function () {
				var valores = [];

				$('.zona_valores p').each(function (index) {
					var valor = leer_elemento(campo, index, $(this));
					valores.push(valor);
				});

				return valores;
			}
		}
	};

	var pintar_boton_mas = function (campo) {
		$('<label></label>').appendTo($('.zona_button'));

		var button_mas = $('<button type="button" class="mas_button">' + _('Añadir valor') + '</button>');	// IDIOMAOK
		//button_mas.html('+');
		button_mas.appendTo($('.zona_button'));
		//button_mas.button();
		button_mas.button({
			icons: {
				primary: "ui-icon-plusthick"
			},
			text: true
		});

		button_mas.click(function (event) {
			crear_elemento(campo, true);
		});
	};

	var pintar_boton_menos = function (paraf_element) {
		var button_menos = $('<button type="button" class="menos_button"></button>');
		button_menos.html('-');
		// paraf_element.append(button_menos);
		button_menos.appendTo(paraf_element);

		button_menos.button({
			icons: {
				primary: "ui-icon-minusthick"
			},
			text: false
		});

		button_menos.click(function (event) {
			//crear_elemento(campo);
			var num_paraf = $('.zona_valores p').length;

			if (num_paraf > 1) {
				paraf_element.remove();
			} else {
				alert(_('El valor seleccionado no se puede eliminar. Debe existir al menos un valor'));	// IDIOMAOK
			}
		});
	};

	var crear_elemento = function (campo, boton_menos, valor) {
		var paraf = $('<p></p>');
		var label = $('<label>' + _('Valor') + '</label>');	// IDIOMAOK
		label.appendTo(paraf);

		if (campo.tipo_camp == "2" || campo.tipo_camp == "3") {
			Endosys.elementos.index(TM.content_editor_busqueda.elementos, { 'campo_id': campo.id_camp }).done(function (elementos) {
				var select = $('<select name="valores" style="width: 200px;"></select>');
				select.append($('<option value="">' + _('Seleccione') + '</option>'));	// IDIOMAOK

				for (var n = 0; n < elementos.length; n++) {
					var option = $('<option value=' + elementos[n].id + '>' + elementos[n].nombre + '</option>');
					option.data("datos_valor", elementos[n]).appendTo(select);
				}

				select.appendTo(paraf);
				console.log("A: " + JSON.stringify(campo));

				if (campo.tipo_camp == "3" && campo.tipo_cont == "2") {
					var opciones = '<option value="MENOR">&lt;</option>';
					opciones += '<option value="MENORIGUAL">&lt;=</option>';
					opciones += '<option value="IGUAL">=</option>';
					opciones += '<option value="MAYORIGUAL" selected>&gt;=</option>';
					opciones += '<option value="MAYOR">&gt;</option>';

					var oper = $('<select name="opciones" style="width: 50px;">' + opciones + '</select>');
					var cantidad = $('<input style="width: 60px;" type="number" step="1" value="1" min="1"></input>');

					if (!!valor && !!valor.cantidad) cantidad.val(valor.cantidad);
					if (!!valor && !!valor.oper) oper.val(valor.oper);

					oper.insertAfter(select);
					cantidad.insertAfter(oper);
				}

				//cuando se trata de modificar un campo
				if (valor) {
					select.find("option[value='" + valor.id + "']").attr("selected", true);
				}

				var zona_valores = $('.zona_valores');
				paraf.appendTo(zona_valores);

				if (boton_menos) {
					pintar_boton_menos(paraf);
				}

				$(".zona_valores").find("select:last").focus();
			});
		} else if (campo.tipo_camp == "4") {
			var checkbox = $('<input type="checkbox">');
			checkbox.appendTo(paraf);

			//cuando se trata de modificar un campo
			if (valor && valor.text == "SI") {
				checkbox.attr("checked", true);
			}

			var zona_valores = $('.zona_valores');
			paraf.appendTo(zona_valores);

			if (boton_menos) {
				pintar_boton_menos(paraf);
			}
		} else {
			var input = $('<input></input>');
			input.appendTo(paraf);
			
			//cuando se trata de modificar un campo
			if (valor) {
				input.val(valor.text);
			}
			
			var zona_valores = $('.zona_valores');
			paraf.appendTo(zona_valores);
			
			if (boton_menos) {
				pintar_boton_menos(paraf);
			}

			if (campo.tipo_camp == "8") {
				input.flatpickr({
					dateFormat: "d/m/Y",
				});
			}
			
			$(".zona_valores").find("input:first").focus();
		}
	};

	var leer_elemento = function (campo, index, paraf) {
		valor = {};

		if (campo.tipo_camp == "2" || campo.tipo_camp == "3") {
			// var datos_valor =paraf.find($("select option:selected")).data().datos_valor;
			var datos_valor = paraf.find("select option:selected").data().datos_valor;
			
			if (datos_valor) {
				valor.id = datos_valor.id;
				valor.text = datos_valor.nombre;

				if (campo.tipo_camp == "3") {
					valor.cantidad = paraf.find("input").val();
					valor.oper = paraf.find('select[name="opciones"]').val();
				}
			}
		} else if (campo.tipo_camp == "4") {
			//if(paraf.find($("input")).is(':checked')){
			if (paraf.find("input").is(':checked')) {
				valor.text = "SI";
			} else {
				valor.text = "NO";
			}

			valor.id = index;
		} else {
			valor.id = index;
			//valor.text = paraf.find($("input")).val();
			valor.text = paraf.find("input").val();
		}

		return valor;
	};

	return {
		get: function (tipo_estructura, campo) {
			if (tipo_estructura == ESTRUCTURA_ENTRE) {
				return entre(campo);
			} else if (tipo_estructura == ESTRUCTURA_SIMPLE) {
				return simple(campo);
			} else if (tipo_estructura == ESTRUCTURA_VARIOS) {
				return varios(campo);
			}
		}
	}
}();

// var estruc = estructura.get(ESTRUCTURA_ENTRE, CAMPO_TEXTO);
// estruc.pintar();
// estructura.get(ESTRUCTURA_ENTRE, CAMPO_SELEC).pintar();