var nuevo_campo_dialog = function() {

    return {

        campo_calculado_estado: function(){
            if (opciones_config["CAMPOS_CALCULADOS"]=="0"){
                $('#nuevocampo-calculado').prop("disabled", true);
                $("#calculado_estado").text(_("Desactivado")).addClass("calculado_desactivado");
            }else{
                $('#nuevocampo-calculado').prop("disabled", false);
                $("#calculado_estado").text(_("Activado")).addClass("calculado_activado");
            }
        },

        titulo_dialog: function(edit){
            if (edit){
                return _("Editar campo");
            }else{
                return _("Nuevo campo");
            }

        },

        mostrar: function(campo_id) {

            var id = campo_id;

            return controles.modal_dialog.mostrar({
                title: nuevo_campo_dialog.titulo_dialog(id!=undefined), // si viene id entonces es un dialog para editar
                width: '500px',
                height: "auto", 
                enterAccept: false,
                
                init: function(accept) {
                    


                    var $dialog = this;
                    return $.get("content/dialog_nuevo_editar_campo.html"+ew_version_param())
                    .done(function(html) {

                        if (id){
                            Endosys.campos.show(TM.content_editorFormularios, id)
                            .done(function(campo){
                                $('#nuevocampo-nombre').val(campo.nombre);
                                $('#nuevocampo-titulo').val(campo.titulo);
                                $('#nuevocampo-tipo').val(campo.tipo);
                                $('#nuevocampo-columnas').val(campo.columnas);
                                $('#nuevocampo-tipo-control').val(campo.tipo_control);
                                $('#nuevocampo-obligatorio').prop("checked", campo.obligatorio);
                                $('#nuevocampo-lectura').prop("checked", campo.solo_lectura);
                                $('#nuevocampo-valorpordefecto').val(campo.valorPorDefecto);
                                $('#nuevocampo-calculado').val(campo.script);
                                $('#nuevocampo-ambito').val(campo.ambito);
                                nuevo_campo_dialog.campo_calculado_estado();
                            });
                        }else{
                            nuevo_campo_dialog.campo_calculado_estado();
                        }

                        $dialog.html(html);
                    });
                    
                }

                ,result: function() {
                    return {
                        nombre:         $('#nuevocampo-nombre').val(),
                        titulo:         $('#nuevocampo-titulo').val(),
                        tipo:           $('#nuevocampo-tipo').val(),
                        columnas:       $('#nuevocampo-columnas').val(),
                        tipo_control:   $('#nuevocampo-tipo-control').val(),
                        obligatorio:    $('#nuevocampo-obligatorio').is(":checked") ? 1 : 0,
                        solo_lectura:   $('#nuevocampo-lectura').is(":checked") ? 1 : 0,
                        calculado:      $('#nuevocampo-calculado').val(),
                        valorPorDefecto:$('#nuevocampo-valorpordefecto').val(),
                        ambito:         $('#nuevocampo-ambito').val()
                    }
                }
                
            });
        }

    }

}();




var nuevo_grupocampos_dialog = function() {

    var content =   '<p><label>Name</label><input id="nuevogrupocampos-nombre" type="text" /></p>' +/*IDIOMA*/
                    '<p><label>Columns</label><input class="peque" id="nuevogrupocampos-columnas" type="text" /></p>';/*IDIOMA*/

    return {

        mostrar: function() {
            return controles.modal_dialog.mostrar({
                title: "New field group", width: "360px",/*IDIOMA*/
                enterAccept: false,
                
                init: function(accept) {
                    this.html(content).addClass('nuevogrupocampos-dialog');
                    $('#nuevocampo-tipo-control').parent().hide();
                }

                ,result: function() {
                    return {
                        nombre:         $('#nuevogrupocampos-nombre').val(),
                        columnas:       $('#nuevogrupocampos-columnas').val()
                    }
                }
            });
        }

    }

}();