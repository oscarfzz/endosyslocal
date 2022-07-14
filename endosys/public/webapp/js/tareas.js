var gestion_tareas = function() {

	var datatable_results;

	return {

		tarea_id: null,
		datatable_results: undefined,

		//BORRAR CUANDO CIERRE PETICION #181
		//funcion test para probar el crear -
		/*param_test: function(){
			var params = {};
			params["recurso"] = "exploraciones";
			params["_busqueda"] = 9;
			params["estado"] = 1;
			params["format"] = "csv";
			params["tipo_tarea"] = "EXP";
			return params;
		},*/


		// Recibe un valor estado y lo transforma 
		// a un string para mostrar en pantalla
		_transformarEstado : function(estado){
			if (estado==1){
				return _("En Curso");//IDIOMAOK
			}else if (estado==2){
				return _("Finalizado");//IDIOMAOK
			}else if (estado==3){
				return _("Error");//IDIOMAOK
			}else{
				return _("Desconocido");//IDIOMAOK
			}  
		},

		// Crea una tarea y lanza el hilo correspondiente
		// al tipo de tarea
		crear_exportar: function(params){
			var crear_tarea = Endosys.tareas.create(TM.tareas, params)
			.done(function() {
				gestion_tareas.informar_tarea_creada();
			}).fail(function(response){
				if (response && response.responseText){
					Endosys.statusbar.mostrar_mensaje(parseError(response.responseText), 1);	
				}
			});
		},

		//obtiene las tareas de ese usuario y llama 
		//a la funcion logica_pantalla para cargar el datatable y armar la pantalla
		mostrar: function(callback_fn, opciones) {

			TM.tareas.activate();
			Endosys.statusbar.mostrar_mensaje(_('Cargando Tareas...'));//IDIOMAOK
			var btn_refrescar = '<span id="refrescar_tareas"><i class="fa fa-refresh"></i><span>';
			set_titulo_pantalla(_("Tareas") + btn_refrescar, $(this).text() );
			var content_html = "content/gestion_tareas.html";
			TM.tareas.load_content(mainlayout, content_html+ew_version_param())
			.done(function() {
				gestion_tareas.logica_pantalla(callback_fn);
			});

		},

		//evento de seleccion de row del datatable
		_seleccionar_row: function(row) {
			datatable_results.unselectAllRows();
			datatable_results.selectRow(row);
			datatable_results.clearTextSelection();
			gestion_tareas.tarea_id = datatable_results.getRecord(row).getData("id");
		},

		// crea y completa la pantalla con el datatable
		logica_pantalla: function(callback_fn){

			// funcion para formatear el estado de la tarea en el datatable.
			var formatterEstado = function(container, record, column, data){
				if (data==1){
					container.innerHTML = '<span class="tarea-en-curso">'+gestion_tareas._transformarEstado(data)+'</span>';
				}else if (data==2){
					container.innerHTML = '<span class="tarea-finalizada">'+gestion_tareas._transformarEstado(data)+'</span>';
				}else if (data==3){
					container.innerHTML = '<span class="tarea-error">'+gestion_tareas._transformarEstado(data)+'</span>';
				}else{
					container.innerHTML = gestion_tareas._transformarEstado(data);
				}  
			}

			var selector1 = ".layout_main_content";

			var fielddef = [
				{key: 'id', label: _('Nº'), width: "auto", resizeable: true, sortable: true,visible: false},//IDIOMAOK
				{key: 'fecha_comienzo', label:_('Inicio'), width: "auto", resizeable: true, sortable: true},//IDIOMAOK
				{key: 'hora_comienzo', label:_('Hora'), width: "auto", resizeable: true, sortable: true},//IDIOMAOK
				{key: 'fecha_fin', label: _('Fin'), width: "auto", resizeable: true, sortable: true},//IDIOMAOK
				{key: 'hora_fin', label:_('Hora'), width: "auto", resizeable: true, sortable: true},//IDIOMAOK
				{key: 'estado', label: _('Estado'), width: "auto", formatter:formatterEstado,resizeable: true, sortable: true},//IDIOMAOK
				{key: 'descripcion', label: _('Descripción'), width: 300, resizeable: true, sortable: true},//IDIOMAOK
			];
			
			// Define un custom row formatter para resaltar los deshabilitados
			var rowFormatter = function(elTr, oRecord) {
				return true;
			}; 
			

			var opciones_datatable = {
				initialLoad:	false,
				MSG_EMPTY:		'<em>' + _('No se ha encontrado ninguna tarea') + '</em>',//IDIOMAOK
				formatRow:		rowFormatter,
				height:			"200px",	//	solo para que tenga el scrollbar, luego el alto es dinámico.
				width:			"100%"
			}
			
			//Mostrar la columna usuario si es sisadmin
			if (Endosys.auth.username.toUpperCase()=="SYSADMIN"){
				fielddef.push({key: 'username', label: _('Usuario'), width: "auto", resizeable: true, sortable: true});//IDIOMAOK
			}


			//	y añadir un botón para descargar y para ver detalles
			fielddef.push({
				key: "button",
				label: _("Opciones"),//IDIOMAOK
				width: 165,
				formatter: function(el, oRecord, oColumn, oData) {
					data = oRecord.getData();
					if (data.descargable==true){
						el.innerHTML = $('<a onclick="unset_prevenir_refresco_manual(1000)" href="'+Endosys.tareas.resource +'/'+data.resultado+'" target="_self" class="ui-button-small">' + _('Descargar') + '</a>').button({icons: {primary: "ui-icon-arrowthickstop-1-s"}, text: true})[0].outerHTML;//IDIOMAOK
					}
					el.innerHTML += $('<button class="boton-dialog-detalle ui-button-small" type="button" data-id="'+data.id+'">' + _('Ver detalle') + '</button>').button({icons: {primary: "ui-icon-plus"}, text: true})[0].outerHTML;//IDIOMAOK
				}
			});
		
			gestion_tareas.datatable_results = new YAHOO.widget.ScrollingDataTable(
					"datatable_busqueda_result", fielddef, dummyDataSource,
					opciones_datatable
			);

			datatable_results = gestion_tareas.datatable_results;
			controles.init_YUI_datatable(datatable_results, {m_inferior:45,layoutPaneResizing: $(selector1).layout().panes.center});

			datatable_results.hideColumn("id");

			//	evento click en una fila de la tabla
			datatable_results.subscribe("rowClickEvent", function(oArgs) {
				if (!datatable_results.getRecord(oArgs.target)) return;	//	comprobar que la fila tiene record asignado (porque la fila con el mensaje 'no hay resultados' no tiene record y daria error)
				gestion_tareas._seleccionar_row(oArgs.target);
			});
				
			datatable_results.subscribe("buttonClickEvent", function(oArgs) {
				if (!datatable_results.getRecord(oArgs.target)) return;
				gestion_tareas._seleccionar_row(oArgs.target);
			});

			var params = {};

			gestion_tareas._load_tareas(TM.tareas, params, datatable_results)

			$("#refrescar_tareas").off();
			$("#refrescar_tareas").on("click", function(){
				gestion_tareas._load_tareas(TM.tareas, params, datatable_results);
			});

		},

		_load_tareas: function(tm, params, datatable_results){

			// busca las tareas y las ingresa en el datatable_results
			Endosys.tareas.index(tm, params, {datatable: datatable_results})
			.done(function(results){

				if (results && results.length == 0) {
					Endosys.statusbar.mostrar_mensaje(_('No se ha encontrado ninguna tarea'));//IDIOMAOK
				} else {

					$("#total").html(results.length);
					Endosys.statusbar.mostrar_mensaje(_('Listo'));//IDIOMAOK
				
					$(".boton-dialog-detalle").on("click", function(){
						gestion_tareas.mostrar_dialog_tarea($(this).attr("data-id"));
					});

				}	

			})
			.fail(function () {
				Endosys.statusbar.mostrar_mensaje(_('Error al cargar las tareas'), 1);//IDIOMAOK
			});

		},

		// mensaje en pantalla que indica que la tarea ha sido creada con exito
		informar_tarea_creada: function(){//IDIOMAOK
			var contenido = "<strong>"+_("La tarea se ha iniciado con éxito.")+"</strong>";//IDIOMAOK 
			contenido += '<br />'+_("Puede consultar el estado desde la sección de Tareas del Sistema");//IDIOMAOK 
			crear_alerta(contenido,3000)
		},

		_obtener_tarea_dialog: function(tm, id, $form){

			Endosys.statusbar.mostrar_mensaje(_('Obteniendo los datos de la tarea...'));//IDIOMAOK 
			return Endosys.tareas.show(tm, id)
			.done(function(tarea) {
				for (var key in tarea) {
					$form.find("#campo-"+key).val(tarea[key]);
				}

				$("#campo-estado").val(function(){
					return gestion_tareas._transformarEstado($(this).val());
				});
				$form.i18n();

				if (tarea.estado==2){
					$("#dialog-tarea-aceptar").hide();
					if (tarea.descargable==1){
						$("#dialog-tarea-aceptar").show();
					}
				}

				Endosys.statusbar.mostrar_mensaje(_('Listo'));//IDIOMAOK 
			})
			.fail(function(){
				Endosys.statusbar.mostrar_mensaje(_('La información que se desea visualizar ya no existe.'),1);/*IDIOMAOK*/
				$("#dialog-show-tarea").dialog('close');
			});

		},


		//obtiene el archivo descargable de la tarea desde el REST
		_descargar_tarea: function(id){
			Endosys.tareas.show(TM.tareas, id).done(function(tarea) {
				unset_prevenir_refresco_manual(1000);
				window.location = Endosys.tareas.resource + "/" + tarea.resultado;
			});			
		},


		// elimina la tarea 
		_eliminar_tarea:function(id){
			Endosys.tareas['delete'](TM.tareas, id)
			.done(function(tarea) {
				Endosys.statusbar.mostrar_mensaje(_('La tarea ha sido eliminada con éxito'));//IDIOMAOK 
			});
		},

		// muestra el dialog con el detalle de la tarea
		// usa _obtener_dialog_tarea para cargar la infomacion de la tarea en el form
		mostrar_dialog_tarea: function(tarea_id){
			controles.modal_dialog.mostrar({
				title: _('Detalle de la tarea'), width: 580, height: 450,//IDIOMAOK
				init: function(accept) {

					//	inicializar el contenido
					var content_form_tarea = $("<div id='content_form_tarea'></div>");
					this.append(content_form_tarea);
					content_form_tarea.load("content/dialog_tarea.html"+ew_version_param(), function(data,textStatus) {

						var form = $('#content_form_tarea form');
						var obtener_dialog = gestion_tareas._obtener_tarea_dialog(TM.tareas,tarea_id,form);
						form.i18n();
					});

				},
				open: function( event, ui ) {
					//console.log("test");
					//$("#dialog-tarea-aceptar").hide();
				},
				buttons: [
					{
						text: _('Descargar'),//IDIOMAOK
						id: "dialog-tarea-aceptar",
						click: function(){
							return gestion_tareas._descargar_tarea(tarea_id);
						},
					}, 
					{
						text: _('Eliminar'),//IDIOMAOK
						click: function(){
							var eliminar_dialog = confirm(_("¿Esta seguro que desea eliminar la tarea?"));
							if (eliminar_dialog) {
								gestion_tareas._eliminar_tarea(tarea_id);
								$(this).dialog('close'); 
								gestion_tareas.mostrar();
							}
						} 
					},{
						text: _('Cancelar'),//IDIOMAOK
						click: function() { $(this).dialog('close'); }
					}
					]
			});
			$("#dialog-tarea-aceptar").hide();

		}

	}
	
}();