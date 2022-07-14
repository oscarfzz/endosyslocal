var gestion_notificaciones = function() {

	var datatable_results;

	return {

		notificacion_id: null,
		datatable_results: undefined,
		cantidad_anterior: undefined,
		intervalo_refresco: 60000, //1 min
		controlador_refresco: undefined,
		datatable_usuarios: undefined,
		dialogs_importante: [],

		init: function(intervalo){
			
			if (intervalo != undefined){
				gestion_notificaciones.intervalo_refresco = intervalo;
			}else{
				//console.log(opciones_config["NOTIFICACIONES.REFRESCO"]);
				gestion_notificaciones.intervalo_refresco = opciones_config["NOTIFICACIONES.REFRESCO"];
			}
			//carga las notificaciones
			gestion_notificaciones.cargar_notificaciones(gestion_notificaciones.intervalo_refresco);

			//Crea un intervalo de refresco de notificaciones
			gestion_notificaciones.setIntervalo();

			//Crea el cuadro de dialogo de notificaciones importantes, pero no lo muestra.
			$('<div id="dialog-importante"></div>').appendTo($('body'));
			$('#dialog-importante').dialog({
				autoOpen: false,
				modal: true,
				title: _("¡Notificación importante!"),//IDIOMAOK
				close: function () {
					gestion_notificaciones.btn_close_dialog();   
				},
				buttons:[{
					text: _("Aceptar"),//IDIOMAOK
					click: function(){
						gestion_notificaciones.btn_close_dialog();
					},
				}]
			});

			//Crea el cuadro de dialogo de para mostrar solo el contenido de las notificaciones.
			$('<div id="dialog-notificacion"></div>').appendTo($('body'));
			$('#dialog-notificacion').dialog({
				autoOpen: false,
				modal: true,
				title: _("Notificación"),//IDIOMAOK
				close: function () {
					   
				},
				buttons:[{
					text: _("Aceptar"),//IDIOMAOK
					click: function(){
						$("#dialog-notificacion").dialog("close");
					},
				}]
			});

		},
		
		crear_eventos: function(){

			//INICIALIZACION de eventos 
			//evento que abre todas las notificaciones
			$("#n-footer").on('click',function(event){
				event.stopPropagation(); //evita la propagacion del click
				gestion_notificaciones.mostrar();
				gestion_notificaciones.cerrar_dialog();
				desactivar_asistente();
				set_atras(null);
				set_continuar(null);
			});

			//Evento de apertura y cerrado de notificaciones
			$(".notificaciones-titulo").on("click",function(event){
				$("#mainheader-notificaciones").toggleClass("abierto");
				event.stopPropagation(); //evita la propagacion del click
			});

			//Evento de apertura y cerrado de notificaciones
			$("#mainheader-notificaciones").on("click",function(event){
				event.stopPropagation(); //evita la propagacion del click	
			});

			//oculta el div de notificaciones si se presiona afuera del div
			$("body").on("click",function(){
				gestion_notificaciones.cerrar_dialog();
			});

		},

		cerrar_dialog: function(){
			$("#mainheader-notificaciones").removeClass("abierto")
		},

		abrir_dialog: function(){
			$("#mainheader-notificaciones").addClass("abierto")
		},

		mostrar_notificaciones: function(){
			gestion_notificaciones.cargar_notificaciones();
			$("#mainheader-notificaciones").show();
		},

		ocultar_notificaciones: function(){

			$("#mainheader-notificaciones").hide();
			gestion_notificaciones.cancelar_intervalo();
			gestion_notificaciones.limpiar_notificaciones();
			//gestion_notificaciones.cargar_notificaciones();
		},

		es_visible: function(){
			if ($("#mainheader-notificaciones").css("display")=="block"){
				return true;
			}else{
				return false;
			}
		},

		// crear un intervalo de refresco que se ejecuta cada XXXX milisegundos
		// configurados en el sistema.
		setIntervalo: function(intervalo){

			if (intervalo != undefined){
				gestion_notificaciones.intervalo_refresco = intervalo ;
			}

			// Si no es un numero lo desactiva por defecto poniendolo a 0
			if (parseInt(gestion_notificaciones.intervalo_refresco, 10) === NaN){
				gestion_notificaciones.intervalo_refresco = 0;
			}

			// Verifica si el numero del intervalo es correcto
			// Si es menor a 10000 (10seg) no se activa
			if (parseInt(gestion_notificaciones.intervalo_refresco,10) >= 10000){
				gestion_notificaciones.controlador_refresco = setInterval(gestion_notificaciones.cargar_notificaciones,gestion_notificaciones.intervalo_refresco);	
			}
			
		},

		//cancela el intervalo seteado por la funcion setIntervalo y guardado en la variable
		// controlador_refresco
		cancelar_intervalo: function(){
			clearInterval(gestion_notificaciones.controlador_refresco);
		},

		// marca como leida una notificacion mediante su ID
		marcar_como_leida: function(id_notificacion){
			if (id_notificacion!=undefined){
				Endosys.notificaciones.update(TM.notificaciones, id_notificacion, {'leida': 1})
				.done(function(data){
					
				}).then(function(){
					gestion_notificaciones.cargar_notificaciones();
				});
			}
		},

		limpiar_notificaciones: function(){

			gestion_notificaciones.cantidad_anterior = undefined;
			$("#cantidad-notificaciones").text("0");

		},

		// Genera y carga la UI del popup de notificaciones que se encuentra abajo del nombre de usuario
		cargar_notificaciones: function(){
			var params ={'leida':0};
			Endosys.notificaciones.index(TM.notificaciones, params)
			.done(function(results){

				$("#cantidad-notificaciones").text(results.length);
				$("#ul-notificaciones").html("");

				var i_notificacion=0;
				if (gestion_notificaciones.cantidad_anterior!=undefined){
					i_notificacion =results.length-  gestion_notificaciones.cantidad_anterior;
				}
				gestion_notificaciones.cantidad_anterior = results.length;		
				
				if (results.length==0){

					li =  '<li>';
					li += '	<div class="n-container-no-notificaciones">';
					li += _('No hay nuevas notificaciones');//IDIOMAOK
					li += '.</div>';
					li += '	</li>';
					$("#ul-notificaciones").append(li);

				}else{
					for (var i = 0; i < results.length; i++) {
		
						li =  '<li>';
						li += '	<div class="n-container">';
						li += '			<div class="n-left">';
						li += '				<div class="n-fecha">'+results[i].fecha+' - ' + results[i].hora + '</div>';
						li += '				<div class="n-contenido">'+results[i].contenido+'</div>';
						li += '			</div>';
						li += '			<div class="n-btn-content"><button data-id="'+results[i].id+'" class="ui-button-small">'+_('Ver')+'</button></div>';//IDIOMAOK
						li += '		<div class="clearfix"></div></div>';
						li += '	</li>';

						$("#ul-notificaciones").append(li);

						if (i < i_notificacion){
							if (!results[i].importante){ // si no es importante crea una alerta
								crear_alerta(li);	
							}
						}

						//si es importante abre un dialog modal
						if (results[i].importante){
							gestion_notificaciones.agregar_notificacion_importante(results[i]);	
						}

					}
				}

				//evento que controla el click del boton de ver detalle de notificaiones
				$(".n-btn-content button").button().click(function(){
					var id = $(this).attr("data-id");
					gestion_notificaciones.abrir_recurso(id);
				});
				
				$("#mainheader-notificaciones").show();
			});
		},

		// abre un recurso deacuerdo a los valores que estan almacenados en
		// meta_informacion de la notificacion 
		// Nota:De acuerdo al tipo de recurso y a los parametros que se envien, 
		// 		se deberian programar distintos comportamientos.
		abrir_recurso:function(id_notificacion){

			//si no esta definida el ID => Salir
			if (id_notificacion==undefined) return false;

			//Obtener detalle de la notificacion
			Endosys.notificaciones.show(TM.notificaciones, id_notificacion)
			.done(function(notificacion){
				
				gestion_notificaciones.marcar_como_leida(notificacion.id);
				gestion_notificaciones.cerrar_dialog();	
				
				if (notificacion.meta_informacion){
					// Realizar un accion personalizada de acuerdo al meta_informacion
					gestion_notificaciones.realizar_accion_personalizada(notificacion);	
				}else{ //no tiene meta informacion, entonces solo abro un dialogo con la informacion
					$("#dialog-notificacion").html(notificacion.contenido).dialog("open");
				}									
			});

		},

		//obtiene las tareas de ese usuario y llama 
		//a la funcion logica_pantalla para cargar el datatable y armar la pantalla
		mostrar: function(callback_fn, opciones) {

			TM.notificaciones.activate();
			Endosys.statusbar.mostrar_mensaje(_('Cargando Notificaciones...'));//IDIOMAOK
			set_titulo_pantalla(_("Notificaciones"), $(this).text());//IDIOMAOK
			var content_html = "content/gestion_notificaciones.html";
			TM.notificaciones.load_content(mainlayout, content_html+ew_version_param())
			.done(function() {
				gestion_notificaciones.logica_pantalla(callback_fn);
			});

		},

		//evento de seleccion de row del datatable
		_seleccionar_row: function(row) {
			datatable_results.unselectAllRows();
			datatable_results.selectRow(row);
			datatable_results.clearTextSelection();
			gestion_notificaciones.notificacion_id = datatable_results.getRecord(row).getData("id");
		},

		// crea y completa la pantalla con el datatable
		logica_pantalla: function(callback_fn){

			// funcion para formatear el estado de la tarea en el datatable.
			/*var formatterEstado = function(container, record, column, data){
				if (data==1){
					container.innerHTML = '<span class="tarea-en-curso">'+gestion_tareas._transformarEstado(data)+'</span>';
				}else if (data==2){
					container.innerHTML = '<span class="tarea-finalizada">'+gestion_tareas._transformarEstado(data)+'</span>';
				}else if (data==3){
					container.innerHTML = '<span class="tarea-error">'+gestion_tareas._transformarEstado(data)+'</span>';
				}else{
					container.innerHTML = gestion_tareas._transformarEstado(data);
				}  
			}*/

			var formatterLeida= function(container ,record,column,data){
				if (data==false){
					container.innerHTML = '<span class="ui-icon ui-icon-mail-closed"></span>';
				}else{
					container.innerHTML = '<span class="ui-icon ui-icon-mail-open"></span>';
				}
			};

			var selector1 = ".layout_main_content";

			var fielddef = [

				{key: 'leida', label:'', width: "auto", formatter:formatterLeida, resizeable: true, sortable: true},/*IDIOMAOK*/
				{key: 'fecha', label:_('Fecha'), width: "auto", resizeable: true, sortable: true},/*IDIOMAOK*/
				{key: 'hora', label:_('Hora'), width: "auto", resizeable: true, sortable: true},/*IDIOMAOK*/
				{key: 'contenido', label: _('Mensaje'), width: "auto", resizeable: true, sortable: true},/*IDIOMAOK*/
			];
			
			// Define un custom row formatter para resaltar los deshabilitados
			var rowFormatter = function(elTr, oRecord) {
				return true;
			}; 
			

			var opciones_datatable = {
				initialLoad:	false,
				MSG_EMPTY:		'<em>' + _('No se ha encontrado ninguna notificación') + '</em>',/*IDIOMAOK*/
				formatRow:		rowFormatter,
				height:			"200px",	//	solo para que tenga el scrollbar, luego el alto es dinámico.
				width:			"100%"
			}
			
			//	y añadir un botón para descargar y para ver detalles
			fielddef.push({
				key: "button",
				label: _("Opciones"),/*IDIOMAOK*/
				width: "100px",
				formatter: function(el, oRecord, oColumn, oData) {
					data = oRecord.getData();
					el.innerHTML = $('<button class="boton-ver ui-button-small" type="button" data-id="'+data.id+'">' + _('Ver') + '</button>').button({icons: {primary: "ui-icon-extlink"}, text: true})[0].outerHTML;/*IDIOMAOK*/
					el.innerHTML += $('<button class="boton-eliminar ui-button-small" type="button" data-id="'+data.id+'">' + _('Eliminar') + '</button>').button({icons: {primary: "ui-icon-trash"}, text: false})[0].outerHTML;/*IDIOMAOK*/
				}
			});
		
			gestion_notificaciones.datatable_results = new YAHOO.widget.ScrollingDataTable(
					"datatable_busqueda_result", fielddef, dummyDataSource,
					opciones_datatable
			);

			datatable_results = gestion_notificaciones.datatable_results;
			controles.init_YUI_datatable(datatable_results, {m_inferior:45,layoutPaneResizing: $(selector1).layout().panes.center});

			//	evento click en una fila de la tabla
			datatable_results.subscribe("rowClickEvent", function(oArgs) {
				if (!datatable_results.getRecord(oArgs.target)) return;	//	comprobar que la fila tiene record asignado (porque la fila con el mensaje 'no hay resultados' no tiene record y daria error)
				gestion_notificaciones._seleccionar_row(oArgs.target);
			});
				
			datatable_results.subscribe("buttonClickEvent", function(oArgs) {
				if (!datatable_results.getRecord(oArgs.target)) return;
				gestion_notificaciones._seleccionar_row(oArgs.target);
			});

			var params = {};

			Endosys.notificaciones.index(TM.notificaciones, params, {datatable: datatable_results})
				.done(function(results){

					if (results && results.length == 0) {
						//no se ha encontrado ningun paciente
						Endosys.statusbar.mostrar_mensaje(_('No se ha encontrado ninguna notificación'));/*IDIOMAOK*/
					} else {

						$("#total").html(results.length);
						Endosys.statusbar.mostrar_mensaje(_('Listo'));/*IDIOMAOK*/
					
						$(".boton-ver").on("click", function(){
							var id_notificacion = $(this).attr("data-id");
							gestion_notificaciones.abrir_recurso(id_notificacion);
							desactivar_asistente();
							set_atras(null);
							set_continuar(null);
						});

						$(".boton-eliminar").on("click", function(){
							var id_notificacion = $(this).attr("data-id");
							gestion_notificaciones._eliminar_notificacion(id_notificacion);
						});

					}	

				})
				.fail(function () {
					Endosys.statusbar.mostrar_mensaje(_('Error al cargar las notificaciones'), 1);/*IDIOMAOK*/
				});

		},

		_eliminar_notificacion:function(id){
			var eliminar_dialog = confirm(_("¿Esta seguro que desea eliminar la notificación?"));
			if (eliminar_dialog) {
				Endosys.notificaciones['delete'](TM.notificaciones, id)
				.done(function(notificacion) {
					Endosys.statusbar.mostrar_mensaje(_('La notificación ha sido eliminada con éxito'));//IDIOMAOK 
					gestion_notificaciones.mostrar();
				});
			}
		},

		// funcion que se usa para abrir un recurso o algun sector del sistema
		realizar_accion_personalizada: function(notificacion){

			//mi significa meta_informacion
			mi = JSON.parse(notificacion.meta_informacion);

			if ("recurso" in mi){ 
				//como existe el parametro recurso entonces la accion es sobre un recurso
				if (mi.recurso == "tareas"){
					if ("id" in mi){
						gestion_tareas.mostrar_dialog_tarea(mi.id);
					}
				}
			}

		},


		/* Enviar Msj Como administrador */
		mostrar_creador_mensaje: function(){

			set_titulo_pantalla(_("Crear Notificación"), $(this).text());//IDIOMAOK
			var content_html = "content/crear_notificacion.html";
			TM.notificaciones.load_content(mainlayout, content_html+ew_version_param())
			.done(function() {
				
				fielddef = [
					{key: 'asignado', label: '<input type="checkbox" class="SelectAll">', width: 35, formatter: 'checkbox', resizeable: false, sortable: false},/*IDIOMAOK*/
					{key: 'nombre', label: _('Usuario'), width: 200, resizeable: false, sortable: true}/*IDIOMAOK*/
				];
					
				gestion_notificaciones.datatable_usuarios = new YAHOO.widget.ScrollingDataTable("usuarios-datatable",
															fielddef,
															dummyDataSource, {
															initialLoad: true,
															MSG_EMPTY: _('No se ha encontrado ningún usuario'),/*IDIOMAOK*/
															height: "260px"
														});

				datatable_usuarios = gestion_notificaciones.datatable_usuarios;

				controles.init_YUI_datatable(datatable_usuarios, {layoutPaneResizing: $('.layout_main_content').layout().panes.center})
				
				//evento cuando hacen click en un checkbox de un permiso
				datatable_usuarios.subscribe('checkboxClickEvent', function(oArgs) {
					var elCheckbox = oArgs.target;
					var newValue = elCheckbox.checked;
					var record = this.getRecord(elCheckbox);
					var column = this.getColumn(elCheckbox);
					record.setData(column.key,newValue);
					
					if (column.key == 'asignado') {
						var allChecked = true;
						this.forAllRecords(function (r) {
							if (!r.getData('asignado')) {
								allChecked = false;
								return false;
							}
						});				
						$(column.getThEl()).find(".SelectAll").prop("checked", allChecked);
					}
				});

				//funcion para hacer el check/uncheck de todos los permisos
				YAHOO.widget.DataTable.prototype.forAllRecords = function (fn,scope) {
					//if (!Lang.isFunction(fn)) {return;}
					scope || (scope = this);
					for (var rs = this.getRecordSet(), l = rs.getLength(), i = 0; i < l; i++) {
						if (fn.call(scope, rs.getRecord(i), i) === false) return;
					}
				};

				//evento que controla el checkall
				datatable_usuarios.on('theadCellClickEvent', function (oArgs) {
					var target = oArgs.target,
						column = this.getColumn(target),
						check = false;


					if (column.key == 'asignado') {
						var checkall = $(oArgs.target).find(".SelectAll");
						
						if(checkall.is(':checked')) {  
							check = true; 
							
						} else {  
							check = false;
						}

						datatable_usuarios.forAllRecords(function (r) {
							r.setData('asignado',check);
						});

						this.render();
					}
				});

				Endosys.medicos.index(TM.notificaciones, null, {datatable: datatable_usuarios});

				$("#mensaje-enviar-btn").button().click(function(){

					var seleccionados = gestion_notificaciones.obtener_seleccionados();

					// Poner los saltos de linea
					var contenido = $("#mensaje-contenido").val().replace(/\n/gi,'<br/>');
					if (contenido.trim() == ""){
						alert(_("No puede enviar un mensaje sin contenido."));//IDIOMAOK
						return false;
					}

					if (seleccionados==""){
						alert(_("Debe seleccionar al menos un usuario"));//IDIOMAOK
						return false;
					}

					// Sanar el contenido
					//var sanitizer = new Sanitize(Sanitize.Config.BASIC);
					contenido = contenido.sanitizeHTML();

					args = {
						contenido: contenido,
						tipo_notificacion: "SYS",
						usuarios_destino: seleccionados,
						importante: true
					};

					var confirm_enviar = confirm(_("¿Está seguro que desea enviar la notificación?"));//IDIOMAOK
					if (confirm_enviar){
						Endosys.notificaciones.create(TM.notificaciones, args );
						Endosys.statusbar.mostrar_mensaje(_('Notificación enviada!'));//IDIOMAOK
						$("#mensaje-contenido").val("")	
					}else{
						Endosys.statusbar.mostrar_mensaje(_('Se canceló el envío.'),1);//IDIOMAOK
					}
					
				});

				$("#mensaje-previsualizar-btn").button().click(function(){

					// Poner los saltos de linea
					var contenido = $("#mensaje-contenido").val().replace(/\n/gi,'<br/>');

					// Sanar el contenido
					//var sanitizer = new Sanitize(Sanitize.Config.BASIC);
					contenido = contenido.sanitizeHTML();

					$('#dialog-importante').html(contenido).dialog('open');
					$('#dialog-importante').dialog({position: {my: "center", at: "center", of: window} });

				});




			});

		},

		obtener_seleccionados: function(){
			var seleccionados = [];
			var records = gestion_notificaciones.datatable_usuarios.getRecordSet().getRecords();
			for (var i = 0; i < records.length; i++) {
				var item = records[i].getData();
				if (item.asignado){
					seleccionados.push(item.id);
				}
			}
			return seleccionados.join(",");
		},
		
		agregar_notificacion_importante: function (notificacion) {

			//comprobacion de los dialogs que ya estan en cola para no repetirlos
			var ya_existe_en_cola = false;
			for (var i = 0; i < gestion_notificaciones.dialogs_importante.length; i++) {
				if ( gestion_notificaciones.dialogs_importante[i].id == notificacion.id ){
					ya_existe_en_cola = true
				}
			};

			if (!ya_existe_en_cola){
				gestion_notificaciones.dialogs_importante.push(notificacion);	
			}
			
			if (!$('#dialog-importante').dialog("isOpen")) {
				gestion_notificaciones.mostrar_notificacion_importante();
			}

		},

		mostrar_notificacion_importante: function () {
			if (gestion_notificaciones.dialogs_importante.length!=0){
				var notificacion = gestion_notificaciones.dialogs_importante[0];
				$('#dialog-importante').html(notificacion.contenido).dialog('open');
				$('#dialog-importante').dialog({position: {my: "center", at: "center", of: window} });
			}
		},

		btn_close_dialog: function(){
			if (gestion_notificaciones.dialogs_importante.length > 0) {
				var notificacion = gestion_notificaciones.dialogs_importante.shift();
				gestion_notificaciones.marcar_como_leida(notificacion.id);
				gestion_notificaciones.mostrar_notificacion_importante();
				if (gestion_notificaciones.dialogs_importante.length == 0){
					$("#dialog-importante").dialog("close");
				}
			}
		}


	}
	
}();