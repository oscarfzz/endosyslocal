var input_tipo_multi = function () {

    return {

        $control: null,
        formdata: null,
        tabla_id: null,
        titulo: '',

        actualizar_option: function (option_el, diff, ocultar_cantidad) { // dif es la cantidad a sumar o restar +1,-1
            if (!ocultar_cantidad) ocultar_cantidad = false;

            if (option_el.length) {
                var cantidad = parseInt(option_el.attr("data-cantidad"), 10);
                var tipo_control = parseInt(option_el.attr("data-tipo-control"), 10);
                var text_mostrar = option_el.attr("data-nombre");
               
                if (tipo_control == 2) {
                    if (!diff) diff = 0; //set 0 si no viene dif

                    // actualizar la cantidad
                    if (cantidad == 0) cantidad = 1; //si tipo de control es 2, la cantidad no puede ser = 0
                    cantidad = cantidad + diff;
                    option_el.attr("data-cantidad", cantidad);

                    if (ocultar_cantidad) {
                        text_mostrar = text_mostrar;
                    } else {
                        text_mostrar = '(' + cantidad + ') ' + text_mostrar;
                    }
                } else {
                    text_mostrar = text_mostrar;
                }

                option_el.text(text_mostrar);
            }
        },

        generar_option: function (elemento, tipo_control, ocultar_cantidad) {           
            var option_el = $('<option value="' + elemento.id + '" title="' + elemento.nombre + '"></option>');
            option_el.attr("data-cantidad", elemento.cantidad);
            option_el.attr("data-nombre", elemento.nombre);
            option_el.attr("data-tipo-control", tipo_control);
            option_el.attr("data-codigo", elemento.codigo);
            input_tipo_multi.actualizar_option(option_el, 0, ocultar_cantidad);
            return option_el;
        },

        // XXX usar controles.modal_dialog
        crear_dialog: function () {
            // XXX cargarlo de un archivo externo
            var contenido_dialog =
                '<form class="pure-form" onsubmit="return false;">' +
                '<div class="pure-g">' +
                '<div class="pure-u-2-5">' +
                '<label for="tipomulti-dialog-todos">' + _('Disponibles') + '</label>' +/*IDIOMAOK*/
                '<input id="tipomulti-dialog-buscar" style="width: 100%; margin: 5px 0px;"  placeholder="' + _('Buscar') + '">' +
                '<select id="tipomulti-dialog-todos" size="16" multiple="multiple" style="width: 100%;"></select>' +
                '</div>' +
                '<div class="pure-u-1-5" style="text-align: center; margin-top: 110px;">' +
                '<div class="seccion">' +
                '<button id="tipomulti-dialog-anadir-btn" type="button" style=" width: 108px;">' + _('Añadir') + '</button>' +/*IDIOMAOK*/
                '</div>' +
                '<div class="seccion">' +
                '<button id="tipomulti-dialog-quitar-btn" type="button" style=" width: 108px;">' + _('Quitar') + '</button>' +/*IDIOMAOK*/
                '</div>' +
                '<div class="seccion">' +
                '<button id="tipomulti-dialog-nuevo_elemento-btn" type="button" style=" width: 108px;">' + _('Nuevo...') + '</button>' +/*IDIOMAOK*/
                '</div>' +
                '</div>' +
                '<div class="pure-u-2-5">' +
                '<label for="tipomulti-dialog-seleccionados">' + _('Seleccionados') + '</label>' +/*IDIOMAOK*/
                '<select id="tipomulti-dialog-seleccionados" size="17" multiple="multiple" style="width: 100%; margin-top:5px;height: 348px;"></select>' +
                '</div>' +
                '</div>' +
                '</form>';

            $('<div id="tipomulti-dialog" />')
                .html(contenido_dialog)
                .appendTo($('body'))
                .dialog({
                    resizable: false,
                    title: _('Seleccionar elementos'),/*IDIOMAOK*/
                    width: "980px",
                    autoOpen: false,
                    modal: true,
                    buttons: [{
                        text: _('Accept'),/*IDIOMAOK*/
                        click: function () {
                            //  Llena la lista de elementos del control a partir de la lista de elementos seleccionados

                            //  comprobar si han cambiado los elementos seleccionados (nuevos elementos, quitados,
                            //  o el orden... es decir, si no es identico) y si es asi, lanzar el evento.
                            var anteriores = input_tipo_multi.$control.find('option').map(function () { return $(this).val() }).get();
                            var ahora = $('#tipomulti-dialog-seleccionados').find('option').map(function () { return $(this).val() }).get();
                            if (''.concat(anteriores) != ''.concat(ahora)) input_tipo_multi.formdata.campo_change();

                            input_tipo_multi.$control.empty();

                            $('#tipomulti-dialog-seleccionados').find('option').each(function (index, element) {
                                //crea los datos
                                var option_sel = $(element);
                                var tipo_control = option_sel.attr("data-tipo-control");
                                el_data = { id: option_sel.val(), nombre: option_sel.attr("data-nombre"), cantidad: 0 };

                                // si por alguna razon cantidad de 0, lo configura a 1, y asigna cantidad           
                                var cantidad = parseInt(option_sel.attr("data-cantidad"), 10);
                                if (cantidad == 0) {
                                    el_data.cantidad = 1;
                                } else {
                                    el_data.cantidad = cantidad;
                                }

                                // crea el elemento y lo agrega
                                option_el = input_tipo_multi.generar_option(el_data, tipo_control);
                                input_tipo_multi.$control.append(option_el);
                            });

                            //reasignar el ancho por un bug en ie8 y ie9
                            input_tipo_multi.$control.attr('size', input_tipo_multi.$control.attr('size'));
                            $(this).dialog('close');
                        }
                    }, {
                        text: _('Cancel'),/*IDIOMAOK*/
                        click: function () {
                            $('#tipomulti-dialog-seleccionados').empty();
                            $(this).dialog('close');
                        }
                    }]
                });

            // Boton añadir
            $('#tipomulti-dialog-anadir-btn')
                .button({ icons: { primary: 'ui-icon-arrowthick-1-e' } })
                .click(function () {
                    $('#tipomulti-dialog-todos option:selected').each(function (i, el) {

                        // si existe actualiza o no hace nada depende el tipo_control
                        option_el = $('#tipomulti-dialog-seleccionados option[value="' + $(el).val() + '"]');
                        if (option_el.length) {
                            input_tipo_multi.actualizar_option(option_el, 1);
                        } else {
                            // si no existe lo agrega 
                            var elemento = { id: $(el).val(), nombre: $(el).attr("data-nombre"), cantidad: $(el).attr("data-cantidad") };
                            var tipo_control = $(el).attr("data-tipo-control");
                            option_el = input_tipo_multi.generar_option(elemento, tipo_control);
                            $('#tipomulti-dialog-seleccionados').append(option_el);
                        }

                        option_el.stop(true, true).effect("highlight", 2000);
                    });
                });

            // Doble click en la lista de disponibles llama a evento añadir
            $('#tipomulti-dialog-todos').dblclick(function () { $('#tipomulti-dialog-anadir-btn').click() });

            // Boton quitar
            $('#tipomulti-dialog-quitar-btn')
                .button({ icons: { primary: 'ui-icon-arrowthick-1-w' } })
                .click(function () {
                    $('#tipomulti-dialog-seleccionados').find('option:selected').each(function (i, el) {
                        // si existe actualiza o no hace nada depende el tipo_control
                        option_el = $(el);
                        var tipo_control = option_el.attr("data-tipo-control");
                        if (tipo_control != 2) {
                            option_el.remove();
                        } else {
                            if (parseInt(option_el.attr("data-cantidad"), 10) == 1) {
                                //elimina pq quedaria en cero
                                option_el.remove();
                            } else {
                                //disminuye en 1
                                input_tipo_multi.actualizar_option(option_el, -1);
                            }
                        }
                    });
                });

            // Doble click en la lista de seleccionados llama a evento quitar
            $('#tipomulti-dialog-seleccionados').dblclick(function () { $('#tipomulti-dialog-quitar-btn').click() });

            // Boton Nuevo elemento
            $('#tipomulti-dialog-nuevo_elemento-btn').button({
                icons: { primary: 'ui-icon-plus' }
            }).click(function () {
                nuevo_elemento.mostrar_inputtipomulti(
                    input_tipo_multi.titulo,
                    input_tipo_multi.tabla_id,
                    $('#tipomulti-dialog-todos'),
                    $('#tipomulti-dialog-seleccionados'),
                    $('#tipomulti-dialog-buscar'),
                    input_tipo_multi.tipo_control
                );
            });
        },

        mostrar: function (titulo, tabla_id, $control, formdata, tipo_control) {
            input_tipo_multi.titulo = titulo;
            input_tipo_multi.tabla_id = tabla_id;
            input_tipo_multi.$control = $control;
            input_tipo_multi.formdata = formdata;
            input_tipo_multi.tipo_control = (tipo_control || 0);

            if (!$('#tipomulti-dialog').length) input_tipo_multi.crear_dialog();

            //  poner un titulo del campo
            $('#tipomulti-dialog').find('label.titulo').html(titulo);
            $('#tipomulti-dialog-buscar').val('');

            // limpiar los campos
            $('#tipomulti-dialog-seleccionados option').remove();
            $('#tipomulti-dialog-todos option').remove();

            //  llenar la lista de ELEMENTOS SELECCIONADOS a partir del control
            $control.find('option').each(function (index, element) {
                var elemento = {
                    id: $(element).val(),
                    nombre: $(element).attr("data-nombre"),
                    cantidad: $(element).attr("data-cantidad")
                };
                var tipo_control = $(element).attr("data-tipo-control");
                option_el = input_tipo_multi.generar_option(elemento, tipo_control);
                $('#tipomulti-dialog-seleccionados').append(option_el);
            });

            //  llenar la lista con TODOS LOS ELEMENTOS a partir de la tabla (SOLO ACTIVOS!)
            gestion_tablas.get_tablas(TM.content_exploraciones.detalles.elementoscampos).then(function (tablas) {
                var params = { 'activo': 1, 'campo_id': tablas[tabla_id].campo_id };

                // Si el campo es de ámbito "por servicio", entonces cargar solo los
                // elementos del servicio activo.
                if (tablas[tabla_id].ambito == "1") {
                    params.servicio_id = Endotools.auth.servicio_activo.id;
                }

                return tablas[tabla_id].rest.index(TM.content_exploraciones.detalles.elementoscampos, params);
            }).done(function (elementos) {
                var lista_elementos = [];

                // Creacion de los todos los elementos disponibles 
                for (var i = 0; i < elementos.length; i++) {
                    var elementName = elementos[i].nombre;
                    if(elementos[i].codigo) elementName = elementos[i].codigo + " - " + elementName

                    el_data = {
                        id: elementos[i].id,
                        nombre: elementName,
                        cantidad: 1,
                        codigo: elementos[i].codigo
                    };

                    //crea los elemento con la cantidad oculta
                    option_el = input_tipo_multi.generar_option(el_data, tipo_control, true);
                    $('#tipomulti-dialog-todos').append(option_el);


                    // Para el autocomplete
                    // valor con el codigo si existe
                    var valor = elementos[i].nombre;
                    if (elementos[i].codigo) {
                        valor = elementos[i].codigo + ' - ' + valor;
                    } 
                    
                    lista_elementos.push({
                        label: valor,
                        value: elementos[i].nombre,
                        id: elementos[i].id
                    });
                }

                function highlightText(text, $node) {
                    //condición para que no lleguen cadenas vacias al subrayado del AUTOCOMPLETE, la cadena vacia hace que funcione mal
                    if ($.trim(text).length > 0) {
                        var searchText = $.trim(text).toLowerCase(), currentNode = $node.get(0).firstChild, matchIndex, newTextNode, newSpanNode;
                        while ((matchIndex = currentNode.data.toLowerCase().indexOf(searchText)) >= 0) {
                            newTextNode = currentNode.splitText(matchIndex);
                            currentNode = newTextNode.splitText(searchText.length);
                            newSpanNode = document.createElement("span");
                            newSpanNode.className = "highlight";
                            currentNode.parentNode.insertBefore(newSpanNode, currentNode);
                            newSpanNode.appendChild(newTextNode);
                        }
                    }
                }

                var $buscar_elemento = $('#tipomulti-dialog').find('#tipomulti-dialog-buscar');
                $buscar_elemento.autocomplete({
                    source: lista_elementos,
                    select: function (event, ui) {
                        //busca el elemento seleccionado del autocomplete en la lista de los seleccionados
                        var option_el = $('#tipomulti-dialog-seleccionados option[value="' + ui.item.id + '"]');

                        //buscar el elemento seleccionado en el autocomplete en la lista de todos los disponibles
                        var option_sel = $('#tipomulti-dialog-todos option[value="' + ui.item.id + '"]');

                        // seleccionar el elemento que se agrego en la lista de todos
                        $('#tipomulti-dialog-todos option').prop("selected", false);
                        option_sel.prop("selected", true);

                        // Si no existe en seleccionados,lo crea y añade
                        if (!option_el.length) {
                            // obtengo los datos del elemento del option seleccionado en la lista de todos los disponibles
                            // se crea con cantidad 1 porque en la lista de todos, los elemento tienen la data-cantidad=1 (aunque no se muestre)
                            elemento = { id: option_sel.val(), nombre: option_sel.attr("data-nombre"), cantidad: option_sel.attr("data-cantidad") };
                            // genero y agrego el opcion que se va a insertar
                            option_el = input_tipo_multi.generar_option(elemento, option_sel.attr("data-tipo-control"));
                            $('#tipomulti-dialog-seleccionados').append(option_el);
                        } else {
                            // sino solo lo actualiza
                            input_tipo_multi.actualizar_option(option_el, 1);
                        }

                        option_el.stop(true, true).effect("highlight", 2000);

                        $(this).val('');
                        return false;
                    },
                    close: function (event, ui) { }
                }).data("ui-autocomplete")._renderItem = function (ul, item) {
                    var $a = $("<a></a>").text(item.label);
                    highlightText(this.term, $a);
                    return $("<li></li>").append($a).appendTo(ul);
                };
            }).always(function () {
                $('#tipomulti-dialog').dialog('open');
            });
        }
    }
}();