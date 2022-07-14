/*
	Convirtiendo en un module para usar con RequireJS:
		se ha metido dentro de la llamada a define()

		cualquier referencia desde dentro a la variable global "gestion_usuarios",
		que ya no existe, se ha cambiado por require('js/usuarios').
	
	NOTA: para no tener tantas llamadas a require('js/usuarios'), revisar
	cuantas son a objetos/funciones que podrían ser "privados".
*/

// XXX	de momento el CSSLoader a veces falla (p.e. en el HUCA) hasta que no se resuelva,
// los CSS se cargarán normal. Si no se soluciona, buscar alternativas...
// define(['/lib/CSSLoader-master/dist/css.js!/lib/jquery-ui-multiselect-widget-1.13/jquery.multiselect.css',

/*
	22/2/2015: Se quita (al menos temporalmente) el modulo, volviendo al comportamiento normal anterior.
	Esto es porque se ha de actualizar a JQueryUI-1.11, y esto parece que da problemas con el RequireJS.
*/

var gestion_usuarios = function () {
  //define(['/lib/jquery-ui-multiselect-widget-1.13/jquery.multiselect.js'], function() {

  var datatable_results;
  var datatable_permisos;
  var datatable_permisos_dlg;
  var buscar_btn;
  var array_permisos;
  var comprobar_servicios_id = null;

  return {
    usuario_id: null,
    usuario_activo: null,
    datatable_results: undefined,
    datatable_permisos: undefined,
    arrayPermisos: undefined,
    array_permisos: undefined,
    $dialog_nuevo: undefined,

    _crear_datatable_permisos: function ($el, lista_permisos_user) {
			/*
				crea un datatable con todos los permisos de usuario.
				$el						Es un elemento jQuery en el que se creará el datatable.
				lista_permisos_user		es la lista de permisos asignados a un usuario, para
										marcarlos (devuelto por Endosys.usuarios.show()).
										Puede ser NULL.
				devuelve el objeto DataTable de YUI creado.
			*/
      var permisos = gestion_usuarios.array_permisos.slice();	// duplicar el array de permisos, para marcar los asignados a este usuario
      //	marcar los permisos asignados al usuario
      if (lista_permisos_user) {
        for (var i = 0; i < permisos.length; i++) {
          permisos[i].asignado = false;

          for (var e = 0; e < lista_permisos_user.length; e++) {
            if (lista_permisos_user[e].id == permisos[i].id) {
              permisos[i].asignado = true;
              break;
            }
          }
        }
      }

      //	crear el DataTable
      var datatable = new YAHOO.widget.ScrollingDataTable(
        $el.get(0),
        [{
          key: 'nombre',
          label: _('Permiso'),	// IDIOMAOK
          width: 350,
          resizeable: true,
          sortable: true
        },
        //{key: 'asignado', label: 'Activo', width: 32, formatter:YAHOO.widget.DataTable.formatCheckbox, resizeable: true}
        {
          key: 'asignado',
          label: '<input type="checkbox" class="SelectAll">',
          formatter: 'checkbox'
        }],
        dummyDataSource, {
          initialLoad: true,
          MSG_EMPTY: _('No se ha encontrado ningún permiso'),	// IDIOMAOK
          height: "250px",
          width: "444px"
        }
      );

      datatable.onDataReturnInitializeTable(null, { results: permisos });
      controles.init_YUI_datatable(datatable);

      //evento cuando hacen click en un checkbox de un permiso
      datatable.subscribe('checkboxClickEvent', function (oArgs) {
        var elCheckbox = oArgs.target;
        var newValue = elCheckbox.checked;
        var record = this.getRecord(elCheckbox);
        var column = this.getColumn(elCheckbox);

        record.setData(column.key, newValue);

        // controlamos el estado del checkall
        // miramos si estan todos los permisos el checkall ha de estar activo
        // si se deselecciona alguno y no estan todos los permisos activos el checkall ha de estar desactivado
        if (column.key == 'asignado') {
          var allChecked = true;

          this.forAllRecords(function (r) {
            if (!r.getData('asignado')) {
              allChecked = false;
              return false;
            }
          });

          // $('.SelectAll').prop("checked", allChecked)
          $(column.getThEl()).find(".SelectAll").prop("checked", allChecked);
        }
      });

      //funcion para hacer el check/uncheck de todos los permisos
      YAHOO.widget.DataTable.prototype.forAllRecords = function (fn, scope) {
        //if (!Lang.isFunction(fn)) {return;}
        scope || (scope = this);
        for (var rs = this.getRecordSet(), l = rs.getLength(), i = 0; i < l; i++) {
          if (fn.call(scope, rs.getRecord(i), i) === false) return;
        }
      };

      // evento que controla el checkall
      datatable.on('theadCellClickEvent', function (oArgs) {
        var target = oArgs.target,
          column = this.getColumn(target),
          check = false;

        if (column.key == 'asignado') {
          var checkall = $(oArgs.target).find(".SelectAll");

          if (checkall.is(':checked')) {
            check = true;
          } else {
            check = false;
          }

          // funcion para chequear todos o deschequear segun parametro
          this.forAllRecords(function (r) {
            r.setData('asignado', check);
          });

          this.render();
        }
      });

      // tooltip del dataTable
      gestion_usuarios._tooltip_datatable_permisos(datatable);
      return datatable;
    },

    _tooltip_datatable_permisos: function (datatable) {
      // crea un tooltip para una tabla de permisos y lo configura
      var $table = $(datatable.getTableEl());

      $table.find('.yui-dt-data tr').each(function (index) {
        var description = datatable.getRecord(this).getData('descripcion') || null;

        $(this).attr('title', description);
      });

      $table.tooltip({ show: { delay: 1000 } });
    },

    _checkMedico: function ($form) {
      // XXX	de momento se ha ocultado la opción "Medico"; los usuarios siempre se
      // crean como Médicos, ya que si no el servidor da errores. Asi que esta función
      // no hace nada, ya que por defecto la .zonaMedico está visible.
      return;
    },

    _asignar_perfiles: function ($form, datatable) {
      var option_selected = $form.find('.usuario-perfil option:selected').val();
      var lista_permisos = [];

      if (option_selected == "administrativo") {
        lista_permisos = ["crear_modif_citas", "crear_modif_pacientes"];
      } else if (option_selected == "medico") {
        lista_permisos = ["realizar_exploraciones", "informes_exploraciones_user", "consultar_exploraciones_todas"];
      } else if (option_selected == "supervisor") {
        lista_permisos = ["realizar_exploraciones", "consultar_exploraciones_todas", "modificar_exploraciones_todas", "informes_exploraciones_user", "informes_exploraciones_todas", "crear_elementos", "baja_elementos"];
      } else if (option_selected == "admin") {
        lista_permisos = ["consultar_exploraciones_todas", "crear_elementos", "baja_elementos", "admin_usuarios_restringido", "borrado_logico"];
      }

      //limpiar datatable
      $form.find(".datatable_lista_permisos .yui-dt-bd input").each(function () {
        var oRecord = datatable.getRecord(this);

        if ($(this).prop("class") != "SelectAll") {
          var estado = true;

          //if (lista_permisos.indexOf(oRecord._oData.id) == -1) {
          if ($.inArray(oRecord._oData.id, lista_permisos) == -1) {
            estado = false;   //No exsite el valor en el array por lo tanto hay que deseleccionarlo
          }

          $(this).attr('checked', estado);

          var lineNew = {
            id: oRecord._oData.id,
            nombre: oRecord._oData.nombre,
            asignado: estado,
            descripcion: oRecord._oData.descripcion
          };

          datatable.updateRow(oRecord, lineNew);
        }
      });
    },

    _limpiar_datatable_permisos: function ($form, datatable) {
      //limpiar datatable     //.yui-dt-bd
      $form.find(".datatable_lista_permisos .yui-dt-bd input").each(function () {
        if ($(this).prop("class") != "SelectAll") {
          var oRecord = datatable.getRecord(this);

          $(this).attr('checked', false);

          var lineNew = {
            id: oRecord._oData.id,
            nombre: oRecord._oData.nombre,
            asignado: false,
            descripcion: oRecord._oData.descripcion
          };

          datatable.updateRow(oRecord, lineNew);
        }
      });
    },

    _mostrar_api_key: function ($form) {
      var display_apikey = $form.find(".key-display");
      var text_apikey = display_apikey.find('pre');

      Endosys.usuarios.show(
        TM.content_usuarios.detalles,
        gestion_usuarios.usuario_id,
        {
          id: gestion_usuarios.usuario_id,
          _clave: null
        }
      ).done(function (usuario) {
        if (!!usuario.key) {
          display_apikey.show();
          text_apikey.text(usuario.key);
        } else {
          alert(_("El usuario no tiene ninguna clave generada."));// IDIOMAOK
        }
      });
    },

    _ocultar_api_key: function ($form) {
      var display_apikey = $form.find(".key-display");
      display_apikey.hide();
    },

    _ini_form_usuario: function ($form_usuarios, o) {
      o = o || {};

      // BOTONES
      var guardar_btn = $form_usuarios.find(".guardar_btn");
      var cancelar_btn = $form_usuarios.find(".cancelar_btn");
      var eliminar_btn = $form_usuarios.find(".eliminar_btn");
      var mostrar_apikey = $form_usuarios.find(".mostrar_key_btn");
      var ocultar_apikey = $form_usuarios.find(".ocultar_key_btn");
      var regenerar_apikey = $form_usuarios.find(".regenerar_key_btn");
      var eliminar_apikey = $form_usuarios.find(".eliminar_key_btn");

      // botones opcionales de eliminar, guardar y deshacer cambios (cancelar).
      // Crearlos solo si se ha pasado el evento en el objeto "o"
      o.onEliminar ? eliminar_btn.button().click(function () { o.onEliminar(); }) : eliminar_btn.hide();
      o.onGuardar ? guardar_btn.button().click(function () { o.onGuardar(); }) : guardar_btn.hide();
      o.onCancelar ? cancelar_btn.button().click(function () { o.onCancelar(); }) : cancelar_btn.hide();
      o.onMostrarApiKey ? mostrar_apikey.button().click(function () { o.onMostrarApiKey(); }) : mostrar_apikey.hide();
      o.onOcultarApiKey ? ocultar_apikey.button().click(function () { o.onOcultarApiKey(); }) : ocultar_apikey.hide();
      o.onRegenerarApiKey ? regenerar_apikey.button().click(function () { o.onRegenerarApiKey(); }) : regenerar_apikey.hide();
      o.onEliminarApiKey ? eliminar_apikey.button().click(function () { o.onEliminarApiKey(); }) : eliminar_apikey.hide();

      // multiselect de servicios
      $form_usuarios.find(".usuario-servicio").multiselect({
        header: false,
        minWidth: 320,
        selectedList: 3,
        noneSelectedText: _('Ninguno'), // IDIOMAOK
        selectedText: _('# servicios seleccionados...'),  // IDIOMAOK

        click: function (event, ui) {
          var $options = $form_usuarios.find(".usuario-servicio-agenda option[data-servicio='" + String(ui.value) + "']");

          $options.prop("selected", ui.checked);
          $form_usuarios.find(".usuario-servicio-agenda").multiselect("refresh");
        },

        optgrouptoggle: function (event, ui) {
          for (var i = 0; i < ui.inputs.length; i++) {
            var $options = $form_usuarios.find(".usuario-servicio-agenda option[data-servicio='" + String(ui.inputs[i].value) + "']");
            $options.prop("selected", ui.checked);
          }

          $form_usuarios.find(".usuario-servicio-agenda").multiselect("refresh");
        }
      });

      // multiselect de agendas
      $form_usuarios.find(".usuario-servicio-agenda").multiselect({
        header: false,
        minWidth: 320,
        selectedList: 3,
        classes: 'multiselect-servicio-agenda',
        noneSelectedText: _('Ninguno'), // IDIOMAOK
        selectedText: _('# agendas seleccionadas...'),  // IDIOMAOK

        click: function (event, ui) {
          // Evento que controla que se modifique el multiselect de servicios cuando se modifica el servicio-agenda.
          var hay_seleccionados = false;
          // obtiene el servicio_id que esta almacenado en un atributo del option sobre el que se clickea
          var servicio_id = $form_usuarios.find(".usuario-servicio-agenda option[value='" + ui.value + "']").attr("data-servicio");
          var $option_servicio = $form_usuarios.find(".usuario-servicio option[value='" + servicio_id + "']");

          if (!ui.checked) {
            // Si hay mas de 1 agenda en un servicio y se deselecciona antes de deseleccionar el servicio tiene que verificar que otro option del mismo servicio no este seleccionado
            var $options_agenda = $form_usuarios.find(".usuario-servicio-agenda option[data-servicio='" + servicio_id + "']");

            $options_agenda.each(function () {
              if ($(this).prop("selected") && $(this).val() != ui.value) {
                hay_seleccionados = true;
              }
            });

            if (!hay_seleccionados) {
              $option_servicio.prop("selected", ui.checked);
            }
          } else {
            $option_servicio.prop("selected", ui.checked);
          }

          $form_usuarios.find(".usuario-servicio").multiselect("refresh");
        }
      });
    },

    _actualizar_servicios: function ($form, centros, medico_servicios) {
      /*
        Actualiza el control multiselect de servicios.
        $form		elemento jQuery
        servicios	objeto devuelto por obtener_servicios()
        medico_servicios array de ids de servicios del medico, para seleccionarlos (opcional)
      */
      var $servicios = $form.find(".usuario-servicio");

      for (var i = 0; i < centros.length; i++) {
        var $op_group = $('<optgroup value="' + centros[i].id + '" label="' + centros[i].nombre + '"></optgroup>');

        for (var j = 0; j < centros[i].servicios.length; j++) {
          //var $op = $('<option data-servicio="'+id+'" value="' + centros[i].servicios[j].id + '">' + centros[i].servicios[j].nombre + '</option>');
          var $op = $('<option value="' + centros[i].servicios[j].id + '">' + centros[i].servicios[j].nombre + '</option>');

          //marcar los seleccionados
          if (medico_servicios) {
            if ($.inArray(centros[i].servicios[j].id, medico_servicios) !== -1) {
              $op.attr('selected', '');
            }
          }

          $op_group.append($op);
        }

        $servicios.append($op_group);
      }

      //Guardamos el valor del multiselect cuando haya cargado el mismo, para hacer la comprobación en el momento de guardar los cambios
      comprobar_servicios_id = ($('.usuario-servicio').val() || []).join(",");
      $servicios.multiselect('refresh');
    },

    _actualizar_servicios_filtraje: function (centros) {
      var $servicios_filtraje = $(".filtrar-servicio");

      for (var i = 0; i < centros.length; i++) {
        var $op_group_filtraje = $('<optgroup value="' + centros[i].id + '" label="' + centros[i].nombre + '"></optgroup>');

        for (var j = 0; j < centros[i].servicios.length; j++) {
          //var $op = $('<option data-servicio="'+id+'" value="' + centros[i].servicios[j].id + '">' + centros[i].servicios[j].nombre + '</option>');
          var $op_filtraje = $('<option value="' + centros[i].servicios[j].id + '">' + centros[i].servicios[j].nombre + '</option>');

          $op_group_filtraje.append($op_filtraje);
        }

        $servicios_filtraje.append($op_group_filtraje);
      }

      $servicios_filtraje.multiselect('refresh');
    },

    _actualizar_servicios_agendas: function ($form, agendas, medico_agendas) {
      // Actualiza el control multiselect de servicios y agendas.
      // $form		elemento jQuery
      // agendas     json de agendas
      // medico_agendas array de ids de servicios del medico, para seleccionarlos (opcional)

      // Array de Servicios. Dentro de cada servicio estara el listado de agendas
      var servicios_agendas = [];

      // elemento del multiselect
      var $servicios_agendas = $form.find(".usuario-servicio-agenda");

      // Recorre las agendas disponibles que vienen por REST
      for (var i = 0; i < agendas.length; i++) {
        // Crea el objeto agenda que luego va a ser agregado al servicio.
        var agenda_obj = { id: agendas[i].id, nombre: agendas[i].nombre };

        // Recorre servicios_agendas y si no encuentra el servicio, crea uno nuevo y asi va armando el array de servicios
        var j = 0;
        var servicio_encontrado = false;

        while (j < servicios_agendas.length && servicio_encontrado == false) {
          //si en servicios_agendas ya esta cargado el servicio, sale del while
          if (parseInt(servicios_agendas[j].id, 10) == parseInt(agendas[i].servicio.id, 10)) {
            servicio_encontrado = true;
          } else {
            j++;
          }
        }

        if (servicio_encontrado) { // el servicio ya existia, solo agrega la agenda al serv encontrado.
          servicios_agendas[j].agendas.push(agenda_obj);
        } else { //crea el servicio y agrega la agenda a ese servicio
          var servicio_nuevo = { id: agendas[i].servicio.id, nombre: agendas[i].servicio.nombre, agendas: [] };
          servicios_agendas.push(servicio_nuevo);
          servicios_agendas[servicios_agendas.length - 1].agendas.push(agenda_obj);
        }
      }

      //Crear el contenido del multiselect con los optgroup de los servicios y los option de las agendas
      for (var i = 0; i < servicios_agendas.length; i++) {
        var id = servicios_agendas[i].id;
        var nombre = servicios_agendas[i].nombre;
        var $op_group = $('<optgroup value="' + id + '" label="' + _("Servicio") + ' ' + nombre + '"></optgroup>'); // IDIOMAOK

        for (var j = 0; j < servicios_agendas[i].agendas.length; j++) {
          var id_agenda = servicios_agendas[i].agendas[j].id;
          var nombre_agenda = servicios_agendas[i].agendas[j].nombre;
          var $op = $('<option data-servicio="' + id + '" value="' + id_agenda + '">' + _("Agenda") + ' ' + nombre_agenda + '</option>'); // IDIOMAOK

          // marcar los seleccionados
          if (medico_agendas) {
            if ($.inArray(id_agenda, medico_agendas) !== -1) {
              $op.attr('selected', '');
            }
          }

          // agregar el option al group option
          $op_group.append($op);
        }

        $servicios_agendas.append($op_group);
      }

      $servicios_agendas.multiselect('refresh');
    },

    _get_permisos_asignados: function (datatable) {
      // obtener los permisos asignados. Devuelve un array de ids.
      // datatable	es el datatable de permisos.
      var permisos = [];
      var registros = datatable.getRecordSet();

      for (var i = 0; i < registros.getLength(); i++) {
        var data = registros.getRecord(i)._oData;

        if (data.asignado == true) {
          permisos.push(data.id);
        }
      }

      return permisos;
    },

    _seleccionar_row: function (row) {
      // seleccionar un usuario
      datatable_results.unselectAllRows();
      datatable_results.selectRow(row);
      datatable_results.clearTextSelection();
      // require('js/usuarios')
      gestion_usuarios.usuario_id = datatable_results.getRecord(row).getData("id");

      // mostrar el usuario, a la derecha
      $("#generic_detail .usuario-servicio").multiselect('destroy');
      $("#generic_detail .usuario-servicio-agenda").multiselect('destroy');

      TM.content_usuarios.detalles.load_content("#generic_detail", "content/usuario.html" + ew_version_param()).done(function () {
        var $form_usuarios = $("#generic_detail");

        // require('js/usuarios');
        gestion_usuarios._ini_form_usuario($form_usuarios, {
          onGuardar: function () {
            // obtener los permisos asignados
            var permisos = gestion_usuarios._get_permisos_asignados(datatable_permisos);

            // guardar usuario
            // sacar los params del formulario
            var args = {
              newid: $form_usuarios.find('.usuario-nombre').val(),
            }

            if ($form_usuarios.find('.usuario-passwd').val()) {
              args.password = $form_usuarios.find('.usuario-passwd').val();
            }

            if ($form_usuarios.find('.usuario-ldap')) {
              var check_ldap = $form_usuarios.find('.usuario-ldap');

              if (check_ldap.prop('checked') == true) {
                // si el usuario funciona por ldap, no ha de tener password, como en la
                // tabla users definida por pylons es obligatorio se introduce con un espacio
                args.password = " ";
                args.ldap = "1";
              } else {
                args.ldap = "0";
              }
            }

            if ($form_usuarios.find('.usuario-tipo')) {
              args.tipo = $form_usuarios.find('.usuario-tipo').val();
            }

            if ($form_usuarios.find('.usuario-activo')) {
              if ($form_usuarios.find('.usuario-activo').prop('checked')) {
                args.activo = "1";
              } else {
                args.activo = "0";
              }
            }

            // si es medico...
            if ($form_usuarios.find('.usuario-Medico').prop('checked')) {
              // nombre del medico
              // XXX	de momento no se usa la opción "Medico"; los usuarios siempre se
              // crean como Médicos, ya que si no el servidor da errores. Aqui se fuerza
              // a que se envíe el arg "medico", ya que es el que indica que el usuario es Médico.
              // if ($form_usuarios.find('.usuario-medico_nombre').val())

              args.medico = $form_usuarios.find('.usuario-medico_nombre').val();

              // numero de colegiado del medico
              if ($form_usuarios.find('.usuario-medico_colegiado').val()) {
                args.colegiado = $form_usuarios.find('.usuario-medico_colegiado').val();
              }

              // servicios asignados
              var $servicios = $form_usuarios.find(".usuario-servicio");
              if ($servicios.val()) {
                args.servicios = $servicios.val().join(',')
              } else {
                args.servicios = '';
              }

              var $agendas = $form_usuarios.find(".usuario-servicio-agenda");
              if ($agendas.val()) {
                args.agendas = $agendas.val().join(',');
                // obtiene los servicios seleccionados de acuerdo a las agendas seleccionas
                // args.servicios = gestion_usuarios._get_servicios_seleccionados($form_usuarios);
              } else {
                args.agendas = '';
              }
            }

            // permisos asignados
            if (permisos) {
              args.permisos = permisos.join(',');
            }

            //Guardamos el valor del multiselect servicios
            var comprobar_servicios_guardar = ($('.usuario-servicio').val() || []).join(",");

            Endosys.statusbar.mostrar_mensaje(_('Guardando los datos del usuario...')); // IDIOMAOK
            Endosys.usuarios.update(TM.content_usuarios.detalles, gestion_usuarios.usuario_id, args).done(function () {
              datatable_results.updateRow(
                row,
                {
                  id: args.newid,
                  nombre: args.medico,
                  activo: args.activo === "1" ? true : false,
                  ldap: args.ldap === "1" ? true : false,
                  tipo: args.tipo
                }
              );

              Endosys.statusbar.mostrar_mensaje(_('Ready'));  // IDIOMAOK

              // Si el valor del multiselect servicios es distinto al valor del mismo en el momento de la carga del formulario,
              // al guardar el usuario actualizará la tabla de usuarios según el filtro que haya seleccionado
              if (comprobar_servicios_guardar != comprobar_servicios_id) {
                var servicios = null;
                var servicios_ids = $(".filtrar-servicio").val();
                var params = null;

                if (servicios_ids) { //Si hay algún servicio seleccionado asignaremos la id del/los servicio/s a la variable servicios
                  servicios = servicios_ids.join(",");
                  // console.log(servicios);
                  params = { "servicios": servicios }; //Recogemos la id del/los servicios a modo de diccionario
                }

                Endosys.usuarios.index(TM.content_usuarios, params, { datatable: datatable_results });
              }
            }).done(function () {
              gestion_usuarios.usuario_id = $form_usuarios.find('.usuario-nombre').val();
              $form_usuarios.find('.usuario-passwd').val('');
            });
          },

          onCancelar: function () {
            gestion_usuarios._seleccionar_row(row);
          },

          onEliminar: function () {
            controles.confirm_dialog(
              _('Eliminar usuario'), // IDIOMAOK
              _('¿Está seguro de que desea eliminar este usuario?') // IDIOMAOK
            ).then(function () {
              return Endosys.usuarios["delete"](
                TM.operaciones,
                // require('js/usuarios'),
                gestion_usuarios.usuario_id,
                null,
                { datatable: datatable_results }
              );
            }).done(function () {
              $form_usuarios.html('');
            }).fail(function (jqXHR, textStatus, errorThrown) {
              /*
                si confirm_dialog() se resuelve, este fail() será el del delete(),
                que es el mismo que el de la llamada $.ajax(), y por lo tanto tendrá
                los parametros jqXHR, textStatus, errorThrown.
                Si confirm_dialog() no se resuelve, entonces como no hay una segunda
                funcion en el then() para ese caso, es el fail() del mismo confirm_dialog(), que no tiene parametros.

                textStatus es 'error'
                errorThrown puede ser "FORBIDDEN", etc... segun el tipo de error. Lo mas
                seguro es consultarlo de jqXHR.status
              */
              if (!jqXHR) return; // es del confirm_dialog() asi que salir
              if (jqXHR.status == 403) {
                // forbidden: no se puede porque ya esta en uso, o no se tiene permisos
                Endosys.statusbar.mostrar_mensaje(_('No se puede eliminar el usuario. Probablemente el usuario tenga alguna exploración o cita'), 1); // IDIOMAOK
              } else {
                Endosys.statusbar.mostrar_mensaje(_('Ha ocurrido un error eliminando el usuario'), 1);  // IDIOMAOK
              }
            });
          },

          onMostrarApiKey: function () {
            gestion_usuarios._mostrar_api_key($form_usuarios);
          },

          onOcultarApiKey: function () {
            gestion_usuarios._ocultar_api_key($form_usuarios);
          },

          onEliminarApiKey: function () {
            var respuesta = confirm(_("¿Realmente quiere eliminar la clave para el usuario?"));

            if (!!respuesta) {
              Endosys.usuarios.update(
                TM.content_usuarios.detalles,
                gestion_usuarios.usuario_id,
                {
                  id: gestion_usuarios.usuario_id,
                  medico: gestion_usuarios.usuario_id,
                  _clave: 'delete'
                }
              ).done(function () {
                gestion_usuarios._ocultar_api_key($form_usuarios);
              });
            }
          },

          onRegenerarApiKey: function () {
            var respuesta = confirm(_("¿Realmente quiere generar una nueva clave para el usuario?"));  // IDIOMAOK

            if (!!respuesta) {
              Endosys.usuarios.update(
                TM.content_usuarios.detalles,
                gestion_usuarios.usuario_id,
                {
                  id: gestion_usuarios.usuario_id,
                  medico: gestion_usuarios.usuario_id,
                  _clave: null
                }
              ).done(function () {
                gestion_usuarios._mostrar_api_key($form_usuarios);
              });
            }
          }
        });

        // obtener detalle del usuario
        // Endosys.usuarios.show(TM.content_usuarios.detalles, require('js/usuarios')).done(function (usuario) {
        Endosys.usuarios.show(TM.content_usuarios.detalles, gestion_usuarios.usuario_id).done(function (usuario) {
          // rellenar los controles
          var $content = $("#generic_detail");

          $content.find('.usuario-nombre').prop("value", usuario.id);
          $content.find('.usuario-nombre').attr("readonly", true);

          if (usuario.medico) {
            var nombre_medico = usuario.medico.nombre;
          } else {
            var nombre_medico = '';
          }

          $content.find('.usuario-medico_nombre').prop("value", nombre_medico);

          if (usuario.medico) {
            $content.find('.usuario-medico_colegiado').prop("value", usuario.medico.colegiado);
          }

          if (usuario.ldap == "sí") {
            $content.find('.usuario-ldap').prop("checked", true);
          } else {
            $content.find('.usuario-ldap').prop("checked", false);
          }

          if (usuario.activo == "sí") {
            $content.find('.usuario-activo').prop("checked", true);
          } else {
            $content.find('.usuario-activo').prop("checked", false);
          }

          $content.find('.usuario-tipo').prop("value", usuario.tipo);

          // XXX	de momento no se usa la opción "Medico"; los usuarios siempre se
          // crean como Médicos, ya que si no el servidor da errores. Aqui se fuerza
          // a que sea como sea, el usuario obtenido se trata como médico, y asi se guardará.
          $content.find('.usuario-Medico').prop("checked", true);

          // require('js/usuarios');
          gestion_usuarios._checkMedico($form_usuarios);

          var medico_servicios = [];
          if (usuario.medico) {
            for (var i = 0; i < usuario.medico.servicios.length; i++) {
              medico_servicios.push(usuario.medico.servicios[i].id);
            }
          }

          var medico_agendas = [];
          if (usuario.medico) {
            for (var i = 0; i < usuario.medico.agendas.length; i++) {
              medico_agendas.push(usuario.medico.agendas[i].id)
            }
          }

          if (Endosys.auth.username == "sysadmin" && opciones_config.PERMITIR_API_KEY > 0) {
            $(".apiKey").show();
          }

          Endosys.centros.index(TM.content_usuarios).done(function (centros) {
            gestion_usuarios._actualizar_servicios($form_usuarios, centros, medico_servicios);

            Endosys.agendas.index(TM.content_usuarios).done(function (agendas) {
              gestion_usuarios._actualizar_servicios_agendas($form_usuarios, agendas, medico_agendas);
            });
          });

          // obtener los permisos del usuario
          Endosys.usuarios.show(TM.content_usuarios.detalles, gestion_usuarios.usuario_id).done(function (usuario) {
            // datatable permisos
            var $el = $("#generic_detail .datatable_lista_permisos");
            gestion_usuarios.datatable_permisos = gestion_usuarios._crear_datatable_permisos($el, usuario.permisos);
            datatable_permisos = gestion_usuarios.datatable_permisos;

            $form_usuarios.find(".usuario-perfil").change(function () {
              gestion_usuarios._asignar_perfiles($form_usuarios, datatable_permisos);
            });
          });
        });
      }); // load_content
    },  // _seleccionar_row

    mostrar: function () {
      gestion_usuarios.usuario_id = null;
      TM.content_usuarios.activate();
      TM.content_usuarios.detalles.activate();
      TM.content_usuarios.servicios.activate();
      Endosys.statusbar.mostrar_mensaje(_('Cargando gestión de usuarios...'));  // IDIOMAOK

      // carga de contenido HTML
      TM.content_usuarios.load_content(mainlayout, "content/gestion_usuarios.html" + ew_version_param()).done(function () {
        var servicios_on_open = null;

        // OJO! la documentación de la libreria multiselect es esta: https://ehynds.github.io/jquery-ui-multiselect-widget/#callbacks
        // multiselect de filtrado por servicio
        $(".filtrar-servicio").multiselect({
          header: false,
          minWidth: 320,
          selectedList: 3,
          noneSelectedText: _('Ninguno'), // IDIOMAOK
          selectedText: _('# servicios seleccionados...'),  // IDIOMAOK
          open: function () { //Al abrir el multiselect
            var servicios_ids = $(".filtrar-servicio").val(); //Guardamos el valor del multiselect

            if (servicios_ids) { //Si hay algún servicio seleccionado
              servicios_on_open = servicios_ids.join(","); //Guardamos la id o las id's del servicio o servicios seleccionado/s
            } else {
              servicios_on_open = null;
            }
          },
          close: function () { //Al cerrar el multiselect (hacer click fuera)
            var servicios = null;
            var params = null;
            var servicios_ids = $(".filtrar-servicio").val();
            if (servicios_ids) { //Si hay algún servicio seleccionado asignaremos la id del/los servicio/s a la variable servicios
              servicios = servicios_ids.join(",");
              params = { "servicios": servicios }; //Recogemos la id del/los servicios a modo de diccionario
            }

            if (servicios == servicios_on_open) {// Si son iguales no haremos nada, no será necesario recargar la tabla
              return;
            }

            //params es un diccionario que contendrá las id's de los servicios y que enviaremos a usuarios.py
            Endosys.usuarios.index(TM.content_usuarios, params, { datatable: datatable_results });
          }
        });

        // carga de permisos
        var rest_permisos = Endosys.permisos.index(TM.content_usuarios.detalles).done(function (permisos_cargados) {
          gestion_usuarios.array_permisos = permisos_cargados;
        });

        //carga del multiselect de filtrado por servicio
        rest_permisos.then(function(){
          Endosys.centros.index(TM.content_usuarios.detalles).done(function (centros) {
            gestion_usuarios._actualizar_servicios_filtraje(centros);
          });
        });

        //CREAR LAYOUT
        $('.layout_main_content').layout({
          // west__size: 410,
          west__size: 606,
          spacing_closed: 10,
          slideTrigger_open: "click",
          initClosed: false,
          resizable: false,
          // togglerAlign_open: "top"
        });

        var nuevo_btn = $("#nuevo_btn").button();

        // Esta función se encarga de traducir los 0 y 1 de la columna Tipo a Administrador o Usuario
        // 1 = Administrador
        // 0 = Usuario
        var formatterTipo = function (container, record, column, data) {  // IDIOMAOK
          if (data == '1') {
            container.innerHTML = _('Administrador');
          } else {
            container.innerHTML = _('Usuario');
          }
        };

        // crear la tabla de resultados
        gestion_usuarios.datatable_results = new YAHOO.widget.ScrollingDataTable(
          'datatable_busqueda_result',
          [
            { key: 'id', label: _('Usuarios'), width: 80, resizeable: true, sortable: true }, // IDIOMAOK
            { key: 'nombre', label: _('Nombre'), width: 200, resizable: true, sortable: true }, // IDIOMAOK
            { key: 'activo', label: _('Activo'), formatter: "checkbox", sortable: true }, // IDIOMAOK
            { key: 'ldap', label: _('Ldap'), formatter: "checkbox", sortable: true }, // IDIOMAOK
            { key: 'tipo', label: _('Tipo'), formatter: formatterTipo, sortable: true } // IDIOMAOK
          ],
          dummyDataSource,
          {
            initialLoad: false,
            MSG_EMPTY: _('No se ha encontrado ningún usuario'), // IDIOMAOK
            height: "450px",
            width: "auto"
          }
        );

        datatable_results = gestion_usuarios.datatable_results;
        datatable_results.subscribe("rowMouseoverEvent", datatable_results.onEventHighlightRow);
        datatable_results.subscribe("rowMouseoutEvent", datatable_results.onEventUnhighlightRow);
        controles.init_YUI_datatable(datatable_results);

        // evento click en una fila de la tabla
        datatable_results.subscribe("rowClickEvent", function (oArgs) {
          // comprobar que la fila tiene record asignado (porque la fila con el mensaje 'no hay resultados' no tiene record y daria error)
          if (!datatable_results.getRecord(oArgs.target)) return;
          gestion_usuarios._seleccionar_row(oArgs.target);
          return;
        });

        // boton nuevo
        nuevo_btn.click(function () {
          /*require('js/usuarios')*/gestion_usuarios.mostrar_nuevo();
        });

        // cuando se ha cargado el content, cargar los usuarios (necesita el datatable)
        Endosys.usuarios.index(TM.content_usuarios, null, { datatable: datatable_results });

        // edicion campo activo (checkbox)
        datatable_results.subscribe('checkboxClickEvent', function (oArgs) {
          var elCheckbox = oArgs.target;
          var newValue = elCheckbox.checked;
          var record = this.getRecord(elCheckbox);
          var column = this.getColumn(elCheckbox);
          var recordIndex = this.getRecordIndex(record);
          var usuario_id = record.getData("id");
          var medico = record.getData("nombre");
          var tipo = record.getData("tipo");
          var checkKey = "";

          if(elCheckbox.offsetParent.className.includes("ldap")) {
            checkKey = "ldap";
          } else if(elCheckbox.offsetParent.className.includes("activo")) {
            checkKey = "activo";            
          }

          Endosys.usuarios.update(TM.content_usuarios, usuario_id, {
            'medico': medico,
            // 'activo': newValue ? '1' : '0',
            // 'ldap': newValueLdap ? '1' : '0',
            [checkKey]: newValue ? '1' : '0',   // [] permite key dinamica
            'tipo': tipo
          }).fail(function () {
            elCheckbox.checked = !newValue;
          });
        });
      });
    },  // mostrar

    _dialog_nuevo_ok: function () {
      // crear el paciente con los datos introducidos en el dialog
      var $form = gestion_usuarios.$dialog_nuevo;

      //	obtener los permisos asignados
      var permisos = gestion_usuarios._get_permisos_asignados(datatable_permisos_dlg);

      //  llamada a la creacion del nuevo usuario
      Endosys.statusbar.mostrar_mensaje(_('Creando el usuario...'));//IDIOMAOK

      // sacar los params del formulario
      var args = {
        id: $form.find('.usuario-nombre').val(),
        password: $form.find('.usuario-passwd').val()
      };

      if ($form.find('.usuario-ldap')) {
        if ($form.find('.usuario-ldap').prop('checked') == true) {
          // si el usuario funciona por ldap, no ha de tener password, como en la
          // tabla users definida por pylons es obligatorio se introduce con un espacio
          args.password = " ";
          args.ldap = "1";
        } else {
          args.ldap = "0";
        }
      }

      if ($form.find('.usuario-tipo')) {
        args.tipo = $form.find('.usuario-tipo').val();
      }

      if ($form.find('.usuario-activo')) {
        if ($form.find('.usuario-activo').prop('checked') == true) {
          // si el usuario funciona por ldap, no ha de tener password, como en la
          // tabla users definida por pylons es obligatorio se introduce con un espacio
          args.activo = "1";
        } else {
          args.activo = "0";
        }
      }

      //	si es medico...
      //	XXX	de momento no se usa la opción "Medico"; los usuarios siempre se
      //		crean como Médicos, ya que si no el servidor da errores.
      //			if ($form.find('.usuario-Medico').prop('checked')) {
      //	nombre del medico
      //				if ($form.find('.usuario-medico_nombre').val())
      args.medico = $form.find('.usuario-medico_nombre').val();

      // numero colegiado del medico
      if ($form.find('.usuario-medico_colegiado').val()) {
        args.colegiado = $form.find('.usuario-medico_colegiado').val();
      }

      // servicios asignados
      var $servicios = $form.find(".usuario-servicio");

      if ($servicios.val()) {
        args.servicios = $servicios.val().join(',');
      } else {
        args.servicios = '';
      }

      var $agendas = $form.find(".usuario-servicio-agenda");

      if ($agendas.val()) {
        args.agendas = $agendas.val().join(',');
      } else {
        args.agendas = '';
      }

      // permisos asignados
      if (permisos) {
        args.permisos = permisos.join(',');
      }

      Endosys.usuarios.create(TM.operaciones, args).done(function (usuario) {
        Endosys.statusbar.mostrar_mensaje(_('El usuario se ha creado correctamente'));  // IDIOMAOK
        // añadirlo al datatable y seleccionarlo
        datatable_results.addRow({
          id: usuario.id,
          nombre: args.medico,
          activo: args.activo == '1' ? true : false,
          tipo: args.tipo == '1' ? 'Administrador' : 'Usuario'
        });

        var rs = datatable_results.getRecordSet();
        gestion_usuarios._seleccionar_row(rs.getLength() - 1);
      }).fail(function () {
        Endosys.statusbar.mostrar_mensaje(_('Error al crear el usuario, revise los valores introducidos en los campos'), 1);  // IDIOMAOK
      });
    },

    mostrar_nuevo: function () {
      // Crear el dialog
      var $form = $('<div id="dialog-nuevo-usuario" />').appendTo($('body')).dialog({
        title: _('Nuevo usuario'),  // IDIOMAOK
        width: "580px",
        modal: true,
        autoOpen: false,
        close: function () {
          $(this).remove();
					gestion_usuarios.$dialog_nuevo = null;
        },
        buttons: [{
          text: _('Accept'),
          click: function () {/*IDIOMAOK*/
						gestion_usuarios._dialog_nuevo_ok();
            $(this).dialog('close');
          }
        }, {
          text: _('Cancel'),
          click: function () {/*IDIOMAOK*/
            $(this).dialog('close');
          }
        }]
      });
			/*require('js/usuarios')*/gestion_usuarios.$dialog_nuevo = $form;

      TM.content_usuarios.load_content($form.get(0), "content/usuario.html" + ew_version_param()).then(function () {
				//	inicializar el formulario y cargar los servicios
				gestion_usuarios._ini_form_usuario($form);
				gestion_usuarios._checkMedico($form);
        return Endosys.agendas.index(TM.content_usuarios);
      }).then(function (agendas) {
        gestion_usuarios._actualizar_servicios_agendas($form, agendas);
        return Endosys.centros.index(TM.content_usuarios);
      }).then(function (centros) {
        // poner los servicios en el desplegable de servicio medico
        gestion_usuarios._actualizar_servicios($form, centros);

        // crear el datatable de permisos
        var $el = $form.find(".datatable_lista_permisos");
				/*require('js/usuarios')*/gestion_usuarios.datatable_permisos_dlg = /*require('js/usuarios')*/gestion_usuarios._crear_datatable_permisos($el);
        datatable_permisos_dlg = /*require('js/usuarios')*/gestion_usuarios.datatable_permisos_dlg;

				// limpiar datatable permisos
				gestion_usuarios._limpiar_datatable_permisos($form, datatable_permisos_dlg);
        $form.find(".usuario-perfil").change(function () {
					gestion_usuarios._asignar_perfiles($form, datatable_permisos_dlg);
        });

        $form.dialog('open');
      });
    },

    cerrar: function () {
      $("#generic_detail .usuario-servicio").multiselect('destroy');
    }
  }
}();
