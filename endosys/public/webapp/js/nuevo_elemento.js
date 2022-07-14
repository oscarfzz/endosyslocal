var nuevo_elemento = function() {

    return {

        $control: null,
        formdata: null,
        tabla_id: null,
        callback: null,


        _mostrar_camposelec_success: function(id, nombre) {
            //  añadir el nuevo item y seleccionarlo
            $('<option />').html(nombre).val(id).appendTo(nuevo_elemento.$control);
            nuevo_elemento.$control.val(id);
            nuevo_elemento.$control.data('valor_anterior', id);
            nuevo_elemento.formdata.campo_change();
        },
        
        _mostrar_camposelec_success2: function(id, nombre) {
            //borrar cache
            nuevo_elemento.$control.dataSource.flushCache();
            nuevo_elemento.$control._elTextbox.value_element = id;
            nuevo_elemento.$control._elTextbox.value =  nombre;
            nuevo_elemento.formdata.campo_change();
        },

        _mostrar_inputtipomulti_success: function(id, nombre) {
            var listados = nuevo_elemento.$control;

            tipo_control = listados.tipo_control;
            el_data = {id: id, nombre: nombre, cantidad: 1};
            option_el_todos =  input_tipo_multi.generar_option(el_data, tipo_control, true);
            option_el_selec =  input_tipo_multi.generar_option(el_data, tipo_control);

            //  añadir el nuevo item al listado de todos los elementos y al de elementos seleccionados
            listados.todos.append(option_el_todos);
            listados.seleccionados.append(option_el_selec);
            var list_search = listados.busqueda_autocomplete.autocomplete( "option", "source" );
            list_search.push({label: nombre, value: nombre, id:id});

            option_el_selec.stop(true, true).effect("highlight", 2000);
        },

        //  XXX usar controles.input_dialog
        crear_dialog: function() {
            $('<div id="nuevoelemento-dialog" />')
             .html($('<form onsubmit="return false" class="pure-form"><label style="margin-right: 8px;">' + _('Elemento') + '</label> <input name="nombre" type="text" /></form>'))/*IDIOMAOK*/
             .appendTo($('body'))
             .dialog({
                resizable: false,
                title: _('Nuevo elemento'),/*IDIOMAOK*/
                width: "360px",
                autoOpen: false,
                modal: true,
                buttons: [{
                    text: _('Accept'),/*IDIOMAOK*/
                    click: function() {
                        that = this;
                        var nuevoelemento = $('#nuevoelemento-dialog input').val();

                        if (nuevoelemento!=""){
                            //  crear el nuevo elemento
                            gestion_tablas.get_tablas(TM.content_exploraciones.detalles.elementoscampos)
                            
                            .then(function(tablas) {
                                var params = {nombre: nuevoelemento, activo: '1'};
                                if ((tablas[nuevo_elemento.tabla_id].rest == Endosys.elementos) || (tablas[nuevo_elemento.tabla_id].rest == Endosys.predefinidos)) {
                                    params.campo_id = tablas[nuevo_elemento.tabla_id].id.split('_')[1];
                                }
                                
                                // Si es un listado de elementos de un campo con ambito "`por servicio",
                                // al crear el nuevo elemento se asigna el servicio activo.
                                // si no hay servicio activo, lanzar error.
                                if ((tablas[nuevo_elemento.tabla_id].rest == Endosys.elementos) && (tablas[nuevo_elemento.tabla_id].ambito == 1)) {
                                    if ( Endosys.auth.servicio_activo && Endosys.auth.servicio_activo.id) {
                                        params.servicio_id = Endosys.auth.servicio_activo.id;
                                    } else {
                                        throw _("No se puede añadir un nuevo elemento a un campo con ámbito 'por servicio' porque no hay ningún servicio activo.");
                                    }
                                }
                                
                                return tablas[nuevo_elemento.tabla_id].rest.create(TM.content_exploraciones.detalles.elementoscampos, params, null);
                            })
                            
                            .done(function(elemento) {
                                if (nuevo_elemento.callback && nuevo_elemento.callback.success)
                                    nuevo_elemento.callback.success(elemento.id, nuevoelemento);
                                $(that).dialog('close');
                            })
                            .fail(function(response){
                                Endosys.statusbar.mostrar_mensaje(parseError(response.responseText), 1);
                            });
                        }else{
                            alert(_("No se puede crear un elemento con texto vacio"));
                        }
                    }
                }, {
                    text: _('Cancel'),/*IDIOMAOK*/
                    click: function() {
                        $(this).dialog('close');
                    }
                }]
            });
        },

        mostrar: function(titulo, tabla_id, callback) {
            if (!$('#nuevoelemento-dialog').length) nuevo_elemento.crear_dialog();
            $('#nuevoelemento-dialog label').html(titulo);
            $('#nuevoelemento-dialog input').val('');
            nuevo_elemento.tabla_id = tabla_id;
            nuevo_elemento.callback = callback;
            $('#nuevoelemento-dialog').dialog('open');
        },

        mostrar_camposelec: function(titulo, tabla_id, $control, formdata) {
            nuevo_elemento.$control = $control;
            nuevo_elemento.formdata = formdata;
            nuevo_elemento.mostrar(titulo, tabla_id, { success: nuevo_elemento._mostrar_camposelec_success });
        },
        
        mostrar_camposelec2: function(titulo, tabla_id, $control, formdata) {
            nuevo_elemento.$control = $control;
            nuevo_elemento.formdata = formdata;
            nuevo_elemento.mostrar(titulo, tabla_id, { success: nuevo_elemento._mostrar_camposelec_success2 });
        },

        mostrar_inputtipomulti: function(titulo, tabla_id, listado_todos, listado_seleccionados, autocomplete, tipo_control) {
            nuevo_elemento.$control = {todos: listado_todos, seleccionados: listado_seleccionados, busqueda_autocomplete: autocomplete, tipo_control: tipo_control};
            nuevo_elemento.mostrar(titulo, tabla_id, { success: nuevo_elemento._mostrar_inputtipomulti_success });
        },

        // 2.4.9: Funcion para crear un nuevo elemento desde un memo, sin pasar por el dialog 
        // y agregarlo en el control relacionado al memo.
        // @nombre Es el nombre del elemento.
        // @tabla_id Es el campo_id de donde se quiere agregar el elemento.
        // @control Es el control target que donde se va a agregar ese elemento.
        crear: function(nombre, tabla_id, control, tipo_control){

            // tabla_id es el campo_id
            nuevo_elemento.tabla_id = tabla_id;
            
            // crear el nuevo elemento
            gestion_tablas.get_tablas(TM.content_exploraciones.detalles.elementoscampos)
            .then(function(tablas) {
                var params = {nombre: nombre, activo: '1', campo_id: tabla_id };
                // XXX TODO no se tiene en cuenta el ambito del campo, por si se ha de indicar servicio_id
                return Endosys.elementos.create(TM.content_exploraciones.detalles.elementoscampos, params, null)
            })
            .done(function(elemento) {
                // completo los atributos del elemnto para que funcione correctamente el generar option
                elemento.nombre = nombre;
                elemento.cantidad = 0;
                elemento.tipo_control = tipo_control;
                var $nodo = input_tipo_multi.generar_option(elemento, tipo_control);
                control.append($nodo);
            });

        }

    }


}();