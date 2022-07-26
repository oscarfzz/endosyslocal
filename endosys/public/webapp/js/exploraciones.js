var gestion_exploraciones = function () {
    var datatable_results;
    // var etcapcontrol;

    return {
        exploracion_id: null,
        exploracion_borrada: null,
        datatable_results: undefined,
        dialog_callback: null,
        menusItems: {},     // ojo, variable global. Impide que puedan haber 2 forms. simultaneos

        // PAGINACION - Paso 1: Activar paginacion
        paginacion: true,
        _MOUSE_EN_GRAFICO: false,   // XXX

        // Guarda informacion sobre el tab que esta activa en ese momento
        tab_active: {
            formulario: null,
            id: null,
        },

        estado: null,   // El estado de la exploracion

        _ini_form_exploraciones: function (args) {
            /*
             *  ARGS: agregado para hacer el popup de "sin finalizar" en v2.4.8
             *  - ocultar_detalle: True = No muestra el detalle de la exploracion cuando se hace click - Solo selecciona
             *  - callback_dblclick_row: evento que es llamado cuando se hace doble click en la fila
             *  - datatable_el: el contenedor de la tabla. Se tiene que pasar el DOM Nativo o un String
             */

            // Parametros por default
            var args_local = {
                ocultar_detalle: false,
                callback_dblclick_row: undefined,
                datatable_el: "datatable_busqueda_result",
                container: undefined,
            };

            // Recorre los parametros y los guarda en args_local si existen
            if (args != undefined) {
                for (var key in args_local) {
                    if (args.hasOwnProperty(key)) {
                        args_local[key] = args[key];
                    }
                }
            }

            var layout_main_content = $('.layout_main_content');
            if (args_local.container) {
                layout_main_content = args_local.container.children('.layout_main_content');
            }

            /* Inicializa el DataTable. El Layout debe estar ya creado. */

            // Configurarle el data locale al YUI para usarlo en el formatter
            YAHOO.util.DateLocale["es-ES"] = YAHOO.lang.merge(YAHOO.util.DateLocale, { x: "%d/%m/%Y" });

            //funcion que aplica el formateo de la fecha
            var formatterDate = function (container, record, column, data) {
                container.innerHTML = YAHOO.util.Date.format(data, { format: "%x" }, "es-ES");
            };

            //  crear la tabla de resultados
            var fielddef = [
                { key: 'numero', label: 'Nº', width: 50, resizeable: true, sortable: true },
                { key: 'fecha', label: _('Fecha'), width: 80, formatter: formatterDate, resizeable: true, sortable: true },/*IDIOMAOK*/
                { key: 'hora', label: _('Time:Hora'), width: 80, resizeable: true, sortable: true },/*IDIOMAOK*/
                { key: 'idunico', label: opciones_config.IDUNICO_LABEL, width: 100, resizeable: true, sortable: true },/*IDIOMAOK*/
                { key: 'nhc', label: _('NHC'), formatter: "formatNHC", width: 100, resizeable: true, sortable: true },
                { key: 'paciente', label: _('Paciente'), width: 190, resizeable: true, sortable: true },  //  calculado/*IDIOMAOK*/
                { key: 'tipoexploracion', label: _('Abrev:Tipo Exploracion'), width: 140, resizeable: true, sortable: true }, //  calculado/*IDIOMAOK*/
                { key: 'medico', label: _('Médico'), width: 180, resizeable: true, sortable: true }   //  calculado/*IDIOMAOK*/
            ];

            if (opciones_config.MOSTRAR_COLUMNA_SERVICIO_EN_EXPLORACIONES) {
                fielddef.push({ key: 'servicio', label: _('Servicio'), width: 140, resizeable: true, sortable: true });//IDIOMAOK
            }

            if (opciones_config.MOSTRAR_COLUMNA_CENTRO_EN_EXPLORACIONES) {
                fielddef.push({ key: 'centro', label: _('Centro'), width: 160, resizeable: true, sortable: true });//IDIOMAOK
            }

            gestion_exploraciones.datatable_results = new YAHOO.widget.ScrollingDataTable(
                args_local.datatable_el, fielddef, dummyDataSource, {
                initialLoad: false,
                MSG_EMPTY: '<em>' + _('No se ha encontrado ninguna exploración') + '</em>',/*IDIOMAOK*/
                height: "200px",    //  solo para que tenga el scrollbar, luego el alto es dinámico.
                width: "100%"
            });

            datatable_results = gestion_exploraciones.datatable_results;

            controles.init_YUI_datatable(datatable_results, { m_inferior: 45, layoutPaneResizing: layout_main_content.layout().panes.north });

            //  columnas 'calculadas' (que no se extraen directamente de los campos devueltos por el datasource)
            datatable_results.doBeforeLoadData = function (sRequest, oResponse, oPayload) {
                var centro_id = Endosys.auth.servicio_activo.centro_id
                for (var n = 0; n < oResponse.results.length; n++) {
                    oResponse.results[n].idunico = oResponse.results[n].paciente.idunico;
                    oResponse.results[n].nhc = "";
                    for (var i = 0; i < oResponse.results[n].paciente.centros.length; i++) {
                        if (oResponse.results[n].paciente.centros[i].id === centro_id) {
                            oResponse.results[n].nhc = oResponse.results[n].paciente.centros[i].nhc;
                            break;
                        }
                    }
                    oResponse.results[n].paciente = (oResponse.results[n].paciente.nombre || "") + ' ' + (oResponse.results[n].paciente.apellido1 || "") + ' ' + (oResponse.results[n].paciente.apellido2 || "");
                    oResponse.results[n].tipoexploracion = oResponse.results[n].tipoExploracion.nombre;
                    oResponse.results[n].medico = oResponse.results[n].medico.nombre;

                    if (opciones_config.MOSTRAR_COLUMNA_SERVICIO_EN_EXPLORACIONES) {
                        oResponse.results[n].servicio = oResponse.results[n].servicio ? oResponse.results[n].servicio.nombre : "";
                    }

                    if (opciones_config.MOSTRAR_COLUMNA_CENTRO_EN_EXPLORACIONES) {
                        //mostrar el centro que se relaciona con el servicio actual y no
                        //el que essta en el modelo exploraciones
                        oResponse.results[n].centro = oResponse.results[n].centro ? oResponse.results[n].centro.nombre : null;
                    }

                    // Obtiene el campo string y lo convierte a tipo Date de javascript.
                    var aFecha = oResponse.results[n].fecha.split("/");
                    var aHora = oResponse.results[n].hora.split(":");
                    oResponse.results[n].fecha = new Date(aFecha[2], parseInt(aFecha[1], 10) - 1, aFecha[0], aHora[0], aHora[1], aHora[2]);
                }
                return true;

            };

            // Si por parametro viene una funcion del dobleclick entonces crea el evento y llama a esa funcion
            if (args_local.callback_dblclick_row) {
                datatable_results.subscribe("rowDblclickEvent", function (oArgs) {
                    this.unselectAllRows();
                    this.selectRow(oArgs.target);
                    this.clearTextSelection();
                    if (!datatable_results.getRecord(oArgs.target)) return; //  comprobar que la fila tiene record asignado (porque la fila con el mensaje 'no hay resultados' no tiene record y daria error)
                    args_local.callback_dblclick_row(datatable_results.getRecord(oArgs.target).getData("id"));
                });
            }

            //  evento click en una fila de la tabla
            datatable_results.subscribe("rowClickEvent", function (oArgs) {
                this.unselectAllRows();
                this.selectRow(oArgs.target);
                this.clearTextSelection();
                if (!datatable_results.getRecord(oArgs.target)) return; //  comprobar que la fila tiene record asignado (porque la fila con el mensaje 'no hay resultados' no tiene record y daria error)

                // Muestra la exploracion si ocultar detalle = false
                if (!args_local.ocultar_detalle) {
                    gestion_exploraciones._mostrar_exploracion(datatable_results.getRecord(oArgs.target).getData("id"), $("#detalle_exploracion"));
                }
            });

            if (opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'IDUNICO') {
                datatable_results.hideColumn("nhc")
            }

            if (opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'NHC') {
                datatable_results.hideColumn("idunico")
            }

            layout_main_content.layout().options.north.onresize();

        },

        _fin_form_exploraciones: function (o) {
            if (gestion_exploraciones.datatable_results) {
                gestion_exploraciones.datatable_results.destroy();
                gestion_exploraciones.datatable_results = null;
                datatable_results = null;
            }
        },

        _ini_botones: function (exploracion) {
            var paciente_id = exploracion.paciente_id;

            if (opciones_config["EWC_MODO.ACTIVO"] == 1) {
                // Se crea el link del nuevo Endosys App Client
                $("#exploracion-capturar-btn").button().click(function () {
                    $("#exploracion-capturar-btn").prop("disabled", true);
                    $("#exploracion-capturar-btn").addClass("btn-disabled");
                    $("#exploracion-capturar-btn").children(".ui-button-text").text(_("Abriendo"));//IDIOMAOK
                    unset_prevenir_refresco_manual(1000);

                    var port = document.location.port ? ("||" + document.location.port) : "";
                    var server = window.location.hostname + port;
                    var url = "endosysapp:a=capture,e=" + exploracion.id + ",p=" + exploracion.paciente.id + ",s=" + server;
                    window.open(url, "_self");

                    // deshabilita el boton por X segundos para evitar que sea presionado nuevamente.
                    setTimeout(function () {
                        $("#exploracion-capturar-btn").prop("disabled", false);
                        $("#exploracion-capturar-btn").children(".ui-button-text").text(_("Capturar"));//IDIOMAOK
                        $("#exploracion-capturar-btn").removeClass("btn-disabled");
                    }, 5000);
                });

            } else {
                $("#exploracion-capturar-btn").button().click(function () {
                    //  iniciar la captura
                    //  configurar el etcapcontrol

                    // Configura el puerto segun segun el protocolo y
                    // luego si hay datos del puerto o si usa el por defecto
                    var port;
                    if (document.location.protocol == 'https:') {
                        port = document.location.port ? document.location.port : 443;
                    } else {
                        port = document.location.port ? document.location.port : 80;
                    }
                    gestion_captura.etcapcontrol.protocol = document.location.protocol;

                    var host = document.location.hostname;
                    gestion_captura.configurar({ 'port': port, 'host': host });

                    try {
                        //etcapcontrol.ejecutar_captura();
                        gestion_captura.ejecutar_captura();
                    } catch (err) {
                        Endosys.statusbar.mostrar_mensaje(_('No se ha podido ejecutar el programa de captura'), 1);/*IDIOMAOK*/
                    }
                });
            }


            //  Botón importar imágenes ///////////////////////////////////////////////
            var contador = 0;   /*  este contador servirá para controlar cuándo se han enviado todos los ficheros (aunque hayan dado error),
                                    y asi poder recargar la pestaña de imágenes */

            $('#captura-importarimg-btn').button();
            $('#captura-importar-fileupload').fileupload({
                url: '/rest/capturas',
                formData: [
                    {
                        name: 'exploracion_id',
                        value: exploracion.id
                    }
                ],

                dataType: 'xml',

                start: function (e) {
                },

                always: function (e, result) {
                    /*  Al terminar el envio de cada fichero (sea correcto o no) se ejecuta el always.
                        Usando la variable contador se controla cuando ha terminado con todos, para
                        recargar la pestaña de capturas.
                    */

                    contador--;
                    if (contador <= 0) {
                        imagenes_expl.set_transactionmanager(TM.content_exploraciones.detalles.imagenes);
                        imagenes_expl.obtener_thumbs(gestion_exploraciones.exploracion_id, $('#exploracion-tab-imagenes>.ui-layout-center>ul'));
                        //cargar las pestaña de imagenes
                        //dependiendo de si existe la pestaña cita la posición de la pestaña imagnes sera una o otra
                        if ($('#exploracion-tab-info').length) {
                            $('#exploracion_form_tabview').tabs('option', 'active', 2)
                        } else {
                            $('#exploracion_form_tabview').tabs('option', 'active', 1)
                        }
                    }
                },

                add: function (e, data) {
                    /*  Se ejecuta por cada archivo seleccionado para subir, antes de que
                        empiecen a enviarse. Se puede hacer un filtrado para no enviar
                        no admitidos, demasiado grandes, etc... Para los que pasan el filtro
                        se tiene que llamar a data.submit()
                    */

                    var acceptFileTypes = /^image\/(jpe?g)|(bmp)|(png)$/i;
                    var uploadErrors = [];

                    if (!acceptFileTypes.test(data.files[0]['type'])) {
                        //var msg = "El fichero '" + data.files[0]['name'] + "' no se puede cargar porque su extensión no está permitida.";
                        var msg = sprintf(_("El fichero '%s' no se puede cargar porque su extensión no está permitida."), data.files[0]['name']); /*IDIOMAOK*/
                        uploadErrors.push(msg);
                    }

                    if (data.files[0]['size'] && data.files[0]['size'] > opciones_config.IMAGEN_UPLOAD_SIZE) {
                        //var msg = "El fichero '" + data.files[0]['name'] + "' no se puede cargar porque tiene un tamaño superior al permitido.";
                        var msg = sprintf(_("El fichero '%s' no se puede cargar porque tiene un tamaño superior al permitido."), data.files[0]['name']); /*IDIOMAOK*/
                        uploadErrors.push(msg);
                    }
                    if (uploadErrors.length > 0) {
                        alert(uploadErrors.join("\n"));
                    } else {
                        contador++;
                        data.submit();
                    }

                }
            }).click(function (e) {
                contador = 0;
            });

            $("#exploracion-mostrar-paciente").click(function () {
                //  mostrar el paciente
                gestion_pacientes.mostrar_paciente(paciente_id);
            });

            //  si no está finalizada, mostrar el botón de Capturar
            if (exploracion.estado == 0) {
                $("#exploracion-capturar-btn").show();
                $("#captura-importarimg-btn").show();
            }

            if (exploracion.estado == 1 && Endosys.auth.username == "sysadmin") {
                $("#captura-importarimg-btn").show();
            }
        },

        buscar_exploraciones: function (params, $total, $btnexportar) {
            // PAGINACION
            // Paso 2: Set de parametros y asignacion de pagina que se va a pedir
            if (gestion_exploraciones.paginacion) {
                gestion_paginacion.set_params(params);
                params._pagina = gestion_paginacion.pagina_actual;
            }

            var link = Endosys.exploraciones.resource + ".csv?" + jQuery.param(params);


            //Crear una tarea de Exportar
            $('#exportar_exploraciones_hilo').button();
            $('#exportar_exploraciones_hilo').unbind('click');
            $("#exportar_exploraciones_hilo").bind("click", function () {
                // Hace una copia de params y no una referencia
                // asi params queda exactamenete igual y no afecta
                // a las demas partes del sistema

                var parametros = $.extend(true, {}, params);
                parametros["tipo_tarea"] = "EXP";
                parametros["recurso"] = "exploraciones";
                parametros["format"] = "csv";
                gestion_tareas.crear_exportar(parametros)

            });

            if ($btnexportar) {
                $btnexportar.attr("href", link);
                $btnexportar.button();
            }

            var args = datatable_results ? { datatable: datatable_results } : null;
            return Endosys.exploraciones.index(
                TM.content_exploraciones.buscar,
                params,
                args
            ).done(function (exploraciones, textStatus, jqXHR) {
                // >> PAGINACION - Crear html y eventos del paginador
                if (gestion_exploraciones.paginacion) {
                    // PASO 3: Crear html del paginador
                    gestion_paginacion.asignar_contenedores($("#paginacion"), $('#total-exploraciones'));
                    gestion_paginacion.crear_paginador();

                    // PASO 4: Evento 1 - Click en el link del numero de pagina
                    $("#paginacion a").bind("click", function () {
                        gestion_paginacion.cambiar_pagina($(this));
                        gestion_exploraciones.buscar_exploraciones(
                            params,
                            $('#total-exploraciones'),
                            $("#exportar_excel")
                        );
                    });

                    // PASO 5: Evento 2 - Cuando se presiona el enter en el input de la pagina actual
                    $("#pagina-actual").bind("keydown", function (e) {
                        if (e.keyCode == 13) {
                            gestion_paginacion.cambiar_pagina($(this));
                            gestion_exploraciones.buscar_exploraciones(
                                params,
                                $('#total-exploraciones'),
                                $("#exportar_excel")
                            );
                        }
                    });
                    // << PAGINACION
                } else {
                    if ($total) $total.html(exploraciones.length);
                }

                if (exploraciones && exploraciones.length == 0) {
                    // no se ha encontrado ninguna exploracion
                    Endosys.statusbar.mostrar_mensaje(_('No se ha encontrado ninguna exploración'));  /*IDIOMAOK*/
                }
            }).fail(function (exploraciones) {
                if ($total) $total.html(0);
            });
        },

        obtener_exploracion: function (tm, id, $form_node, $tabs, callback) {
            // obtener los datos completos de una exploracion por el Id
            Endosys.statusbar.mostrar_mensaje(_('Obteniendo los datos de la exploración...'));    /*IDIOMAOK*/
            gestion_exploraciones.estado = null;
            gestion_exploraciones._deshabilitar_guardar();
            Endosys.exploraciones.show(tm, id).done(function (exploracion) {
                // extraer los formularios directamente del xml, no se puede hacer con el schema (que yo sepa)
                var _formularios = [];
                for (var i = 0; i < exploracion.formularios.length; i++) {
                    _formularios.push({
                        id: Number(exploracion.formularios[i].id),
                        titulo: exploracion.formularios[i].titulo,
                        controles: [],
                        formdata: null
                    });
                }

                //  XXX
                //  El grafico
                //              var grafico_img = $('#exploracion_form_tabview 
                //#exploracion-tab-imagenes>.ui-layout-east>img');
                //              grafico_img.attr("src", "/res/grafico_" + exploracion.tipoExploracion.codigo + ".jpg")
                var grafico_div = $('#exploracion_form_tabview #exploracion-tab-imagenes>.ui-layout-east>div');
                grafico_div.css("background-color", '#FFFFFF');
                grafico_div.css("background-repeat", 'no-repeat');
                grafico_div.css("background-image", 'url("/res/grafico_' + exploracion.tipoExploracion.codigo + '.jpg")');

                //construimos la papelera para eliminar flechas de posicionamiento
                var $papelera = $('<img id="papelera" src="/res/papelera.png" style="position: absolute;">');
                $papelera.css('right', '0px');
                $papelera.css('top', '0px');
                $papelera.css('margin-top', '5px');
                $papelera.css('margin-right', '5px');
                $papelera.droppable({
                    accept: ".flecha",
                    hoverClass: "papelera_over",
                    drop: function (event, ui) {
                        Endosys.imagenes.update(
                            tm,
                            ui.draggable.data("imagen").id,
                            { 'posx': null, 'posy': null }
                        );

                        ui.draggable.remove();
                        //el codigo comentado es para cuando se elimina una flecha roja se deseleccione su captura relacionada
                        //se decide que no sea asi por eso se comenta codigo
                        /*if(ui.draggable.attr("src") == "/res/flecha_grafico_seleccionada.png"){
                            $("#captura"+ui.draggable.data("imagen").id+"").css("background-color", "transparent");
                        }*/
                    }
                });

                $('#exploracion_form_tabview #exploracion-tab-imagenes>.ui-layout-east').append($papelera);

                if (callback && callback.success) callback.success(exploracion);

                $form_node.find('#num_exploracion').html(exploracion.numero);
                $form_node.find('#num_exploracion').attr("tittle", exploracion.id);
                $form_node.find('#tipo_exploracion').html(exploracion.tipoExploracion.nombre);

                // muestra el numero de exploracion sobre la cantidad de exploraciones que se hicieron del mismo tipo.
                if (opciones_config["TIPOS_EXPLORACION.MOSTRAR_NUMERO"] || opciones_config["TIPOS_EXPLORACION.MOSTRAR_CONTADOR"]) {
                    if (exploracion.estado == 0) {
                        $form_node.find('#numero_tipo_exploracion').html("(" + exploracion.numero_tipo_exploracion.posicion + ")");
                    } else {
                        $form_node.find('#numero_tipo_exploracion').html("(" + exploracion.numero_tipo_exploracion.posicion + "/" + exploracion.numero_tipo_exploracion.total + ")");
                    }
                }

                $form_node.find('#fecha').html(exploracion.fecha);
                $form_node.find('#hora').html(exploracion.hora);
                if (opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'NHC' || opciones_config.IDENTIFICADORES_PACIENTE.toUpperCase() === 'NHC+IDUNICO') {
                    var centro_id = Endosys.auth.servicio_activo.centro_id;
                    $form_node.find('#historia').html("");

                    if (!!exploracion.paciente.centros) {
                        for (var i = 0; i < exploracion.paciente.centros.length; i++) {
                            if (exploracion.paciente.centros[i].id === centro_id) {
                                $form_node.find('#historia').html(exploracion.paciente.centros[i].nhc);
                                break;
                            }
                        }
                    }
                } else {
                    $form_node.find('#historia').html(exploracion.paciente.idunico || "");
                }

                var paciente = (exploracion.paciente.nombre || "") + ' ' + (exploracion.paciente.apellido1 || "") + ' ' + (exploracion.paciente.apellido2 || "");
                if (exploracion.edad_paciente) {
                    paciente = paciente + ', ' + exploracion.edad_paciente + ' ' + _('años');/*IDIOMAOK*/
                }

                // Rellenar aqui los campos de la pestaña info, en la sección
                // "Datos exploración".
                $("#expl_tipo").val(exploracion.tipoExploracion.nombre);
                $("#expl_hora").val(exploracion.hora);
                $("#expl_fecha").val(exploracion.fecha);
                $("#expl_medico").val(exploracion.medico.nombre);

                // Rellenar la aseguradora - se tienen que haber cargado antes!
                // las carga la función cargar_datos_info().
                $('#expl_aseguradora').val(exploracion.aseguradora_id);

                // Rellenar la información del paciente y del médico, que están
                // encima de las pestañas.
                $form_node.find('#paciente').html(paciente);
                $form_node.find('#medico').html(exploracion.medico.nombre);

                //  recorrer los formularios y crear un tab por cada uno
                //  usar el queue para cargarlos uno detras del otro
                var chain = $.when();
                var formularios_responses = [];
                var paneles_agregados = 0;

                $(_formularios).each(function (i, _formulario) {
                    //  crear el Tab (jQuery)
                    var tab_id = "tabs-formularios-" + _formulario.id;
                    $tabs.tabs("add", tab_id, _formulario.titulo).tabs("refresh").tabs("option", "active", -1);  //  OK para jQueryUI >= 1.10

                    $('#' + tab_id).addClass('tab_exploracion').data('formulario', _formulario);  //  guardar la referencia

                    //_formulario.$contenedor = $('#' + tab_id);
                    //  poner dentro de un form, para aplicar estilos de pure a los inputs
                    //  el evento onsubmit="return false" evita una feature no deseada: En un form con solo un
                    //  input tipo text (y posiblemente otros campos) al pulsar enter se ejecuta el submit
                    $('#' + tab_id).html('<form onsubmit="return false" class="pure-form pure-form-stacked"></form>');
                    _formulario.$contenedor = $('#' + tab_id).find('form');

                    //  cola de carga de formularios
                    chain = chain.then(function () {
                        //  obtener los datos completos del formulario de una exploracion por los Ids
                        return Endosys.formularios.show(tm, _formulario.id, { 'exploracion_id': id })
                            .done(function (response) {
                                formularios_responses.push({ "response": response, "_formulario": _formulario });
                                //                          formularios.generar_formulario(response, _formulario, false, exploracion);
                            });
                    });
                    paneles_agregados++;
                });

                // -->> 2.4.9: Si esta en el tab de imagenes, activa el refresco
                //              de imagenes segun el estado de la exploracion
                $("#exploracion_form_tabview").on('tabsactivate', function (event, ui) {
                    // Entra a Tab
                    // Actualiza la informacion del tab activa
                    gestion_exploraciones.tab_active.id = ui.newPanel.selector;
                    if ($("#" + ui.newPanel.attr("id")).data()) {
                        gestion_exploraciones.tab_active.formulario = $("#" + ui.newPanel.attr("id")).data('formulario');
                    } else {
                        gestion_exploraciones.tab_active.formulario = null;
                    }

                    // El tab de imagenes esta seleccionda
                    if (gestion_exploraciones.tab_active.id == "#exploracion-tab-imagenes") {
                        refresh_imagenes.set_exploracion_estado(gestion_exploraciones.estado);
                    } else {
                        refresh_imagenes.terminar();
                    }

                });

                // Activamos el primer formulario
                $tabs.tabs("option", "active", 0 - paneles_agregados === 0 ? -1 : -paneles_agregados);

                //  cuando ha cargado todos los formularios, generarlos (eso carga los elementos, entre otras cosas...)
                //  XXX antes se hacia directamente, sin usar el array "formularios_responses"... se ha
                //      cambiado para no cargar los elementos mientras se cargan los formularios,
                //      ya que eso ralentiza... probar que asi funcione bien!
                chain.done(function () {
                    for (var i = 0; i < formularios_responses.length; i++) {
                        formularios.generar_formulario(formularios_responses[i].response, formularios_responses[i]._formulario, false, exploracion);
                    }

                    if (exploracion.borrado) {
                        gestion_exploraciones._deshabilitar_edicion();
                    } else {
                        gestion_exploraciones._habilitar_guardar();
                    }
                });
            }).fail(function () {
                if (callback && callback.failure) callback.failure();
                Endosys.statusbar.mostrar_mensaje(_('Ha ocurrido un error obteniendo los datos de la exploración'), 1);/*IDIOMAOK*/
            });
        },

        iscomplete: function (campo, valor) {
            if (campo.tipo == 4) {
                //si es tipo checkbox y el campo es obligatorio se ha de mirar q este chequeado
                if (valor != 1) {
                    var msg = campo.titulo;
                    throw msg;
                }
            } else {
                if ($.trim(valor) == "") {
                    var msg = campo.titulo;
                    throw msg;
                }
            }
        },

        guardar_exploracion: function (tm, exploracion_id, $form_node, $tab_capturas/*, callback*/) {
            Endosys.statusbar.mostrar_mensaje(_('Guardando la exploración...'));/*IDIOMAOK*/
            var updates = [];

            //  extraer los valores de los campos para enviar por REST
            //  recorrer todos los tabs de formularios
            var errores_validacion = []
            forms_to_update = []; // guarda el id y los params de los formularios a actualizar
            $form_node.find('.tab_exploracion').each(function (index, el) {
                var obligatorios = "";
                var params = {};
                var formulario = $(el).data('formulario');
                formulario.formdata.get_valores_controles(function (control_obj, valor) {
                    params[control_obj.campo_id] = valor;
                    if (control_obj.campo.obligatorio == true) {
                        try {
                            gestion_exploraciones.iscomplete(control_obj.campo, valor);
                        } catch (e) {
                            errores_validacion.push(formulario.titulo + ": " + e);
                        }
                    }
                });
                forms_to_update.push({ 'form_id': formulario.id, 'params': params });
            });

            // hubo algun error de la validacion de campos obligatorios. devuevle un promise con los errores
            if (errores_validacion.length > 0) {
                var defer = $.Deferred();
                var promise = defer.promise();
                defer.reject({ 'tipo_error': 'campos_obligatorios', 'contenido': errores_validacion });
                return promise;
            }

            //  Guardar el orden de las capturas
            if ($tab_capturas) {
                var capturas = [];
                $tab_capturas.find("li.endosys-imagen-container>a").each(function (index, el) {
                    capturas.push($(el).data("imagen").id);
                });
                updates.push(Endosys.exploraciones.update(
                    tm,
                    exploracion_id,
                    {
                        'orden_capturas': capturas.join(),
                        aseguradora_id: $("#expl_aseguradora").val() === "" ? null : $("#expl_aseguradora").val()
                    }
                ));
            }

            // comprobar que no tenga errores_validacion no tiene sentido, ya que se comprueba mas arriba,
            // pero se deja explicito para que se entienda
            if (errores_validacion.length == 0) {
                // solo agrega al array de updates si la validacion de todos es correcta.
                // porque al agregarlos ya se ejecutan y si el primero es success y el segundo es fail,
                // los datos del primero se grabaron pero es incorrecto pq hay un fallo en la finalizacion
                // de la exploracion
                for (var i = 0; i < forms_to_update.length; i++) {
                    updates.push(
                        Endosys.formularios.update(
                            tm,
                            forms_to_update[i].form_id,
                            $.extend(forms_to_update[i].params, { 'exploracion_id': exploracion_id })
                        )
                    );
                }

                return $.when.apply($, updates);
            }
        },

        valores_por_defecto_from_form: function (tm, $form) {
            //  extraer los valores de los campos para enviar por REST como valores por defecto
            //      recorrer todos los tabs de formularios
            //  XXX esta funcion está sacada de endosys.exploraciones.guardar_exploracion(), mirar
            //      si se puede compartir código...
            //  XXX Esta mal
            $form.find('.tab_exploracion').each(function (index, el) {
                var params = {};
                var formulario = Yto$(el).data('formulario');

                for (var i = 0; i < formulario.controles.length; i++) {
                    var $control = formulario.controles[i].$control;
                    //  extraer el valor segun el tipo de campo
                    var valor = '';
                    //      TIPO TEXTO
                    if (esControlTipo($control, Endosys.campos.TIPO_TEXTO)) {
                        //  el valor esta en el atributo value del control, que es un HTMLElement (mas concretamente un HTMLInputElement)
                        valor = $control.val();
                        //      TIPO SELECCION
                    } else if (control.hasClass('campo-tipo-selec')) {
                        //  el valor esta en el atributo value del elemento button
                        valor = Endosys.Y.one(control._button).get('value');
                        //      TIPO BOOL
                        //} else if (control.hasClass('endosys-checkbox')) {
                    } else if (esControlTipo(control, Endosys.campos.TIPO_BOOL)) {
                        //  el valor esta en el atributo value del elemento button
                        valor = control.get('checked') ? 1 : 0;
                        //      TIPO MEMO
                    } else if (esControlTipo(control, Endosys.campos.TIPO_MEMO)) {
                        valor = Endosys.Y.one(control).get('value');
                        //      TIPO MULTI
                    } else if (esControlTipo(control, Endosys.campos.TIPO_MULTI)) {
                        //  todos los ids de los elementos seleccionados separados por comas
                        valor = '';
                        control.all('option').each(function (node) {
                            valor += node.get('value') + ',';
                        });
                        if (valor != '') valor = valor.substr(0, valor.length - 1);   //  quitar la ultima coma (si la hay)
                    }
                    params[formulario.controles[i].campo_id] = valor;
                }

                params['_modo'] = 'VALORESPORDEFECTO';
                Endosys.formularios.update(tm, formulario.id, params);
            });
        },

        _mostrar_exploracion: function (exploracion_id, $contenedor) {
            gestion_exploraciones.exploracion_id = exploracion_id;
            //  abortar las transacciones pendientes que puedan estar cargando los elementos de los campos de tipo selec
            //  XXX hacer esto al cambiar a cualquier pantalla!

            TM.content_exploraciones.detalles.elementoscampos.abort();

            //  mostrar la exploración
            TM.content_exploraciones.detalles.load_content($contenedor, "content/exploracion.html" + ew_version_param()).done(function () {
                // Tab de imágenes
                $('#exploracion-tab-imagenes').layout({
                    east__size: 320,
                    east__resizable: true,
                    slidable: true,
                    spacing_closed: 10
                });

                // Gráfico
                var grafico_img = $('#exploracion_form_tabview #exploracion-tab-imagenes>.ui-layout-east>div');
                grafico_img.mouseenter(function () {
                    gestion_exploraciones._MOUSE_EN_GRAFICO = true;
                });
                grafico_img.mouseleave(function () {
                    gestion_exploraciones._MOUSE_EN_GRAFICO = false;
                });

                // Obtener las miniaturas (de forma async)
                imagenes_expl.set_transactionmanager(TM.content_exploraciones.detalles.imagenes);
                imagenes_expl.obtener_thumbs(gestion_exploraciones.exploracion_id, $('#exploracion-tab-imagenes>.ui-layout-center>ul'));

                // Añadir el tab de "info" delante de el de "Informes"...
                $('a[href$="#exploracion-tab-informes"]').parent().before('<li><a href="#exploracion-tab-info"><i class="fa fa-lg fa-info-circle" aria-hidden="true"></i></a></li>');
                $('#exploracion-tab-informes').before('<div id="exploracion-tab-info"></div>');

                // ...y cargar la info (de forma async)
                var promise = gestion_exploraciones.cargar_datos_info();

                // Exploración

                // crear TabView
                var $tabs = $('#exploracion_form_tabview').tabs();

                // Esperar a que termine cargar_datos_info(), para que esté
                // creada la pestaña info, y las aseguradorasr cargadas.
                promise.then(function (cita) {
                    gestion_exploraciones.obtener_exploracion(
                        TM.content_exploraciones.detalles,
                        gestion_exploraciones.exploracion_id,
                        $("#exploracion_form"),
                        $tabs,
                        {
                            success: function (exploracion) {
                                // Actualiza el estado de gestion_exploracion
                                gestion_exploraciones.estado = exploracion.estado;

                                //$("#captura_link").attr("href", "endosysapp:a=capture,e="+exploracion.id+",p="+exploracion.paciente.id)
                                //
                                // ---EWC
                                //

                                //!!!!DESACTIVA CIERRE SESSION!!!!
                                cierre_sesion.desactivar();
                                gestion_exploraciones._ini_botones(exploracion);

                                //  boton para asignar valores por defecto
                                $('#exploracion-asignarvaloresdefecto-btn').button().click(function () {
                                    gestion_exploraciones.valores_por_defecto_from_form(TM.operaciones, $("#exploracion_form"));
                                });

                                if (exploracion.borrado) {
                                    $("#exploracion_borrada").show();
                                    $("#exploracion_borrada").click(function () {
                                        controles.modal_dialog.mostrar({
                                            title: _('Motivo'),/*IDIOMAOK*/
                                            resizable: false,
                                            height: "auto",
                                            width: "auto",
                                            enterAccept: true,
                                            buttons: [{
                                                text: _('Aceptar'),/*IDIOMAOK*/
                                                click: controles.modal_dialog._Aceptar
                                            }],
                                            init: function (accept) {
                                                var container = $("#generic-dialog");
                                                container.html(exploracion.borrado_motivo);
                                            }
                                        });
                                    });
                                } else {
                                    $("#exploracion_borrada").hide();
                                }

                                //  segun el estado activar/desactivar controles
                                if (exploracion.estado == 0) {
                                    //  NO FINALIZADA

                                    //  "ocultar" tab de informes
                                    informes.desactivar_form();
                                    informes.crear_btn_informes_anteriores(exploracion.paciente.id);

                                    /// BOTON FINALIZAR
                                    $('#exploracion-guardar-btn').button({ label: _('Finalizar') }).click(function () {/*IDIOMAOK*/
                                        /*
                                        hasta ahora el orden era:
                                            1 - finalizar_exploracion()
                                            2 - guardar_exploracion()
                                            3 - _mostrar_exploracion()

                                        ahora el orden es:
                                            1 - guardar_exploracion()
                                            2 - finalizar_exploracion()
                                            3 - _mostrar_exploracion()

                                        Ya que en alguna integración (Sant Boi...) se necesitan datos introducidos
                                        en los campos de la exploración en el momento de finalizarla, para utilizarlos
                                        en el mensaje de captura de actividad, y tal como estaba antes aun no se
                                        habían almacenado.
                                        */

                                        //  Ahora:

                                        //  desactiva el botón para no pulsarlo varias veces seguidas por error
                                        $('#exploracion-guardar-btn').attr('disabled', 'disabled');

                                        gestion_exploraciones.guardar_exploracion(
                                            TM.operaciones,
                                            gestion_exploraciones.exploracion_id,
                                            $("#exploracion_form"),
                                            $("#exploracion-tab-imagenes")
                                        ).then(
                                            function () { // success del then
                                                // Pone el estado a 1, que es 'finalizado'
                                                return Endosys.exploraciones.update(
                                                    TM.operaciones,
                                                    gestion_exploraciones.exploracion_id,
                                                    { 'estado': 1 }
                                                );
                                            },

                                            function (response) { // fail del then
                                                return response;
                                            }
                                        ).done(function () {
                                            Endosys.statusbar.mostrar_mensaje(_('Exploración finalizada correctamente'));/*IDIOMAOK*/

                                            // Recargar la exploracion
                                            gestion_exploraciones._mostrar_exploracion(gestion_exploraciones.exploracion_id, $contenedor);
                                            gestion_exploraciones.estado = 1;
                                        }).fail(function (response) {
                                            gestion_exploraciones._mostrar_error_guardar_exploracion(response);

                                            //  activa de nuevo el botón SOLO si ha fallado
                                            //  Si ha ido bien no vale la pena activarlo porque se recarga la pantalla
                                            $('#exploracion-guardar-btn').attr('disabled', null);
                                        });
                                    });

                                    /// BOTON CANCELAR - NO REALIZADA
                                    // Si no se permite la cancelacion de citas/exploraciones en el INI, quitar el botón.
                                    if (opciones_config.CANCELAR_CITAS_EXPLORACIONES == 0) {
                                        $("#exploracion-cancelar-btn").hide();
                                    } else {
                                        $('#exploracion-cancelar-btn').button({ label: _('No realizada') }).click(function () { /*IDIOMAOK*/
                                            // cancelar la exploracion
                                            controles.confirm_dialog(
                                                _('Exploración no realizada'),  /*IDIOMAOK*/
                                                _('¿Está seguro de que desea no realizar la exploración? se perderán los cambios realizados'),  /*IDIOMAOK*/

                                                function () {
                                                    var _do_cancelar = function (motivo_cancelacion) {
                                                        Endosys.exploraciones.update(
                                                            TM.operaciones,
                                                            gestion_exploraciones.exploracion_id,
                                                            { 'estado': 2, 'motivo_id': motivo_cancelacion }
                                                        ).done(function () {
                                                            reset_pantalla();
                                                            //ACTIVAR CIERRE DE SESION
                                                            cierre_sesion.activar();
                                                            contenido_principal.cerrar('#mainlayout');
                                                            gestion_exploraciones.estado = null;
                                                            Endosys.statusbar.mostrar_mensaje(_('La exploración se ha marcado como "No Realizada"'));/*IDIOMAOK*/
                                                        });
                                                    }

                                                    if (opciones_config.USAR_MOTIVO_CANCELACION) {
                                                        motivo_cancelacion_dialog.mostrar().done(function (motivo_cancelacion) {
                                                            //  enviar el motivo de fallo a la cita...
                                                            if (motivo_cancelacion == null) {
                                                                Endosys.statusbar.mostrar_mensaje(_('No ha seleccionado un motivo de cancelación'), 1);   /*IDIOMAOK*/
                                                            } else {
                                                                _do_cancelar(motivo_cancelacion);
                                                            }
                                                        });
                                                    } else {
                                                        _do_cancelar();
                                                    }
                                                }
                                            );
                                        });
                                    }

                                    /// BOTON DESCARTAR
                                    $('#exploracion-descartar-btn').show();
                                    $('#exploracion-descartar-btn').button().click(function () {
                                        var confirm_dialog = confirm("¿Esta seguro?");

                                        if (confirm_dialog) {
                                            //Borrar la exploracion
                                            Endosys.exploraciones['delete'](
                                                TM.nueva_exploracion,
                                                exploracion.id,
                                                { 'borrado_motivo': 'Descartar' }
                                            ).done(function () {
                                                reset_pantalla();

                                                contenido_principal.cerrar('#mainlayout', cierre_sesion.activar);
                                                Endosys.statusbar.mostrar_mensaje(_('La exploración ha sido descartada'), 0);/*IDIOMAOK*/
                                                gestion_exploraciones.estado = null;
                                                //ACTIVAR CIERRE
                                                cierre_sesion.activar();
                                            }).fail(function (data) {
                                                if (data.responseText) {
                                                    error = parseError(data.responseText);
                                                    Endosys.statusbar.mostrar_mensaje(error, 1);
                                                }
                                            });
                                        }
                                    });

                                    $('#exploracion-recuperar-btn').hide();
                                    $('#exploracion-borrar-btn').hide();
                                } else {
                                    //  FINALIZADA
                                    // si abre una finalizada, entonces puede venir de dos lugares.
                                    // 1) si se guardo recientemente
                                    // 2) si viene por un click desde un datatable de un editar de busqueda
                                    //    Si es asi no tengo que desactivar busqueda ni poner en null los set                                   if (!ejecutar_busqueda.activo){

                                    //desactivar el ir hacia atras
                                    if (!ejecutar_busqueda.activo) {
                                        desactivar_asistente();
                                        set_atras(null);
                                        set_continuar(null);
                                    }

                                    //  INFORMES
                                    informes.ini_form_expl();
                                    informes.crear_btn_informes_anteriores(exploracion.paciente.id);

                                    /// BOTON GUARDAR
                                    $('#exploracion-guardar-btn').button({ label: _('Save') }).click(function () {/*IDIOMAOK*/
                                        gestion_exploraciones.guardar_exploracion(
                                            TM.operaciones,
                                            gestion_exploraciones.exploracion_id,
                                            $("#exploracion_form"),
                                            $("#exploracion-tab-imagenes")
                                        ).done(function () {
                                            Endosys.statusbar.mostrar_mensaje(_('Exploración guardada correctamente'));/*IDIOMAOK*/
                                        }).fail(function (response) {
                                            gestion_exploraciones._mostrar_error_guardar_exploracion(response);
                                        });
                                    });

                                    // boton deshacer
                                    $('#exploracion-cancelar-btn').button({ label: _('Deshacer cambios') }).click(function () {/*IDIOMAOK*/
                                        // recargar los datos descartando los cambios realizados
                                        controles.confirm_dialog(
                                            _('Deshacer cambios'),
                                            _('¿Está seguro de que desea deshacer los cambios realizados?'),/*IDIOMAOK*/
                                            function () {
                                                gestion_exploraciones._mostrar_exploracion(exploracion_id, $contenedor);
                                            }
                                        );
                                    });

                                    // oculta el boton de descartar
                                    $('#exploracion-descartar-btn').hide();
                                }

                                /// BOTON BORRAR - 2.4.10
                                $('#exploracion-borrar-btn').button({ label: _('Borrar') }).click(function () {//IDIOMAOK
                                    //Borrar la exploracion finalizada // borrado logico 2.4.10
                                    controles.confirm_dialog(
                                        _('Borrar exploración'),
                                        _('¿Está seguro de que desea borrar la exploración?'),/*IDIOMAOK*/

                                        function () {
                                            controles.input_dialog.mostrar(
                                                _('Motivo'),    //IDIOMAOK
                                                _('Ingrese el motivo por el cual desea borrar:'),   //IDIOMAOK
                                                ''
                                            ).then(function (motivo) {
                                                if (motivo != "") {
                                                    Endosys.exploraciones['delete'](
                                                        TM.nueva_exploracion,
                                                        exploracion.id,
                                                        { 'borrado_motivo': motivo }
                                                    ).done(function () {
                                                        reset_pantalla();
                                                        contenido_principal.cerrar('#mainlayout', cierre_sesion.activar);
                                                        Endosys.statusbar.mostrar_mensaje(_('La exploración ha sido eliminada'), 0);/*IDIOMAOK*/
                                                        gestion_exploraciones.estado = null;
                                                        //ACTIVAR CIERRE
                                                        cierre_sesion.activar();
                                                    }).fail(function (data) {
                                                        if (data.responseText) {
                                                            error = parseError(data.responseText);
                                                            Endosys.statusbar.mostrar_mensaje(error, 1);
                                                        }
                                                    });
                                                } else {
                                                    Endosys.statusbar.mostrar_mensaje(_("Debe completar el motivo"), 1);//IDIOMAOK
                                                }
                                            });
                                        }
                                    );
                                });

                                /// BOTON Recuperar - 2.4.10
                                $('#exploracion-recuperar-btn').button({ label: _('Recuperar') }).click(function () {//IDIOMAOK
                                    //Borrar la exploracion finalizada // borrado logico 2.4.10
                                    controles.confirm_dialog(
                                        _('Recuperar exploración'),
                                        _('¿Está seguro de que desea recuperar la exploración?'),/*IDIOMAOK*/
                                        function () {
                                            Endosys.exploraciones.update(TM.nueva_exploracion, exploracion.id, { '_recuperar': 1 }).done(function () {
                                                // Recargar la exploracion
                                                gestion_exploraciones._mostrar_exploracion(gestion_exploraciones.exploracion_id, $contenedor);
                                            }).fail(function (data) {
                                                if (data.responseText) {
                                                    error = parseError(data.responseText);
                                                    Endosys.statusbar.mostrar_mensaje(error, 1);
                                                }
                                            });
                                        }
                                    );
                                });

                                if (!exploracion.borrado) {
                                    $('#exploracion-recuperar-btn').hide();
                                    $('#exploracion-recuperar-btn').button("option", "disabled", true);
                                } else {
                                    $('#exploracion-borrar-btn').hide();
                                    $('#exploracion-borrar-btn').button("option", "disabled", true);
                                }

                                if (!userinfo.tiene_permiso("borrado_logico")) {
                                    $('#exploracion-borrar-btn').hide();
                                    $('#exploracion-recuperar-btn').hide();
                                }

                                /*if (exploracion.borrado){
                                    alert(1);
                                    gestion_exploraciones._deshabilitar_edicion();
                                }*/
                                // seleccionar la ultima pestaña
                                // tabView.selectTab(tabView.get('tabs').length - 1);
                            }
                        }
                    );
                });
            });
        },

        una: {
            mostrar: function (exploracion_id) {
                //  muestra solo una exploracion
                gestion_exploraciones.exploracion_id = null;
                TM.content_exploraciones.activate();
                TM.content_exploraciones.buscar.activate();
                TM.content_exploraciones.detalles.activate();
                TM.content_exploraciones.detalles.elementoscampos.activate();
                TM.content_exploraciones.detalles.textospredefinidos.activate();
                TM.content_exploraciones.detalles.informes.activate();
                TM.content_exploraciones.detalles.imagenes.activate();
                TM.content_exploraciones.detalles.cita.activate();
                Endosys.statusbar.mostrar_mensaje(_('Cargando la exploración...'));/*IDIOMAOK*/

                mainlayout.html("<div class='endo_pane_redondeado endo-panel endo_pane_content'></div>");

                gestion_exploraciones._mostrar_exploracion(exploracion_id, $('#mainlayout>div'));
            },

            cerrar: function () {
            }
        },

        avanzada: {
            mostrar: function (_busqueda) {
                gestion_exploraciones.exploracion_id = null;
                TM.content_exploraciones.activate();
                TM.content_exploraciones.buscar.activate();
                TM.content_exploraciones.detalles.activate();
                TM.content_exploraciones.detalles.elementoscampos.activate();
                TM.content_exploraciones.detalles.textospredefinidos.activate();
                TM.content_exploraciones.detalles.informes.activate();
                TM.content_exploraciones.detalles.imagenes.activate();
                TM.content_exploraciones.detalles.cita.activate();
                Endosys.statusbar.mostrar_mensaje(_('Cargando gestión de exploraciones...'));/*IDIOMAOK*/
                TM.content_exploraciones.load_content(mainlayout, "content/busqueda_exploraciones.html" + ew_version_param()).done(function () {
                    //crear layouts
                    $('.layout_main_content').layout({
                        north__size: 280,
                        spacing_closed: 10,
                        slideTrigger_open: "click",
                        initClosed: false
                    });

                    gestion_exploraciones._ini_form_exploraciones();
                    gestion_exploraciones.datatable_results.subscribe("rowDblclickEvent", function () {
                        //  doble click en una expl cierra el panel
                        $('.layout_main_content').layout().close('north');
                    });
                    gestion_exploraciones.buscar_exploraciones({ estado: 1, '_busqueda': _busqueda }, $('#total-exploraciones'), $("#exportar_excel"));
                });
            },
            cerrar: function () {
                gestion_exploraciones._fin_form_exploraciones();
            }
        },

        por_fecha: {
            mostrar: function (callback_fn) {
                gestion_exploraciones.exploracion_id = null;
                TM.content_exploraciones.activate();
                TM.content_exploraciones.buscar.activate();
                TM.content_exploraciones.detalles.activate();
                TM.content_exploraciones.detalles.elementoscampos.activate();
                TM.content_exploraciones.detalles.textospredefinidos.activate();
                TM.content_exploraciones.detalles.informes.activate();
                TM.content_exploraciones.detalles.imagenes.activate();
                TM.content_exploraciones.detalles.cita.activate();
                Endosys.statusbar.mostrar_mensaje(_('Cargando gestión de exploraciones...'));/*IDIOMAOK*/

                TM.content_exploraciones.load_content(mainlayout, "content/busqueda_exploraciones_fecha.html" + ew_version_param()).done(function () {
                    // CREAR LAYOUT
                    $('.layout_main_content').layout({
                        north__size: 480,
                        spacing_closed: 10,         // tamaño de la barra una vez cerrada
                        slideTrigger_open: "click",    // default
                        initClosed: false
                    });

                    $('.contenedor2').layout({
                        west__size: 370,
                        west__resizable: false,
                        slidable: true,
                        spacing_closed: 10
                    });

                    //  configurar la gestion de exploraciones
                    if (!userinfo.tiene_permiso("borrado_logico")) {
                        $("#busquedaexpl-eliminados").hide();
                    }

                    gestion_exploraciones._ini_form_exploraciones();
                    gestion_exploraciones.datatable_results.subscribe("rowDblclickEvent", function () {
                        //  doble click en una expl cierra el panel
                        $('.layout_main_content').layout().close('north');
                    });

                    //  crear TabView form busqueda
                    var $tabs = $('#busquedaexpl-tabview').tabs({ active: 0 });// OK para jQueryUI >= 1.10

                    //  crear calendario para busqueda de un dia
                    $("#busqueda-undia-datepicker").flatpickr({
                        inline: true,
                        locale: 'es',
                        mode: 'range',
                        format: "Y-m-d",
                        onChange: function (selectedDates, dateStr, instance) {
                            console.log(selectedDates)
                            if (selectedDates.length === 2) {
                                var fecha_min = selectedDates[0].toLocaleString().split(',')[0];
                                var fecha_max = selectedDates[1].toLocaleString().split(',')[0];
                                buscarEntre2fechas(fecha_min, fecha_max)
                            }

                            if (selectedDates.length === 1) {
                                var fecha_min = selectedDates[0].toLocaleString().split(',')[0];
                                buscarPorFecha(fecha_min)
                            }
                            

                        }
                    })

                    //  boton buscar (entre 2 fechas)
                    function buscarEntre2fechas(fecha_min, fecha_max) {
                        var args = { estado: 1 };

                        if (fecha_min) args.fecha_min = fecha_min;
                        if (fecha_max) args.fecha_max = fecha_max;
                        if (!fecha_min && !fecha_max) {
                            Endosys.statusbar.mostrar_mensaje(_('Debe introducir un rango de fechas antes de iniciar la búsqueda'), 1);
                            return;
                        } else {
                            if (Endosys.auth.servicio_activo) {
                                args.servicio_activo = Endosys.auth.servicio_activo.id;
                            }

                            if ($("#checkbox-buscar-eliminados").prop("checked")) {
                                args.borrado = 1;
                            }

                            gestion_exploraciones?.buscar_exploraciones(args, $('#total-exploraciones'), $("#exportar_excel"));
                        }
                    };

                    //  boton buscar (una sola fecha)
                    function buscarPorFecha (fecha) {
                        var args = { estado: 1 };
                        if (fecha) args.fecha = fecha;
                        if (Endosys.auth.servicio_activo) args.servicio_activo = Endosys.auth.servicio_activo.id;
                        if ($("#checkbox-buscar-eliminados").prop("checked")) args.borrado = 1;

                        gestion_exploraciones?.buscar_exploraciones(args, $('#total-exploraciones'), $("#exportar_excel"));
                    };

                    //  boton semana actual (entre 2 fechas)
                    $('#busqueda-semanaactual-btn').button().click(function () {
                        var s;
                        var dia = new Date();

                        // buscar cuantos dias han pasado desde el lunes anterior (el 0 es domingo, lo tengo en cuenta!)
                        var totaldias = (dia.getDay() == 0) ? (7 - 1) : (dia.getDay() - 1);
                        // buscar el lunes restando los dias
                        dia.setTime(dia.getTime() - (totaldias * (24 * 60 * 60 * 1000)));
                        s = dia.getDate() + '/' + (dia.getMonth() + 1) + '/' + dia.getFullYear();
                        $("#busqueda-fecha-inicio").val(s);
                        // buscar el domingo sumando 6
                        dia.setTime(dia.getTime() + (6 * (24 * 60 * 60 * 1000)));
                        s = dia.getDate() + '/' + (dia.getMonth() + 1) + '/' + dia.getFullYear();
                        $("#busqueda-fecha-fin").val(s);
                        $("#busqueda-buscar-btn").click();
                    });

                    // boton mes actual (entre 2 fechas)
                    $('#busqueda-mesactual-btn').button().click(function () {
                        var s;
                        var dia = new Date();
                        // buscar el dia 1 de este mes
                        var diauno = new Date(dia.getFullYear(), dia.getMonth(), 1);
                        // buscar el dia 1 del mes que viene (o enero del año que viene si es diciembre) y restarle uno
                        if (dia.getMonth() == 11) {
                            var ultimodia = new Date(dia.getFullYear() + 1, 0, 1);
                        } else {
                            var ultimodia = new Date(dia.getFullYear(), dia.getMonth() + 1, 1);
                        }
                        ultimodia.setTime(ultimodia.getTime() - (1 * (24 * 60 * 60 * 1000)));

                        s = diauno.getDate() + '/' + (diauno.getMonth() + 1) + '/' + diauno.getFullYear();
                        $("#busqueda-fecha-inicio").val(s);
                        s = ultimodia.getDate() + '/' + (ultimodia.getMonth() + 1) + '/' + ultimodia.getFullYear();
                        $("#busqueda-fecha-fin").val(s);
                        $("#busqueda-buscar-btn").click();
                    });

                    //  boton hoy (una sola fecha)
                    $('#busqueda-hoy-btn').button().click(function () {
                        var hoy = new Date();
                        hoy = hoy.getDate() + '/' + (hoy.getMonth() + 1) + '/' + hoy.getFullYear();
                        $("#busqueda-fecha-undia").val(hoy);
                        $("#busqueda-undia-btn").click();
                    });

                    //  boton ayer (una sola fecha)
                    $('#busqueda-ayer-btn').button().click(function () {
                        var ayer = new Date();
                        ayer.setTime(ayer.getTime() - (1 * (24 * 60 * 60 * 1000)));
                        ayer = ayer.getDate() + '/' + (ayer.getMonth() + 1) + '/' + ayer.getFullYear();
                        $("#busqueda-fecha-undia").val(ayer);
                        $("#busqueda-undia-btn").click();
                    });

                    //  buscar todas las exploraciones de hoy
                    $("#busqueda-hoy-btn").click();

                    Endosys.statusbar.mostrar_mensaje(_('Ready'));/*IDIOMAOK*/

                    if (callback_fn) callback_fn();
                });
            },

            cerrar: function () {
                gestion_exploraciones._fin_form_exploraciones();
            }
        },

        sin_finalizar: {
            mostrar_popup: function () {
                gestion_exploraciones.exploracion_id = null;
                TM.content_exploraciones.activate();
                TM.content_exploraciones.buscar.activate();
                TM.content_exploraciones.detalles.activate();
                TM.content_exploraciones.detalles.elementoscampos.activate();
                TM.content_exploraciones.detalles.textospredefinidos.activate();
                TM.content_exploraciones.detalles.informes.activate();
                TM.content_exploraciones.detalles.imagenes.activate();
                TM.content_exploraciones.detalles.cita.activate();
                Endosys.statusbar.mostrar_mensaje(_('Cargando gestión de exploraciones...'));//IDIOMAOK

                var seleccionar = function () {
                    var record = datatable_results.getRecord(gestion_exploraciones.datatable_results.getSelectedRows()[0]);

                    if (!record) return;
                    var exploracion_id = record.getData("id");
                    contenido_principal.mostrar(gestion_exploraciones.una, exploracion_id);
                    $('#generic-dialog').dialog("close");
                    set_titulo_pantalla(_("Exploración sin finalizar"), _('Realizando exploración'));/*IDIOMAOK*/
                    if (opciones_config.MOSTRAR_ATRAS_EXPLORACION) {
                        activar_asistente();
                        set_atras(function () {
                            nueva_exploracion.reconstruir_nueva_exploracion(exploracion_id);

                            //llamar ir hacia atras
                            nueva_exploracion._ir_hacia_atras(exploracion_id);
                        });

                        set_continuar(null);
                    } else {
                        desactivar_asistente();
                        set_atras(null);
                        set_continuar(null);
                    }
                }

                var cancelar = function () {
                    $('#generic-dialog').dialog("close");
                }

                controles.modal_dialog.mostrar({
                    title: _('Seleccionar exploración sin finalizar'),/*IDIOMAOK*/
                    height: 600,
                    width: 1000,
                    dialogClass: "dialog_exploracion_sin_finalizar",
                    buttons: [{
                        id: "btn-seleccionar-expl",
                        text: _("Seleccionar"),//IDIOMAOK
                        click: seleccionar
                    }, {
                        text: _("Cancelar"),//IDIOMAOK
                        click: cancelar
                    }],
                    resizable: false,
                    enterAccept: false,
                    result: function () { },
                    init: function (accept) {
                        var container = $("#generic-dialog");

                        TM.content_exploraciones.load_content(container, "content/busqueda_exploraciones.html" + ew_version_param()).done(function () {
                            container.children('.layout_main_content').layout({
                                spacing_closed: 0,
                                slideTrigger_open: "click",
                                initClosed: false
                            });

                            var args = {
                                ocultar_detalle: true,
                                callback_dblclick_row: seleccionar,
                                datatable_el: $("#generic-dialog #datatable_busqueda_result")[0], // Necesita el DOM nativo por eso se hace el [0]
                                container: container
                            };

                            gestion_exploraciones._ini_form_exploraciones(args);
                            //  buscar exploraciones con estado=0 y del mismo medico
                            gestion_exploraciones.buscar_exploraciones({ estado: 0, medico_id: Endosys.auth.medico_id, servicio_activo: Endosys.auth.servicio_activo.id }, $('#total-exploraciones'), $("#exportar_excel"));

                            //ocultar los bordes
                            container.find(".ui-layout-north").removeClass("endo_pane_redondeado");
                        });
                    }
                });
            },

            mostrar: function () {
                gestion_exploraciones.exploracion_id = null;
                TM.content_exploraciones.activate();
                TM.content_exploraciones.buscar.activate();
                TM.content_exploraciones.detalles.activate();
                TM.content_exploraciones.detalles.elementoscampos.activate();
                TM.content_exploraciones.detalles.textospredefinidos.activate();
                TM.content_exploraciones.detalles.informes.activate();
                TM.content_exploraciones.detalles.imagenes.activate();
                TM.content_exploraciones.detalles.cita.activate();
                Endosys.statusbar.mostrar_mensaje(_('Cargando gestión de exploraciones...'));//IDIOMAOK
                TM.content_exploraciones.load_content(mainlayout, "content/busqueda_exploraciones.html" + ew_version_param()).done(function () {
                    //crear layouts
                    $('.layout_main_content').layout({
                        north__size: 280,
                        spacing_closed: 10,
                        slideTrigger_open: "click",
                        initClosed: false
                    });

                    gestion_exploraciones._ini_form_exploraciones();
                    //  buscar exploraciones con estado=0 y del mismo medico
                    gestion_exploraciones.buscar_exploraciones({ estado: 0, medico_id: Endosys.auth.medico_id, servicio_activo: Endosys.auth.servicio_activo.id }, $('#total-exploraciones'), $("#exportar_excel"));
                });
            },

            cerrar: function () {
                gestion_exploraciones._fin_form_exploraciones();
            }
        },

        por_paciente: {
            mostrar: function (paciente_id) {
                gestion_exploraciones.exploracion_id = null;
                TM.content_exploraciones.activate();
                TM.content_exploraciones.buscar.activate();
                TM.content_exploraciones.detalles.activate();
                TM.content_exploraciones.detalles.elementoscampos.activate();
                TM.content_exploraciones.detalles.textospredefinidos.activate();
                TM.content_exploraciones.detalles.informes.activate();
                TM.content_exploraciones.detalles.imagenes.activate();
                TM.content_exploraciones.detalles.cita.activate();
                Endosys.statusbar.mostrar_mensaje(_('Cargando gestión de exploraciones...'));/*IDIOMAOK*/
                TM.content_exploraciones.load_content(mainlayout, "content/busqueda_exploraciones.html" + ew_version_param()).done(function () {
                    $('.layout_main_content').layout({
                        north__size: 280,
                        spacing_closed: 10,
                        slideTrigger_open: "click",
                        initClosed: false
                    });

                    gestion_exploraciones._ini_form_exploraciones();
                    gestion_exploraciones.datatable_results.subscribe("rowDblclickEvent", function () {
                        //  doble click en una expl cierra el panel
                        $('.layout_main_content').layout().close('north');
                    });
                    //  buscar exploraciones del paciente indicado
                    gestion_exploraciones.buscar_exploraciones({ estado: 1, 'paciente_id': paciente_id, servicio_activo: Endosys.auth.servicio_activo.id }, $('#total-exploraciones'), $("#exportar_excel"));
                });
            },

            cerrar: function () {
                gestion_exploraciones._fin_form_exploraciones();
            }
        },

        mostrar_numero_expl_dialog: function () {
            return controles.input_dialog.mostrar(
                _('Buscar por número de exploración'),  // IDIOMAOK
                _('Número de exploración'), // IDIOMAOK
                ''
            ).then(function (numero_expl) {
                // Busca la exploracion
                TM.content_exploraciones.activate();
                TM.content_exploraciones.buscar.activate();
                TM.content_exploraciones.detalles.activate();
                TM.content_exploraciones.detalles.elementoscampos.activate();
                TM.content_exploraciones.detalles.textospredefinidos.activate();
                TM.content_exploraciones.detalles.informes.activate();
                TM.content_exploraciones.detalles.imagenes.activate();
                TM.content_exploraciones.detalles.cita.activate();

                return gestion_exploraciones.buscar_exploraciones({ numero: numero_expl, servicio_activo: Endosys.auth.servicio_activo.id });
            }).then(function (exploraciones) {
                var deferred = $.Deferred();

                if (exploraciones[0]) {
                    // Hay exploracion, devuelve la primera
                    deferred.resolve(exploraciones[0]);
                } else {
                    // No encontro exploracion
                    Endosys.statusbar.mostrar_mensaje(_('No se ha encontrado ninguna exploración con este número'));/*IDIOMAOK*/
                    deferred.reject();
                }

                return deferred.promise();
            });
        },

        set_tiempos_captura: function (tiempo_total, tiempo_retirada) {
            //  asignar los tiempos a los campos predefinidos __TIEMPO_TOTAL y __TIEMPO_RETIRADA
            //  han de ser de TIPO TEXTO
            //  XXX aqui los valores son strings indicando los segundos. De momento se convierten
            //  a un formato HH:MM:SS, hasta que se cree un tipo de campo de "duración/cantidad de tiempo"
            //  (ahora mismo este valor no sirve para búsquedas!)
            tiempo_total = seconds_to_hhmmss(Number(tiempo_total) || 0);
            tiempo_retirada = seconds_to_hhmmss(Number(tiempo_retirada) || 0);

            //  recorrer todos los formularios de la exploración, y en cada uno buscar estos campos
            //  XXX YUI... pasar a jquery
            $("#exploracion_form").find('.tab_exploracion').each(function (index, el) {
                var formulario = $(el).data('formulario');
                var control;
                control = formularios.get_control_by_nombrecampo(formulario, '__TIEMPO_TOTAL');
                if (control && esControlTipo(control.control, Endosys.campos.TIPO_TEXTO)) {
                    $(control.control).val(tiempo_total);
                }
                control = formularios.get_control_by_nombrecampo(formulario, '__TIEMPO_RETIRADA');
                if (control && esControlTipo(control.control, Endosys.campos.TIPO_TEXTO)) {
                    $(control.control).val(tiempo_retirada);
                }
            });
        },

        // gestion_exploraciones.cargar_datos_info()
        //
        // Carga la pestaña de info.
        // Devuelve un promise, con un param con la cita en json, o null
        // si no tiene cita.
        //
        // NOTA: La sección "Datos exploración" en la pestaña de info no
        // se rellena aquí, sino desde obtener_exploracion(), pues es
        // quien obtiene esta información (Tipo de exploración, médico,
        // fecha, hora y aseguradora).
        cargar_datos_info: function () {
            return TM.content_exploraciones.detalles.cita.load_content(
                '#exploracion_form_tabview #exploracion-tab-info',
                "content/exploracion_info.html" + ew_version_param()
            ).then(function () {
                // Poner como solo lectura todos los controles
                $('#exploracion-tab-info input, #exploracion-tab-info textarea').attr({
                    readonly: 'readonly'/*, style: 'background-color: #E4FFF0'*/
                });

                // Aseguradora - crear el control, y obtener las aseguradoras
                // de forma async para llenar el listado.
                var $aseguradora = $(document).find('select#expl_aseguradora');
                $aseguradora.append($('<option value="">-</option>'));

                Endosys.aseguradoras.index(TM.operaciones, { 'activo': 1 }).done(function (aseguradoras) {
                    for (var i = 0; i < aseguradoras.length; i++) {
                        if ($aseguradora.find('option[value="' + aseguradoras[i].id + '"]').length < 1) {
                            $aseguradora.append($('<option value="' + aseguradoras[i].id + '">' + aseguradoras[i].nombre + '</option>'));
                        }
                    }
                });

                // Cargar datos de la Cita
                return Endosys.citas.index(TM.content_exploraciones.detalles.cita, { exploracion_id: gestion_exploraciones.exploracion_id });
            }).then(function (citas) {
                // Si no ha devuelto ninguna cita, salir
                if (citas.length == 0) {
                    $('#exploracion-seccion-cita').hide();
                    return null;
                }

                $('#exploracion-seccion-cita').show();
                var cita = citas[0];
                //  asignar los datos de la cita a los campos (se entiende que ha devuelto 1 cita)
                $('#fecha_cita_expl').val(cita.fecha);
                $('#hora_cita_expl').val(cita.hora);
                $('#observaciones_cita_expl').val(cita.observaciones);
                if (cita.agenda)
                    $('#agenda_cita_expl').val(cita.agenda.nombre);
                if (cita.prioridad)
                    $('#prioridad_cita_expl').val(cita.prioridad.nombre);
                if (cita.ex) {
                    $('#prestacion_cita_expl').val(cita.ex.prestacion_descr);
                    $('#servicio_petic_cita_expl').val(cita.ex.servicio_peticionario_descr);
                    $('#medico_petic_cita_expl').val(cita.ex.medico_peticionario_descr);
                }
                if (cita.aseguradora_id && $('#expl_aseguradora').val() === "") {
                    $('#expl_aseguradora').val(cita.aseguradora_id);
                }
                return cita;
            });
        },

        _deshabilitar_edicion: function () {
            $(".tab_exploracion").find("input, select, textarea, button").prop("disabled", true);
            $(".tab_exploracion").find("button").button("option", "disabled", true);
            $("#exploracion-generar-btn").button("option", "disabled", true);
            $("#exploracion-invalido-btn").button("option", "disabled", true);
            $(".tab_exploracion").find('input[type="checkbox"]').button("option", "disabled", true);
            $("#exploracion-cancelar-btn").button("option", "disabled", true);
            $("#exploracion-guardar-btn").button("option", "disabled", true);
        },

        _habilitar_guardar: function () {
            // habilita el boton de guardar.
            // aqui ya existe el button y usa el .button para habilitar
            $("#exploracion-guardar-btn").button("option", "disabled", false);
        },

        _deshabilitar_guardar: function () {
            // deshabilita el boton de guardar
            // usa el prop pq todavia no esta realizado el .button
            $("#exploracion-guardar-btn").prop("disabled", true);
        },

        // el parametro response tiene que ser el que viene por el fail del guardar_exploracion
        // esta funcion se ejecuta cuando se finaliza o cuando se actualiza la exploracion
        _mostrar_error_guardar_exploracion: function (response) {
            var error_generico = _('Error al finalizar la Exploración');/*IDIOMAOK*/

            if (response && response.tipo_error) {
                if (response.tipo_error == "campos_obligatorios") {
                    // muestra error por pantalla de los campos obligatorios
                    var msg = _('La exploración no se ha guardado, existen campos obligatorios sin rellenar.');/*IDIOMAOK*/
                    msg = msg + " (" + response.contenido.join([separator = ', ']) + ")";
                    Endosys.statusbar.mostrar_mensaje(msg, 1);
                } else {
                    Endosys.statusbar.mostrar_mensaje(error_generico, 1)
                }
            } else {
                Endosys.statusbar.mostrar_mensaje(error_generico, 1)
            }
        }
    }
}();
