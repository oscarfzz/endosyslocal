var gestion_tablas = (function () {
  var datatable_detail;
  return {
    tabla_id: null,
    datatable_detail: undefined,
    tablas: undefined,
    $dialog_mod_predefinido: undefined,
    cargando_tablas: null,

    importar_elementos: function (list, total, tablas, $dialog, importados) {
      if (list.length > 0 && $dialog.dialog('isOpen')) {
        params = list.pop();

        if (tablas[gestion_tablas.tabla_id].campo_id) {
          params.campo_id = tablas[gestion_tablas.tabla_id].campo_id;
        }

        if (tablas[gestion_tablas.tabla_id].ambito == 1) {
          params.servicio_id = Endotools.auth.servicio_activo.id;
        }

        tablas[gestion_tablas.tabla_id].rest.create(TM.operaciones, params, null).done(function () {
          importados++;
        }).always(function () {
          $dialog.find('#progressbar').progressbar({
            value: Math.round(((total - list.length) * 100) / total)
          });

          gestion_tablas.importar_elementos(list, total, tablas, $dialog, importados);
        });
      } else {
        $dialog.find('#progressbar').progressbar({ value: 100 });
        $('#tablas-listado').change();

        if (total - importados === 0) {
          Endotools.statusbar.mostrar_mensaje(_('Se han importado correctamente todos los valores'), 0);
        } else if (importados === 0) {
          Endotools.statusbar.mostrar_mensaje(_('No se ha podido importar ningún elemento'), 1);
        } else {
          Endotools.statusbar.mostrar_mensaje(_('Ocurrió un error al grabar algunos elementos'), 1);
        }

        document.getElementById('dialog-importar-aceptar').disabled = false;
        $dialog.dialog('close');
      }
    },

    mostrar_dialog_mod_importar: function (tabla_id, tablas) {
      return controles.modal_dialog.mostrar({
        title: _('Importar desde fichero'),
        width: '500px',
        height: 'auto',
        enterAccept: false,	// IDIOMAOK

        init: function (accept) {
          var $dialog = this;

          // cargar el contenido
          return $.get('content/importar.html' + ew_version_param()).done(function (htmldata) {
            $dialog.html(htmldata);
            $dialog.find('.fileinput-button').button();
            $dialog.find('#progressbar').progressbar({ value: 0 });
            $dialog.parent().find('.ui-dialog-titlebar-close').hide();

            document.getElementById('file').onchange = function () {
              $('#file-name-text').text(_('Fichero seleccionado: ') + this.files[0].name);
            };
          });
        },

        buttons: [
          {
            text: _('Importar'), // IDIOMAOK
            id: 'dialog-importar-aceptar',
            click: controles.modal_dialog._Aceptar
          },
          {
            text: _('Cancelar'), // IDIOMAOK
            id: 'dialog-importar-cancelar',
            click: function () {
              $(this).dialog('close');
            }
          }
        ],
        check: function () {
          var soloActivos = $('#import-solo-activos');
          var $dialog = this;
          if (tabla_id == undefined) return;
          if (tabla_id.indexOf('_FORMULARIO_') == 0) return;
          if (tabla_id.indexOf('_GRUPOCAMPOS_') == 0) return;
          var file = document.getElementById('file').files[0];
          if (!file) return;
          var reader = new FileReader();
          reader.onload = function (progressEvent) {
            var lines = this.result.split('\r\n');
            var progress = 0;
            var list = new Array();
            for (var line = 0; line < lines.length; line++) {
              var values = lines[line].split('\t');
              var valor = null;
              var activo = '1';
              var codigo = null;
              var orden = null;
              switch (values.length) {
                case 4:
                      orden = values[3];
                case 3:
                      codigo = values[2].split('"').length === 3 ? values[2].split('"')[1] : values[2];
                case 2:
                      activo = values[1] === "0" ? "0" : "1";
                case 1:
                      valor = values[0].split('"').length === 3 ? values[0].split('"')[1] : values[0];
                      break;
                default:
                      continue;
              }

              if (valor == '') continue;

              var params = {
                nombre: valor,
                activo: activo,
                codigo: codigo,
                texto: codigo,
                orden: orden
              };
              if (soloActivos.is(':checked')) {
                if (params.activo == '1') {
                  list.push(params);
                }
              } else {
                list.push(params);
              }
            }
            gestion_tablas.importar_elementos(list, list.length, tablas, $dialog, 0);
          };

          document.getElementById('dialog-importar-aceptar').disabled = true;
          reader.readAsText(file);
        }
      });
    },

    mostrar_dialog_mod_predefinido: function (datos_elemento, row) {
      return controles.modal_dialog.mostrar({
        title: _('Datos del texto predefinido'),
        width: '500px',
        height: 'auto',
        enterAccept: false,	// IDIOMAOK

        init: function (accept) {
          var $dialog = this;

          // cargar el contenido
          return $.get('content/predefinido.html' + ew_version_param()).done(function (htmldata) {
            $dialog.html(htmldata);
            $dialog.find('#desc-elemento').val(datos_elemento.nombre);

            // consultar el texto predefinido
            Endotools.predefinidos.show(TM.content_tablas.detalles, datos_elemento.id).done(function (predefinido) {
              $dialog.find('#texto-predefinido').val(predefinido.texto);
            });
          });
        },

        result: function () {
          var valores_elemento = {
            nombre: this.find('#desc-elemento').val(),
            texto: this.find('#texto-predefinido').val()
          };

          Endotools.predefinidos.update(TM.operaciones, datos_elemento.id, valores_elemento).done(function () {
            var pos = datatable_detail.getRecordIndex(row);

            datatable_detail.updateRow(pos, {
              id: datos_elemento.id,
              nombre: valores_elemento.nombre,
              activo: datos_elemento.activo
            });
          }).fail(function (response) {
            if (response.responseText) {
              data = JSON.parse(response.responseText);

              if (data && data.data) {
                Endotools.statusbar.mostrar_mensaje(data.data, 1);	// IDIOMAOK
              } else {
                Endotools.statusbar.mostrar_mensaje(_('Ocurrió un error al grabar'), 1);	// IDIOMAOK
              }
            } else {
              Endotools.statusbar.mostrar_mensaje(_('Ocurrió un error al grabar'), 1);	// IDIOMAOK
            }
          });

          return this;
        }
      });
    },

    get_tablas: function (tm) {
      // devuelve un promise, y en el done el param es gestion_tablas.tablas
      if (gestion_tablas.cargando_tablas) {
        return gestion_tablas.cargando_tablas;
      }

      //  devuelve las tablas disponibles
      temptablas = {
        /*
        'salas': {
          id: 'salas',
          campo_id: null,
          nombre: _('Salas'),	// IDIOMAOK
          rest: Endotools.salas
        },
        */
        aseguradoras: {
          id: 'aseguradoras',
          campo_id: null,
          nombre: _('Aseguradoras'),	// IDIOMAOK
          rest: Endotools.aseguradoras
        }
      };

      // Campos tipo seleccion y multi:
      //		obtener todos los campos de cada formulario y filtrar solo los de seleccion y multi (en la funcion procesar_formulario)
      //		primero obtiene los formularios y luego los campos de cada uno.
      var procesar_formulario = function (formulario) {
        var grupoCampos = null;

        for (var j = 0; j < formulario.gruposCampos.length; j++) {
          var campos = formulario.gruposCampos[j].campos;
          for (var i = 0; i < campos.length; i++) {
            // añadir una 'tabla' que sea el titulo del formulario al principio
            if (j == 0 && i == 0) {
              grupoCampos = null;
              var titulo_formulario_id = '_FORMULARIO_' + formulario.titulo;

              temptablas[titulo_formulario_id] = {
                id: titulo_formulario_id,
                campo_id: null,
                nombre: formulario.titulo,
                rest: null
              };
            }

            // mostrar solo los tipo seleccion/selec multi
            if (campos[i].tipo != Endotools.campos.TIPO_SELECCION && campos[i].tipo != Endotools.campos.TIPO_MULTI && campos[i].tipo != Endotools.campos.TIPO_MEMO) continue;

            var campo_id = formulario.id + '_' + campos[i].id;
            temptablas[campo_id] = {
              id: campo_id,
              campo_id: campos[i].id,
              nombre: campos[i].titulo,
              ambito: campos[i].ambito,
              codigo_nombre: campos[i].nombre,	// se refiere a la columna nombre de la tabla campos
              nombre_formulario: formulario.titulo,
              rest: Endotools.elementos
            };

            if (campos[i].tipo == Endotools.campos.TIPO_MEMO) {
              temptablas[campo_id].rest = Endotools.predefinidos;
            }
          }
        }
      };

      // jquery promises chain...
      var callback_campos_fail = function () {
        gestion_tablas.tablas = undefined;
      };

      gestion_tablas.cargando_tablas = Endotools.formularios.index(tm, null).then(function (formularios) {
        var chain = $.when();

        $(formularios).each(function (i, _form) {
          // solo los formularios "activos" (que estén asignados a algún tipo de exploración que esté activo)
          if (_form.activo) {
            chain = chain.then(function () {
              return Endotools.formularios.show(tm, _form.id, { _showmode: '1' }).done(procesar_formulario);
            });
          }
        });

        return chain;
      }, callback_campos_fail).then(function () {
        gestion_tablas.tablas = temptablas;

        return gestion_tablas.tablas;
      }, callback_campos_fail);

      return gestion_tablas.cargando_tablas;
    },

    mostrar: function () {
      gestion_tablas.tabla_id = null;
      TM.content_tablas.activate();
      TM.content_tablas.detalles.activate();
      Endotools.statusbar.mostrar_mensaje(_('Cargando gestión de tablas...'));	// IDIOMAOK

      TM.content_tablas.load_content(mainlayout, 'content/gestion_tablas.html' + ew_version_param()).done(function () {
        // CREAR LAYOUT
        $('.layout_main_content').layout({
          west__size: 300,
          spacing_closed: 10,
          slideTrigger_open: 'click',
          initClosed: false,
          esizable: false
          // togglerAlign_open: "top"
        });

        // configurar la gestion de tablas
        // -------------------------------
        // crear la tabla de detalles
        var sortOrden = function (a, b, desc, field) {
          var valor_a = a.getData(field) ? parseInt(a.getData(field), 10) : 0;
          var valor_b = b.getData(field) ? parseInt(b.getData(field), 10) : 0;

          if (valor_a > valor_b) return desc ? -1 : 1;
          if (valor_a < valor_b) return desc ? 1 : -1;

          return 0;
        };

        fielddef = [
          {
            key: 'nombre',
            label: _('Elemento'),	// IDIOMAOK
            width: 450,
            resizeable: false,
            sortable: true
          }, {
            key: 'activo',
            label: _('Activo'),	// IDIOMAOK
            width: 35,
            formatter: 'checkbox',
            resizeable: false,
            sortable: true
          }, {
            key: 'orden',
            label: _('Orden'),
            width: 40,
            resizeable: false,
            sortable: true,
            sortOptions: { sortFunction: sortOrden },
            editor: new YAHOO.widget.TextboxCellEditor({
              validator: YAHOO.widget.DataTable.validateNumber,
              disableBtns: true
            })
          }
        ];

        if (!!opciones_config.HABILITAR_CODIGOS_ELEMENTOS) {
          fielddef.push({
            key: 'codigo',
            label: _('Código'),
            width: 50,
            resizeable: false,
            sortable: true,
            editor: new YAHOO.widget.TextboxCellEditor({
              disableBtns: true
            })
          });
        }

        gestion_tablas.datatable_detail = new YAHOO.widget.ScrollingDataTable('tablas-datatable', fielddef, dummyDataSource, {
          initialLoad: false,
          selectionMode: 'standard',
          MSG_EMPTY: _('No se ha encontrado ningún elemento'),	// IDIOMAOK
          height: '260px'
          // width: "100%"
        });

        datatable_detail = gestion_tablas.datatable_detail;
        controles.init_YUI_datatable(datatable_detail, {
          layoutPaneResizing: $('.layout_main_content').layout().panes.center,
          m_inferior: 65
        });

        datatable_detail.subscribe('cellClickEvent', datatable_detail.onEventShowCellEditor);

        datatable_detail.subscribe('editorSaveEvent', function (oArgs) {
          var oColumn = oArgs.editor.getColumn();
          var column = oColumn.getKey();
          var oRecord = oArgs.editor.getRecord();
          var newValue = oRecord.getData(column);
          var row = this.getRecord(oArgs.target);
          var elemento_id = oRecord.getData('id');
          var valores_elemento = {};

          valores_elemento[column] = newValue;
          Endotools.elementos.update(TM.operaciones, elemento_id, valores_elemento).fail(function (response) {
            Endotools.statusbar.mostrar_mensaje(_('Ocurrió un error al grabar'), 1);	// IDIOMAOK
            $('#tablas-listado').change();
          });
        });

        datatable_detail.subscribe('cellDblclickEvent', function (oArgs) {
          var $listado_tablas = $('#tablas-listado');
          var tabla_id = $listado_tablas.val();

          if (tabla_id == undefined) return;
          if (tabla_id.indexOf('_FORMULARIO_') == 0) return;
          if (tabla_id.indexOf('_GRUPOCAMPOS_') == 0) return;

          gestion_tablas.tabla_id = tabla_id;

          if (gestion_tablas.tablas[tabla_id].rest == Endotools.predefinidos) {
            $('#tablas-modificar-btn').button().click();
          }
        });

        // evento click en una fila de la tabla
        datatable_detail.subscribe('rowClickEvent', datatable_detail.onEventSelectRow);

        // llenar el listado de tablas y activar eventos
        gestion_tablas.get_tablas(TM.content_tablas).done(function (tablas) {
          var $listado_tablas = $('#tablas-listado');
          var $titulo_formulario = null;

          $('#tablas-modificar-btn').hide();

          // llenar el listado de tablas.
          // la variable "tablas" tiene todos los items que se muestran en el
          // listado de tablas en el mismo orden, incluidos los "titulos" de
          // los formularios.
          $listado_tablas.empty();

          for (var n in tablas) {
            var $el;

            if (tablas[n].id.indexOf('_FORMULARIO_') == 0) {
              // si es un titulo de formulario...
              // mejor crear un <optgroup>, que se muestra bien en IE.
              $el = $('<optgroup label="' + tablas[n].nombre + '"></optgroup>');
              $titulo_formulario = $el;
            } else if (tablas[n].id.indexOf('_GRUPOCAMPOS_') == 0) {
              // si es un titulo de grupo de campos...
              $el = $('<option class="titulo-grupocampos" disabled="disabled" value="' + tablas[n].id + '">' + tablas[n].nombre + '</option>');
            } else if (tablas[n].id == 'salas' || tablas[n].id == 'aseguradoras') {
              // si es una tabla predefinida...
              $el = $('<option class="tabla" value="' + tablas[n].id + '">' + tablas[n].nombre + '</option>');
            } else {
              // si es una tabla de un campo tipo selec o multi
              $el = $('<option class="tabla-campo" value="' + tablas[n].id + '">' + tablas[n].nombre + '</option>');
            }

            if ($titulo_formulario && $el != $titulo_formulario) {
              // si está dentro de un titulo de formulario (el <optgroup>) ponerlo dentro.
              $titulo_formulario.append($el);
            } else {
              $listado_tablas.append($el);
            }
          }

          // ordenamos los campos de los formularios
          for (var i = 0; i < $('select#tablas-listado optgroup').length; i++) {
            var $grupo = $('select#tablas-listado optgroup')[i];

            $('option', $grupo).sort(function (a, b) {
              return ($(a).text().toUpperCase() > $(b).text().toUpperCase());
            }).appendTo($grupo);
          }

          // evento clic en la lista de tablas para mostrar los elementos
          $listado_tablas.change(function () {
            var tabla_id = $listado_tablas.val();

            if (tabla_id == undefined) return;
            if (tabla_id.indexOf('_FORMULARIO_') == 0) return;
            if (tabla_id.indexOf('_GRUPOCAMPOS_') == 0) return;

            gestion_tablas.tabla_id = tabla_id;

            // coment ruben
            // var preprocess = null;
            if (gestion_tablas.tablas[tabla_id].rest == Endotools.predefinidos) {
              $('#tablas-titulotipo').html(_('Textos predefinidos del campo') + ' ' + gestion_tablas.tablas[tabla_id].nombre);	// IDIOMAOK
              $('#tablas-modificar-btn').show();

              if (!!opciones_config.HABILITAR_CODIGOS_ELEMENTOS) {
                gestion_tablas.datatable_detail.hideColumn('codigo');
              }

              gestion_tablas.datatable_detail.hideColumn('orden');
            } else if (gestion_tablas.tablas[tabla_id].rest == Endotools.elementos) {
              // entra si es un listado de elementos
              // obtener el ámbito
              var ambito_tag = '';

              if (gestion_tablas.tablas[tabla_id].ambito == 1) {
                // por servicio
                ambito_tag = _('<span title="Ámbito por servicio: Cada servicio dispone de su propio listado de elementos para este campo"> (ámbito por servicio)</span>');
              } else {
                // global
                ambito_tag = _('<span title="Ámbito global: Todos los servicios comparten el mismo listado de elementos para este campo"> (ámbito global)</span>');
              }

              $('#tablas-titulotipo').html(_('Elementos del campo') + ' ' + gestion_tablas.tablas[tabla_id].nombre + '' + ambito_tag);	// IDIOMAOK

              gestion_tablas.datatable_detail.showColumn('orden');

              if (!!opciones_config.HABILITAR_CODIGOS_ELEMENTOS) {
                gestion_tablas.datatable_detail.showColumn('codigo');
                $('#tablas-modificar-btn').hide();
              } else {
                $('#tablas-modificar-btn').hide();
              }
            } else {
              gestion_tablas.datatable_detail.hideColumn('codigo');
              gestion_tablas.datatable_detail.hideColumn('orden');
              $('#tablas-modificar-btn').hide();
            }

            gestion_tablas.get_tablas(TM.content_tablas.detalles).done(function (tablas) {
              $('#tablas-toggle-activos').attr('checked', true).closest('.toggle').removeClass('off');

              gestion_tablas._initTable(gestion_tablas.tablas[tabla_id], true, gestion_tablas.datatable_detail);
            });
          });

          $('#tablas-exportar-btn').button().click(function () {
            //obtiene el campo seleccionado
            var tabla_id = $listado_tablas.val();

            if (tabla_id == undefined) return;
            if (tabla_id.indexOf('_FORMULARIO_') == 0) return;
            if (tabla_id.indexOf('_GRUPOCAMPOS_') == 0) return;

            gestion_tablas.get_tablas(TM.content_tablas.detalles).done(function (tablas) {
              // Textos predefinidos
              var params = null;
              if (tablas[tabla_id].campo_id) {
                params = { campo_id: tablas[tabla_id].campo_id };
              }

              if (gestion_tablas.tablas[tabla_id].rest == Endotools.predefinidos) {
                gestion_tablas.exportar_textos_predefinidos(tablas, tabla_id, params);
              } else {
                // Elementos
                gestion_tablas.exportar_elementos(tablas, tabla_id, params);
              }
            });
          });

          $("#tablas-exportar-btn-todos").button().click(function (){
              var tabla_id = $listado_tablas.val();
              var formulario = tablas[tabla_id].nombre_formulario;
              $('optgroup[label="'+formulario+'"] option').each(function(i){
                var campo_id = parseInt($(this).val().split("_")[1],10);
                var params = {'campo_id': campo_id };
                if (gestion_tablas.tablas[$(this).val()].rest == Endotools.predefinidos) { //Si se trata de un campo con texto predefinido
                  gestion_tablas.exportar_textos_predefinidos(gestion_tablas.tablas, $(this).val(), params);
                }else{
                  gestion_tablas.exportar_elementos(gestion_tablas.tablas, $(this).val(), params);
                }
              });

          });

          $('#tablas-importar-btn').button().click(function () {
            var tabla_id = $listado_tablas.val();

            if (tabla_id == undefined) return;
            if (tabla_id.indexOf('_FORMULARIO_') == 0) return;
            if (tabla_id.indexOf('_GRUPOCAMPOS_') == 0) return;

            gestion_tablas.mostrar_dialog_mod_importar(tabla_id, tablas);
          });

          $('#tablas-exportar-btn-activos').button().click(function () {
            //obtiene el campo seleccionado
            var tabla_id = $listado_tablas.val();

            if (tabla_id == undefined) return;
            if (tabla_id.indexOf('_FORMULARIO_') == 0) return;
            if (tabla_id.indexOf('_GRUPOCAMPOS_') == 0) return;

            gestion_tablas.get_tablas(TM.content_tablas.detalles).done(function (tablas) {
              // Textos predefinidos
              var params = null;

              if (tablas[tabla_id].campo_id) {
                params = { campo_id: tablas[tabla_id].campo_id };
              }

              if (gestion_tablas.tablas[tabla_id].rest == Endotools.predefinidos) {
                gestion_tablas.exportar_textos_predefinidos_activos(tablas, tabla_id, params);
              } else {
                // Elementos
                gestion_tablas.exportar_elementos_activos(tablas, tabla_id, params);
              }
            });
          });

          $('#tablas-nuevo-btn').button().click(function () {
            if (gestion_tablas.tabla_id == null) return;

            var $nuevo_valor_edit = $('#tablas-nuevovalor');
            var valor = $nuevo_valor_edit.val();

            if (valor == '') return;

            var ismemo = gestion_tablas.tablas[gestion_tablas.tabla_id].rest == Endotools.predefinidos;

            gestion_tablas.get_tablas(TM.operaciones).then(function (tablas) {
              var params = { nombre: valor, activo: '1' };

              if (tablas[gestion_tablas.tabla_id].campo_id) {
                params.campo_id = tablas[gestion_tablas.tabla_id].campo_id;
              }

              // Si es un listado de elementos de un campo con ambito "por servicio",
              // al crear el nuevo elemento se asigna el servicio activo.
              // si no hay servicio activo, lanzar error.
              if (!ismemo && tablas[gestion_tablas.tabla_id].ambito == 1) {
                if (Endotools.auth.servicio_activo && Endotools.auth.servicio_activo.id) {
                  params.servicio_id = Endotools.auth.servicio_activo.id;
                } else {
                  throw _("No se puede añadir un nuevo elemento a un campo con ámbito 'por servicio' porque no hay ningún servicio activo.");
                }
              }

              return tablas[gestion_tablas.tabla_id].rest.create(TM.operaciones, params, null);
            }).done(function (elemento) {
              //  añadirlo en el datatable
              var texto = null;
              if (ismemo) texto = '';

              datatable_detail.addRow({
                id: elemento.id,
                nombre: valor,
                activo: true
              }, datatable_detail.getRecordSet().getLength());
            }).fail(function (response) {
              if (response.responseText) {
                data = JSON.parse(response.responseText);

                if (data && data.data) {
                  Endotools.statusbar.mostrar_mensaje(data.data, 1);	// IDIOMAOK
                } else {
                  Endotools.statusbar.mostrar_mensaje(_('Ocurrió un error al grabar'), 1);	// IDIOMAOK
                }
              } else {
                Endotools.statusbar.mostrar_mensaje(_('Ocurrió un error al grabar'), 1);	// IDIOMAOK
              }
            });

            $nuevo_valor_edit.val('');
          });

          $('#tablas-nuevovalor').keydown(function (event) {
            if (event.which == 13) $('#tablas-nuevo-btn').click();
          });

          $('#tablas-eliminar-btn').button().click(function () {
            if (gestion_tablas.tabla_id == null) return;

            //  recorrer las filas seleccionadas y eliminarlas
            var rows = datatable_detail.getSelectedRows();
            var terminados = []; // arrays deferreds que se resuelve cuando se completa el delete (sea fail o done)
            var erroneos = []; //almacena los nombres de los erroneos
            var eliminados = 0; //cuenta los que se eliminaron

            if (rows.length > 0) {
              // si en el $.when.apply s falla 1 promise, entonces ya devuelve fail aunque
              // los demas promises no se hayan ejecutado. Para esperar a que todos terminen
              // se usa esta solucion: http://stackoverflow.com/a/5825233

              //Crea los Deferreds
              for (var n in rows) {
                terminados.push($.Deferred());
              }

              //set la cantidad de terminados
              terminados_restantes = rows.length - 1;

              //Procede a eliminar insertando en un array los DELETE
              gestion_tablas.get_tablas(TM.operaciones).done(function (tablas) {
                var deletes = [];

                for (var n in rows) {
                  var elemento_id = datatable_detail.getRecord(rows[n]).getData('id');

                  deletes.push(
                    tablas[gestion_tablas.tabla_id].rest['delete'](TM.operaciones, elemento_id, null, {
                      datatable: datatable_detail
                    }).done(function () {
                      eliminados += 1; //suma eliminados
                    }).error(function (elemento, textStatus, jqXHR) {
                      data = JSON.parse(elemento.responseText);
                      erroneos.push(data.nombre); //carga los que fallaron
                    }).complete(function () {
                      // Va resolviendo los terminados
                      terminados[terminados_restantes].resolve();
                      terminados_restantes -= 1;
                    })
                  );
                }

                $.when.apply($, deletes);

                $.when.apply($, terminados).then(function () {
                  // este se ejecuta cuando todos los deletes estan resueltos, ya sean en done o en fail
                  // el otro when.apply no puede hacer eso (ver stackoverflow)

                  // Muestra mensaje segun el caso
                  if (eliminados == 0 && erroneos.length != 0) {
                    Endotools.statusbar.mostrar_mensaje(_('Ningún elemento pudo ser borrado.'), 1);	// IDIOMAOK
                  } else if (eliminados != 0 && erroneos.length != 0) {
                    Endotools.statusbar.mostrar_mensaje(_('Ocurrieron errores en la eliminación de algunos elementos.'), 1);	// IDIOMAOK
                  } else if (eliminados != 0 && erroneos.length == 0) {
                    Endotools.statusbar.mostrar_mensaje(_('Los elementos fueron eliminados correctamente.'), 0); //IDIOMAOK
                  }

                  //Muestra los que causaron error de eliminacion
                  if (erroneos.length > 0) {
                    var text_erroneos = _('Los siguientes elementos no se pudieron eliminar porque tienen datos dependientes') + ':<ul>';	// IDIOMAOK

                    for (var i = 0; i < erroneos.length; i++) {
                      text_erroneos += '<li>' + erroneos[i] + '</li>';
                    }

                    text_erroneos += '</ul> ' + _("Destilde la opción 'Activo' si no quiere que se muestren en los formularios."); //IDIOMA OK

                    args = {
                      title: _(
                        'Los siguientes elmentos no se eliminaron'
                      ), //IDIOMAOK
                      buttons: [{
                        text: _('Aceptar'),	// IDIOMAOK
                        click: controles.modal_dialog._Aceptar
                      }],
                      height: 300,
                      init: function (accept) {
                        this.append(text_erroneos);
                      },
                      position: {
                        my: 'top',
                        at: 'top',
                        of: window
                      }
                    };

                    controles.modal_dialog.mostrar(args);
                  }
                });
              });
            }
          });

          $('#tablas-modificar-btn').button().click(function () {
            if (datatable_detail.getSelectedRows().length == 0) return;

            var row = datatable_detail.getSelectedRows()[0];
            var datos_elemento = datatable_detail.getRecord(row).getData();
            var tabla_id = $listado_tablas.val();

            if (tabla_id == undefined) return;
            if (tabla_id.indexOf('_FORMULARIO_') == 0) return;
            if (tabla_id.indexOf('_GRUPOCAMPOS_') == 0) return;
            if (gestion_tablas.tablas[tabla_id].rest == Endotools.predefinidos) {
              gestion_tablas.mostrar_dialog_mod_predefinido(datos_elemento, row);
            }
          });

          $('#tablas-toggle-activos').change(function () {
            var tabla_id = $listado_tablas.val();
            var activeState = $(this).is(':checked');

            gestion_tablas._initTable(gestion_tablas.tablas[tabla_id], activeState, gestion_tablas.datatable_detail);
          });

          //  INTEGRACION_SIHGA, boton actualizar
          if (opciones_config.INTEGRACION_SIHGA) {
            $('#tablas-actualizar-btn').button().click(function () {
              if (gestion_tablas.tabla_id == null) return;

              //  actualizar los elementos de la tabla
              gestion_tablas.get_tablas(TM.operaciones).then(function (tablas) {
                //  solo permitir actualizar los elementos de una tabla que representa un campo
                //  de tipo selec. de un formulario. Para identificarlo se comprueba el rest de la tabla.
                if (tablas[gestion_tablas.tabla_id].rest != Endotools.elementos) return true;
                Endotools.statusbar.mostrar_mensaje(_('Actualizando los elementos de la tabla...'));	// IDIOMAOK

                return Endotools.campos.update(TM.operaciones, tablas[gestion_tablas.tabla_id].campo_id, {
                  _actualizar: '1'
                }).fail(function () {
                  Endotools.statusbar.mostrar_mensaje(_('Ha ocurrido un error actualizando los elementos de la tabla'), 1);	// IDIOMAOK
                });
              }).done(function () {
                $('#tablas-listado').change(); // XXX verificar que funcione!!!!
              });
            });
          } else {
            $('#tablas-actualizar-btn').remove();
          }

          // edicion campo activo (checkbox)
          datatable_detail.subscribe('checkboxClickEvent', function (oArgs) {
            // hold the change for now
            YAHOO.util.Event.preventDefault(oArgs.event);
            // block the user from doing anything
            datatable_detail.disable();
            // Read all we need
            var elCheckbox = oArgs.target;
            var newValue = elCheckbox.checked;
            var record = this.getRecord(elCheckbox);
            var column = this.getColumn(elCheckbox);
            var recordIndex = this.getRecordIndex(record);
            var elemento_id = record.getData('id');

            // modificar
            gestion_tablas.get_tablas(TM.operaciones).then(function (tablas) {
              return tablas[
                gestion_tablas.tabla_id
              ].rest.update(TM.operaciones, elemento_id, {
                activo: newValue ? '1' : '0'
              });
            }).done(function () {
              // If Ok, do the change
              var data = record.getData();

              data[column.key] = newValue;
              datatable_detail.updateRow(recordIndex, data);

              if (!newValue && $('#tablas-toggle-activos').is(':checked')) {
                $('#' + datatable_detail._aSelections[0]).remove();
              }
            }).always(function () {
              datatable_detail.undisable();
            });
          });
        });
        if (Endotools.auth.username != "sysadmin") {
        	$("#tablas-exportar-btn-todos").hide(); //Si el usuario logueado no es Sysadmin, hacemos un hide del boton "exportar todos"
        }
      });
    },

    cerrar: function () {
      if (gestion_tablas.datatable_detail) {
        gestion_tablas.datatable_detail.destroy();
        gestion_tablas.datatable_detail = null;
      }
    },

    _initTable: function (tabla, activeState, datatable_detail) {
      var params = {};

      $('#tablas-toggle-activos').attr('checked', activeState);

      if (tabla.campo_id) {
        params = {
          campo_id: tabla.campo_id
          // 'activo': activeState
        };
      }

      if (tabla.id != 'aseguradoras' && activeState != false) {
        params['activo'] = activeState;
      }else if (tabla.id == 'aseguradoras'){
        if (activeState){
          params['activo'] = 1;
        }
      }

      // Si el campo tiene ámbito por servicio, mostrar solo
      // los elementos del servicio activo.
      if (tabla.rest == Endotools.elementos && tabla.ambito == 1) {
        params.servicio_id = Endotools.auth.servicio_activo.id;
      }

      tabla.rest.index(TM.content_tablas.detalles, params, {
        datatable: datatable_detail
      });
    },

    exportar_elementos: function (tablas, tabla_id, params) {

      tablas[tabla_id].rest.index(TM.content_tablas.detalles, params).done(function (elementos) {
        var csvContent = 'data:text/plain;charset=utf-8,';

        for (var i = 0; i < elementos.length; i++) {
          csvContent += '"' + elementos[i].nombre + '"\t';
          csvContent += elementos[i].activo ? '1\t' : '0\t';
          csvContent += elementos[i].codigo !== null && elementos[i].codigo !== undefined ? '"' + elementos[i].codigo + '"' : '';

          if (gestion_tablas.tablas[tabla_id].rest == Endotools.elementos && elementos[i].orden) {
            csvContent += '\t' + elementos[i].orden;
          }

          csvContent += '\r\n';
        }
        gestion_tablas.crear_csv(tablas, tabla_id, csvContent);
      });
    },

    exportar_textos_predefinidos: function (tablas, tabla_id, params) {
      Endotools.predefinidos.index(TM.content_tablas.detalles, params).done(function (predefinidos) {
        var csvContent = 'data:text/plain;charset=utf-8,';
        for (var i = 0; i < predefinidos.length; i++) {
          csvContent += '"' + predefinidos[i].nombre + '"\t';
          csvContent += predefinidos[i].activo ? '1\t' : '0\t';
          csvContent +=
            predefinidos[i].texto !== null
              ? '"' + predefinidos[i].texto + '"'
              : '';
          csvContent += '\r\n';
        }

        gestion_tablas.crear_csv(tablas, tabla_id, csvContent);
      });
    },

    crear_csv: function (tablas, tabla_id, csvContent) {
      var encodedUri = encodeURI(csvContent);
      var link = document.createElement('a');
      link.setAttribute('href', encodedUri);
      link.setAttribute('download', tablas[tabla_id].codigo_nombre + '.txt');
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    },

    exportar_elementos_activos: function (tablas, tabla_id, params) {
      tablas[tabla_id].rest.index(TM.content_tablas.detalles, params).done(function (elementos) {
        var csvContent = 'data:text/plain;charset=utf-8,';

        for (var i = 0; i < elementos.length; i++) {
          if (elementos[i].activo == '1') {
            csvContent += '"' + elementos[i].nombre + '"\t';
            csvContent += elementos[i].activo ? '1\t' : '0\t';
            csvContent += elementos[i].codigo !== null && elementos[i].codigo !== undefined ? '"' + elementos[i].codigo + '"' : '';

            if (gestion_tablas.tablas[tabla_id].rest == Endotools.elementos && elementos[i].orden) {
              csvContent += '\t' + elementos[i].orden;
            }

            csvContent += '\r\n';
          }
        }

        gestion_tablas.crear_csv(tablas, tabla_id, csvContent);
      });
    },

    exportar_textos_predefinidos_activos: function (tablas, tabla_id, params) {
      Endotools.predefinidos.index(TM.content_tablas.detalles, params).done(function (predefinidos) {
        var csvContent = 'data:text/plain;charset=utf-8,';

        for (var i = 0; i < predefinidos.length; i++) {
          if (predefinidos[i].activo == '1') {
            csvContent += '"' + predefinidos[i].nombre + '"\t';
            csvContent += predefinidos[i].activo ? '1\t' : '0\t';
            csvContent += predefinidos[i].texto !== null ? '"' + predefinidos[i].texto + '"' : '';
            csvContent += '\r\n';
          }
        }

        gestion_tablas.crear_csv(tablas, tabla_id, csvContent);
      });
    }
  };
})();
