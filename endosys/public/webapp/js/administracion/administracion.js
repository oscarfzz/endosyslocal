/*
TODO: Usar las funciones genéricas para crear TODO la gestión, no solo para prioridades, motivos y workstations
*/

var administracion = function() {

		var dias_semana = null;
		var _initialized = false;
		var info_recursos = null;

		function _init() {
			if (_initialized) return;
			
			dias_semana = [
				{codigo: "LUNES"/*NO TRADUCIR*/,	descr: _('Lunes')},	/*IDIOMAOK*/
				{codigo: "MARTES"/*NO TRADUCIR*/,	descr: _('Martes')},	/*IDIOMAOK*/
				{codigo: "MIERCOLES"/*NO TRADUCIR*/,descr: _('Miércoles')},/*IDIOMAOK*/
				{codigo: "JUEVES"/*NO TRADUCIR*/,	descr: _('Jueves')},	/*IDIOMAOK*/
				{codigo: "VIERNES"/*NO TRADUCIR*/,	descr: _('Viernes')},	/*IDIOMAOK*/
				{codigo: "SABADO"/*NO TRADUCIR*/,	descr: _('Sábado')},	/*IDIOMAOK*/
				{codigo: "DOMINGO"/*NO TRADUCIR*/,	descr: _('Domingo')}	/*IDIOMAOK*/
			];
			
			/* tipo_borrar: Puede ser:
				* null: Dialogo con confirmacion
				* CONFIRMACION: Dialogo con confirmacion
				* CONFIRMACION_MOTIVO: Dialogo con confirmacion y motivo 
			*/

			info_recursos = [
				/*{
					titulo: [_('Centros'), _('Centro')],
					res:	Endosys.centros,
					detalle:	{
						'codigo':	{titulo: _('Código'), tipo: 'TEXTO', required: true},
						'nombre':	{titulo: _('Nombre'), tipo: 'TEXTO', required: true},
						'salas':	{titulo: _('Salas'), tipo: 'CUSTOM'}
					}
				},*/
				{
					titulo: [_('Motivos de cancelación'), _('Motivo de cancelación')],
					res:	Endosys.motivosCancelacion,
					detalle:	{
						'codigo':	{titulo: _('Código'), tipo: 'TEXTO', required: true},
						'nombre':	{titulo: _('Nombre'), tipo: 'TEXTO', required: true}
					}
				},
				{
					titulo: [_('Prioridades'), _('Prioridad')],
					res:	Endosys.prioridades,
					detalle:	{
						'codigo':	{titulo: _('Código'), tipo: 'TEXTO', required: true},
						'nombre':	{titulo: _('Nombre'), tipo: 'TEXTO', required: true},
						'nivel':	{titulo: _('Nivel'), tipo: 'TEXTO', required: true}
					}
				},
				{
					titulo: [_('Workstations'), _('Workstation')],
					res:	Endosys.workstations,
					detalle:	{
						'nombre':	{titulo: _('Nombre'), tipo: 'TEXTO', required: true},
						'ip':		{titulo: _('IP'), tipo: 'TEXTO'/*, readonly: true*/}
					},
					custom_detalle: detalle_workstation,
					custom_guardar: guardar_workstation, 
					tipo_borrar: 'CONFIRMACION_MOTIVO',
				}
			];
			
			_initialized = true;
		}
		
		//	HELPERS PARA AÑADIR "CUALQUIER" RECURSO REST EN ADMINISTRACION
		function anadir_recurso(info) {
			//	inicializa algunos campos de info
			//info.nombre_recurso = info.res.resource.replace('/', '_');	//	No va, solo cambia el primer caracter
			info.nombre_recurso = info.res.resource.replace(/\//g, '_');	//	sacar el nombre del recurso, por ejemplo /rest/workstations --> rest_workstations
//			info.titulo_singular = info.titulo.split("|")[1];
//			info.titulo = info.titulo.split("|")[0];
			if ($.isArray(info.titulo) && info.titulo.length > 1) {
				info.titulo_singular = info.titulo[1];
				info.titulo = info.titulo[0];
			} else {
				info.titulo_singular = info.titulo;
			}
			
			//	se inicia un promise que se resuelve al cargar todos los items del recurso, y se retorna
			var promise = info.res.index(TM.content_administracion);
			//	Crear un nuevo <li> para este recurso en el tree
			var $root = $('<li id="organizacion-' + info.nombre_recurso + '"><a href="#" data-i18n>' + info.titulo + '</a></li>');
			$("#organizacion ul").append($root);
			promise.done(function(items) {
				//	poner los items en el tree
				$root.append( $("<ul></ul>") );
				for (var i = 0; i < items.length; i++) {
					var $item = $('<li id="' + info.nombre_recurso + '_' + items[i].id + '"><a href="#">' + items[i].nombre + '</a></li>');	//	xxx usar siempre "nombre"?
					$item.data("datos_recurso", items[i]);
					$item.data("info_recurso", info);
					$root.find("ul").append($item);
				}
				
				//	y poner el item para crear uno nuevo
				var $item = $('<li id="' + info.nombre_recurso + '_new"><a href="#">[+]</a></li>');
				$item.data("info_recurso", info);
				$root.find("ul").append($item);
			});
//			cargas.push(promise);
			return promise;
		}
		
		function construir_detalle(info, data/*, node_id*/) {
			/*	Sirve tanto para mostrar uno existente como para crear uno nuevo.
				Esto va en función de si se pasa el parametro data.
			*/
			$("#detalle_elemento").html('<form class="pure-form pure-form-stacked"></form>');
			//	mostrar campos con valores
			$("#detalle_elemento>form").html('<fieldset><legend data-i18n>' + info.titulo_singular + '</legend><div class="pure-g"></div></fieldset>');
			for (var campo in info.detalle) {
				var id = campo + '-' + info.nombre_recurso;
				var tipo = info.detalle[campo].tipo;
				//	construir el campo
				if (!tipo || tipo == 'TEXTO') {
					$("#detalle_elemento>form>fieldset>div").append('<div class="pure-u-1-2"><label for="' + id + '" data-i18n>' + info.detalle[campo].titulo + '</label><input id="' + id + '"></input></div>');
				}
				var $input = $("#" + id);
				if (info.detalle[campo].readonly) $input.prop("readonly", true);
				//	asignar el valor
				if (data && data[campo]) $input.val(data[campo]);
			}
			//	custom
			if (info.custom_detalle) {
				info.custom_detalle($("#detalle_elemento>form"), info, data);
			}
			
			//	Botones
			$("#detalle_elemento>form").append(
				'<fieldset><legend></legend>' +
							'<button id="modificar_btn" type="button" value="Modificar" data-i18n>Modificar</button>' +
							'<button id="nuevo_btn" type="button" value="Guardar" data-i18n>Nuevo</button>' +
							'<button id="eliminar_btn" type="button" value="Eliminar" data-i18n>Eliminar</button></fieldset>');

			$("label[for='nombre-_rest_workstations']").text("SALA")
			//	Según si se ha pasado "data" o no, mostrar unos u otros botones
			if (data) {
				$("#nuevo_btn").hide();
			} else {
				$("#modificar_btn").hide();
				$("#eliminar_btn").hide();
			}
			
			var guardar_click = function() {
				//	comprobar campos requeridos, y recoger los valores
				var ok = true;
				var params = {};
				for (var campo in info.detalle) {
					var $input = $("#" + campo + '-' + info.nombre_recurso);
					params[campo] = $input.val();
					if (info.detalle[campo].required) {
						//ok = ok && Boolean(params[campo]);
						ok &= Boolean(params[campo]);
						if (!ok) break;
					}
				}
				if (!ok) alert(_('Debe de completar todos los campos'));/*IDIOMAOK*/

				//	custom
				if (info.custom_guardar) {
					info.custom_guardar(params, info, data);
				}
				
				//	en funcion de si habia parametro "data" decidir si es un update o create
				var guardando = data ? info.res.update(TM.content_administracion, data.id, params) : info.res.create(TM.content_administracion, params);

				//	cuando se haya guardado, seleccionar el item (XXX esto no va)
				guardando.done(function(created_item) {
					administracion.mostrar(function() {
						//$("#organizacion").jstree("select_node", "#" + node_id);
						$("#organizacion").jstree( "select_node",  "#" + info.nombre_recurso + (created_item ? created_item.id : data.id) );
					});
				}).fail(function(data){

					try {
					  	json_error = JSON.parse(data.responseText);
						Endosys.statusbar.mostrar_mensaje(json_error.data, 1);
					} catch (e) {
						// no puede parsearlo, da error. se muestra un mensaje generico de error
						Endosys.statusbar.mostrar_mensaje(_("Ocurrio un error"), 1);/*IDIOMAOK*/
					}
				
				});
			}
			
			//		Modificar
			$("#modificar_btn").button().click(guardar_click);

			//		Crear nuevo
			$("#nuevo_btn").button().click(guardar_click);
			
			//		Eliminar
			$("#eliminar_btn").button().click(function() {
				controles.confirm_dialog(_('Borrar'), _('¿Está seguro de que desea borrar?'),/*IDIOMAOK*/
					function() {
						if (info.tipo_borrar == "CONFIRMACION_MOTIVO"){	
							controles.input_dialog.mostrar(_('Motivo'), _('Ingrese el motivo por el cual desea borrar:'), '')//IDIOMAOK
							.then(function(motivo) {
								if (motivo!=""){
									borrar(info, data, motivo);
								}else{
									Endosys.statusbar.mostrar_mensaje(_("Debe completar el motivo"), 1);//IDIOMAOK
								}
							});
						}else{
							return borrar(info, data);
						}
					}
				);	
			});					
		}

		function borrar(info, data, borrado_motivo){
			// agrega motivo si se envia.
			motivo = {};
			if (borrado_motivo!=undefined){
				motivo = {'borrado_motivo': borrado_motivo};
			}

			info.res['delete'](TM.content_administracion, data.id, motivo)
			.done(function() {
				administracion.mostrar();	
			})
			.fail(function(data){
				if (data.responseText){
					error = parseError(data.responseText);
					Endosys.statusbar.mostrar_mensaje(error, 1);
				}
			});	
			
		}

		function detalle_workstation($form, info, data) {
			//multiselect de servicios
			$form.append('<fieldset><legend data-i18n>Servicios</legend><div class="pure-g"><div class="pure-u-1-2"><select id="workstation-servicios" multiple=""></select></div></div></fieldset>');
			$("#workstation-servicios").multiselect({
				header: false,
				minWidth: 320,
				selectedList: 3,
				//classes: 'multiselect-servicio-agenda',
				noneSelectedText: _('Ninguno'),/*IDIOMAOK*/
				selectedText: _('# servicios seleccionados...'),/*IDIOMAOK*/
				click: function(event, ui) {
					/*
					//Evento que controla que se modifique el multiselect de servicios cuando
					// se modifica el servicio-agenda.
					var hay_seleccionados = false;
					//obtiene el servicio_id que esta almacenado en un atributo del option sobre el que se clickea
					var servicio_id = $form_usuarios.find(".usuario-servicio-agenda option[value='"+ui.value+"']").attr("data-servicio");
					var $option_servicio = $form_usuarios.find(".usuario-servicio option[value='"+servicio_id+"']");
				 	
					if (!ui.checked) {

						//Si hay mas de 1 agenda en un servicio y se deselecciona
						//antes de deseleccionar el servicio tiene que verificar que
						//otro option del mismo servicio no este seleccionado
						var $options_agenda = $form_usuarios.find(".usuario-servicio-agenda option[data-servicio='"+servicio_id+"']");
				 		$options_agenda.each(function(){

				 			if ($(this).prop("selected") && $(this).val()!=ui.value){
				 				hay_seleccionados = true;
				 			}
				 			
				 		});


					 	if (!hay_seleccionados){
					 		$option_servicio.prop("selected",ui.checked);	
				 		}
					}else{
						$option_servicio.prop("selected",ui.checked);	
					}

				 	$form_usuarios.find(".usuario-servicio").multiselect("refresh");	 	
					*/
     			},
			});
			
			//	se usa el rest de centros para obtener los servicios agrupados por centros
			$.when(
				Endosys.centros.index(TM.content_administracion),
				data ? Endosys.workstations.show(TM.content_administracion, data.id) : [{servicios: []}]
			)
			.then(function(args1, args2) {
				var centros = args1[0];
				var workstation = args2[0];
						
				cargar_multiselect_servicios($("#workstation-servicios"), centros, workstation);

			});
			
		}
		
		function guardar_workstation(params, info, data) {
			var v = $('#workstation-servicios').val();
			if (v) v = $('#workstation-servicios').val().join(",");
			params["servicios"] = v;
		}
		
		/////////////////////////////////////////////////////////////////

		return {
			mostrar: function() {
				/*
				Lógica implementada para centros - servicios - agendas:
				
					- cargar simultaneamente:
						- el html base (load_content)
						- la lista de centros
						
					- cuando se han cargado el html base y los centros:
						- construir el html de los centros
						- y cargar la lista de servicios de cada centro

					- cuando se han cargado los servicios:
						- construir el html de los servicios
						- y cargar la lista de agendas de cada servicio

					- cuando se han cargado las agendas:
						- construir el html de las agendas
						- y crear ya el jstree

				*/
				_init();
				
				TM.content_administracion.activate();
				TM.content_administracion.arbol.activate();
				TM.content_administracion.detalles.activate();

				Endosys.statusbar.mostrar_mensaje(_('Cargando administración de endosys...'));/*IDIOMAOK*/

				//	$.when()	ejecuta varias promises y cuando todas se han cumplido, continua.
				//	.then()		es la continuación de un promise cumplido, además de permitir encadenar una siguiente promise.
				//	.done()		es la continuación de un promise cumplido, pero ya no permite encadenar otra promise.

				cargando_contenido = TM.content_administracion.load_content(mainlayout, "content/administracion.html"+ew_version_param());

				cargando_contenido.done(function(content_cargado) {
				
					//CREAR LAYOUT
					$('.layout_main_content').layout({
							west__size: 300
						,	spacing_closed:			10			
						,	slideTrigger_open:		"click" 	
						,	initClosed:				false
						,	resizable:	false
						//,	togglerAlign_open: "top"
					});
				
				
					$("#organizacion").hide();
				
					var cargando_organizacion = Endosys.centros.index(TM.content_administracion)
					
					.then(function(centros_cargados) {
						//	cargar la lista de servicios de cada centro				
						
						$("#centros").append( $("<ul></ul>") );	//	esto ya podria estar estático en administracion.html...
						
						//	por cada centro construir el html y obtener los servicios
						var promises = [];
						for (var i = 0; i < centros_cargados.length; i++) {
							var $centro = $('<li id="centro_' + centros_cargados[i].id + '"><a href="#">' + centros_cargados[i].nombre + '</a></li>');
							$centro.data("datos_centro", centros_cargados[i]);
							$("#centros").find("ul").append($centro);
							
							
							(function() {
								//	obtener los servicios
								var centro = centros_cargados[i];
								promises.push(
									Endosys.servicios.index(	TM.content_administracion, { centro_id: centro.id }, { fail404: false} )
									.then(function(servicios) {									
										return [servicios, centro];
									})

								);							
							})();
							

						}
						var $nuevo_centro = $('<li id="centro_new"><a href="#">[...]</a></li>');
						$("#centros").find("ul").append($nuevo_centro);						
						//	Como se espera a mas de una promise para continuar, se usa .when() para esperarlas a todas.
						//	Al ser un número indeterminado, se tiene que usar un "truco" para pasar un array como si fuera
						//	una lista de parámetros, usando .apply()
						return $.when.apply($, promises);
					})
					
					.then(function( datos_servicio ) {
						//	cargar la lista de agendas de cada servicio (de todos los centros)
						//	iterar los resultados de carga de servicios de cada uno de los centros
						var promises = [];
						
						for (var i = 0; i < arguments.length; i++) {
							var respuesta = arguments[i];
							var servicios_cargados = respuesta[0];
							var centro = respuesta[1];
							var $ul = $("<ul></ul>").appendTo( $("#centro_" + centro.id) );
							for (var j = 0; j < servicios_cargados.length; j++) {
								//	construir html del servicio
								var $servicio = $('<li id="servicio_' + servicios_cargados[j].id + '"><a href="#">' + servicios_cargados[j].nombre + '</a></li>');
								$servicio.data("datos_servicio", servicios_cargados[j]);
								$ul.append($servicio);
							
								//	obtener las agendas
								var _temporal = function() {
									var servicio = servicios_cargados[j];
									
									promises.push(
										Endosys.agendas.index(TM.content_administracion,{servicio_id: servicios_cargados[j].id})
										.then(function(agendas_cargadas) {
											agendas_cargadas.servicio_id = servicio.id;
											return agendas_cargadas;
										})
									);
								
								}();
								
							}
							var $nuevo_servicio = $('<li id="servicio_new"><a href="#">[...]</a></li>');
							//$nuevo_servicio.data("datos_centro", centros_cargados[i]);
							$ul.append($nuevo_servicio);
						}
						return $.when.apply($, promises);
						
					})
					
					.done(function() {	//	(XXX también se podria usar un .then() aunque no se sigan encadenando promises)
						//	iterar los resultados de carga de agendas de cada uno de los servicios de cada centro
						for (var i = 0; i < arguments.length; i++) {
							var respuesta = arguments[i];
							var agendas_cargadas = respuesta;
							var $ul = $("<ul></ul>").appendTo( $("#servicio_" + respuesta.servicio_id) );
							if(agendas_cargadas){ // es posible que no tenga agendas
								for (var j = 0; j < agendas_cargadas.length; j++) {
									
									var $agenda = $('<li id="agenda_' + agendas_cargadas[j].id + '"><a href="#">' + agendas_cargadas[j].nombre + '</a></li>');
									$agenda.data("datos_agenda", agendas_cargadas[j]);
									$ul.append($agenda);
									
								}
							}
							var $nueva_agenda = $('<li id="agenda_new"><a href="#">[...]</a></li>');							
							$ul.append($nueva_agenda);
							
						}		
					});

					var cargas = [cargando_organizacion];
					
					for (var i = 0; i<info_recursos.length; i++) {
						cargas.push( anadir_recurso(info_recursos[i]) );
					}

					return $.when.apply($, cargas)
					
					.done(function() {
						// cargar prioridades en el arbol
						//	crear el jstree
						$("#organizacion").css("text-align", "left");
						$("#organizacion").jstree({
							"themes": {
								 "theme":	"apple",
								 "dots":	true,
								 "icons":	false
							}
						})
						
						.bind("loaded.jstree", function (event, data) {							
							$(this).jstree("open_all");
						})   
						
						.bind("select_node.jstree", function (event, data) {
							// data.rslt.obj is the jquery extended node that was clicked
							var datos = data.rslt.obj.data();
							var id = data.rslt.obj.attr("id");
							if (id.indexOf("centro_") != -1) {
								if (id.indexOf("centro_new") != -1) {
									//crear un nuevo nodo centro
									administracion.construir_detalle_centros();
								} else {
									//modificar un nodo
									administracion.construir_detalle_centros(datos, id);
								}
							} else if (id.indexOf("servicio_") != -1) {
								var datos_centro = data.inst._get_parent(data.rslt.obj).data('datos_centro');
								if(id.indexOf("servicio_new") != -1) {
									//crear nuevo nodo servicio
									administracion.construir_detalle_servicios( null ,datos_centro);
								} else {
									//modificar servicio							
									administracion.construir_detalle_servicios(datos,datos_centro,id);
								}

							} else if (id.indexOf("agenda_") != -1) {
								var datos_servicio = data.inst._get_parent(data.rslt.obj).data('datos_servicio');
								
								if (id.indexOf("agenda_new") != -1) {
									//crear nuevo nodo agenda
									administracion.construir_detalle_agendas( datos_servicio);
								} else {
									//modificar agenda
									administracion.construir_detalle_agendas( datos_servicio, datos.datos_agenda,id);
								}
							}
							
							//	CONTROLAR CLICK EN UN NODO USANDO LAS FUNCIONES HELPERS
							else {
								var info_recurso = data.rslt.obj.data('info_recurso');
								if (info_recurso) {
									var datos_recurso = data.rslt.obj.data('datos_recurso');
									construir_detalle(info_recurso, datos_recurso);
								}
							}
							
						});
						
						//fin crear jstree
						$('#organizacion').show();
						Endosys.statusbar.mostrar_mensaje(_('Ready'));/*IDIOMAOK*/
					});
				
				});

			},
			

			
			
			construir_detalle_centros: function (datos,id_nodo){
				
				var cargando_contenido_centro = TM.content_administracion.load_content( $("#detalle_elemento"), "content/centro.html");

				cargando_contenido_centro.done(function(content_cargado) {
					
					if(datos){
						$("#detalle_elemento").find("#codigo-centro").val(datos.datos_centro.codigo);
						$("#detalle_elemento").find("#nombre-centro").val(datos.datos_centro.nombre);
					}
					$( "#modificar_btn" )
					.button()
					.click(function( event ) {
						var params_centro = {};
						var iscorrect =  true;
						if ( !$("#detalle_elemento").find("#codigo-centro").val() || !$("#detalle_elemento").find("#nombre-centro").val())
							iscorrect = false;
						
						if (iscorrect){
						
							params_centro.codigo = $("#detalle_elemento").find("#codigo-centro").val();					
							params_centro.nombre = $("#detalle_elemento").find("#nombre-centro").val();
							
							var mofificando_centro = Endosys.centros.update(TM.content_administracion, datos.datos_centro.id, params_centro);
							mofificando_centro.done(function() {
								//lo ideal seria actualizar el objeto con datos que devuelve el update, aunque siempre serán los mismos
								administracion.mostrar(function() {									
									$("#organizacion").jstree("select_node", "#"+id_nodo);
									
								});
							})
							
						}else{
							alert(_('Debe de completar todos los campos del centro'));/*IDIOMAOK*/
						}
							
					});
					$( "#nuevo_btn" )
					.button()
					.click(function( event ) {
						var params_centro = {};
						var iscorrect =  true;
						if ( !$("#detalle_elemento").find("#codigo-centro").val() || !$("#detalle_elemento").find("#nombre-centro").val())
							iscorrect = false;
						
						if (iscorrect){
						
							params_centro.codigo = $("#detalle_elemento").find("#codigo-centro").val();					
							params_centro.nombre = $("#detalle_elemento").find("#nombre-centro").val();
							
							
							var crear_centro = Endosys.centros.create(TM.content_administracion, params_centro);
							crear_centro.done(function(centro) {

								administracion.mostrar(function() {									
									$("#organizacion").jstree("select_node", "#centro_"+centro.id);
									
								});
							})
							
						}else{
							alert(_('Debe de completar todos los campos del centro'));/*IDIOMAOK*/
						}
							
					});
					$( "#eliminar_btn" )
					.button()
					.click(function( event ) {
						
							
						var eliminando_centro = Endosys.centros['delete'](TM.content_administracion, datos.datos_centro.id);
						eliminando_centro.done(function() {

							administracion.mostrar();	
						})
						eliminando_centro.fail(function() {
							alert(_('Error al eliminar el centro'));/*IDIOMAOK*/
						})												

					});					
					
			
					if(datos){
						$( "#nuevo_btn" ).hide();					
					}else{
						$("#zona_salas").hide();
						$( "#modificar_btn" ).hide();
						$( "#eliminar_btn" ).hide();							
					}
					
					if(datos) {					 
					
						var button_mas = $('#nueva_sala');
						
						button_mas.button({
							icons: {
								primary: "ui-icon-plusthick"
							},
							text: false
						});     
						
						button_mas.click(function( event ) {
							//crear_elemento(campo,true);
							dialogo_sala.crear_dialogo_sala(datos.datos_centro.id);
						});

						var cargando_salas = Endosys.salas.index(TM.content_administracion, {centro_id: datos.datos_centro.id});
						
						cargando_salas.done(function(salas_cargadas) {
								
								var datos_salas = [];
								for (var j = 0; j < salas_cargadas.length; j++) {
									var salas = [ salas_cargadas[j].id , salas_cargadas[j].nombre];
									datos_salas.push(salas);

								}

							//DATATABLE

								$('#tabla_salas').dataTable({								
									"aaData" : datos_salas,
									"bJQueryUI": true,
									"bFilter": false,
									"bPaginate": false,
									"bSort": true,
									"bLengthChange": false,
									"bInfo": false
									//"sPaginationType": "full_numbers"
									//"bSortClasses": false
									//"iDisplayLength": 3,
									//"aaSorting": []
								});
								
								$('#tabla_salas').dataTable().$('tr').click(function (){
									administracion.click_salas(datos.datos_centro.id, this) ;
								});
								$('#tabla_salas').dataTable().$('tr').hover(function() {
									$(this).addClass( 'highlighted' );
								}, function() {
									$(this).removeClass('highlighted');
								});
																
						});
					}

				
				});

			},
			
			click_salas: function (centro_id,registro) {
								var data = $('#tabla_salas').dataTable().fnGetData( registro );
								var aPos = $('#tabla_salas').dataTable().fnGetPosition( registro );
								dialogo_sala.crear_dialogo_sala(centro_id,data[0],data[1],aPos);								
								// ... do something with the array / object of data for the row
			},
			
			pintar_asignar_medicos_salas: function (datos_centro, arg_detalle_servicio) {
					
						var cargando_salas = Endosys.salas.index(TM.content_administracion, {centro_id: datos_centro.id});
																				
						cargando_salas.done( function(salas_cargadas) {

								$("#detalle_elemento").find("#select_salas").multiselect({
									header: false,
									minWidth: 225,
									selectedList: 3,
									noneSelectedText: _('Salas disponibles'),/*IDIOMAOK*/
									//multiple: false,
									selectedText: _('# salas seleccionados...')/*IDIOMAOK*/
								});
								
								var $salas = $("#detalle_elemento").find("#select_salas");
							
								
								for (var j = 0; j < salas_cargadas.length; j++) {
									var id = salas_cargadas[j].id;
									var nombre = salas_cargadas[j].nombre;
									var existe = false;
									if(arg_detalle_servicio){
										for(var e = 0; e < arg_detalle_servicio.salas.length; e++){
											if (arg_detalle_servicio.salas[e].id == id){
												existe = true;
											}
										
										}
									}	
									var op = $('<option value="' + id + '">' + nombre + '</option>');
									if (existe){
										op.attr('selected', '');
									}
									$salas.append(op);
									
									//	construir html de la agenda
							
								}

								$salas.multiselect('refresh');
																
							
							

						});

						var cargando_medicos = Endosys.medicos.index(TM.content_administracion);

						cargando_medicos.done( function(respuesta){

							var medicos_cargados = [];
							
							if (respuesta)
								medicos_cargados = respuesta;
									
									
									
							$("#detalle_elemento").find("#select_medicos").multiselect({
								header: false,
								minWidth: 225,
								selectedList: 3,
								noneSelectedText: _('Médicos disponibles'),/*IDIOMAOK*/
								//multiple: false,
								selectedText: _('# medicos seleccionados...')/*IDIOMAOK*/
							});
							
							var $medicos = $("#detalle_elemento").find("#select_medicos");
						
							
							for (var j = 0; j < medicos_cargados.length; j++) {
								var id = medicos_cargados[j].id;
								var nombre = medicos_cargados[j].nombre;
								
								var existe = false;
								if(arg_detalle_servicio){
									for(var e = 0; e < arg_detalle_servicio.medicos.length; e++){
										if (arg_detalle_servicio.medicos[e].id == id){
											existe = true;
										}
									
									}
								}
								var op = $('<option value="' + id + '">' + nombre + '</option>');
								
								if (existe){
									op.attr('selected', '');
								}
								
								$medicos.append(op);
								//	construir html de la agenda
						
							}

							$medicos.multiselect('refresh');
									
						
						});					
		
				
			
			},			
			
			construir_detalle_servicios: function ( datos, datos_centro,id_nodo) {

				var cargando_contenido_servicios = TM.content_administracion.load_content( $("#detalle_elemento"), "content/servicio.html"+ew_version_param());

				cargando_contenido_servicios.done(function(content_cargado) {
					
					if(datos) {
						//se trata de un modificar
						$("#detalle_elemento").find("#codigo-servicio").val(datos.datos_servicio.codigo);
						$("#detalle_elemento").find("#nombre-servicio").val(datos.datos_servicio.nombre);
						
						var obteniendo_detalle_servicio = Endosys.servicios.show(	TM.content_administracion, datos.datos_servicio.id );
						obteniendo_detalle_servicio.done( function (arg_detalle_servicio) {
							administracion.pintar_asignar_medicos_salas( datos_centro, arg_detalle_servicio );
					
						});						
					}else{
						administracion.pintar_asignar_medicos_salas( datos_centro );
					}
					$( "#modificar_btn" )
					.button()
					.click(function( event ) {
						var params_servicio = {};
						var iscorrect =  true;
						if ( !$("#detalle_elemento").find("#codigo-servicio").val() || !$("#detalle_elemento").find("#nombre-servicio").val())
							iscorrect = false;
						
						if (iscorrect){
						
							params_servicio.codigo = $("#detalle_elemento").find("#codigo-servicio").val();					
							params_servicio.nombre = $("#detalle_elemento").find("#nombre-servicio").val();
							var sala_checked = []; 
							$("#detalle_elemento").find("#select_salas :selected").each(function(i, selected){ 
							  //$(selected).text(); 
							  sala_checked.push($(selected).val());
							});
							
							params_servicio.salas = sala_checked.join();
							
							var medico_checked = []; 
							$("#detalle_elemento").find("#select_medicos :selected").each(function(i, selected){ 
							  //$(selected).text(); 
							  medico_checked.push($(selected).val());
							});
							params_servicio.medicos = medico_checked.join();
							
																					
							var mofificando_servicio = Endosys.servicios.update(TM.content_administracion, datos.datos_servicio.id, params_servicio)
							mofificando_servicio.done(function(content_cargado) {
								//lo ideal seria actualizar el objeto con datos que devuelve el update, aunque siempre serán los mismos
								//datos.datos_servicio.nombre = params_servicio.nombre
								//datos.datos_servicio.codigo = params_servicio.codigo;
								
								administracion.mostrar(function() {									
									$("#organizacion").jstree("select_node", "#"+id_nodo);
									
								});
								
							})
							
							
							
						}else{
							alert(_('Debe de completar todos los campos del servicio'));/*IDIOMAOK*/
						}
						

					});
					$( "#nuevo_btn" )
					.button()
					.click(function( event ) {
						var params_servicio = {};
						var iscorrect =  true;
						if ( !$("#detalle_elemento").find("#codigo-servicio").val() || !$("#detalle_elemento").find("#nombre-servicio").val())
							iscorrect = false;
						
						if (iscorrect){
							params_servicio.centro_id = datos_centro.id;
							params_servicio.codigo = $("#detalle_elemento").find("#codigo-servicio").val();					
							params_servicio.nombre = $("#detalle_elemento").find("#nombre-servicio").val();
							var sala_checked = []; 
							$("#detalle_elemento").find("#select_salas :selected").each(function(i, selected){ 
							  //$(selected).text(); 
							  sala_checked.push($(selected).val());
							});
							
							params_servicio.salas = sala_checked.join();
							
							var medico_checked = []; 
							$("#detalle_elemento").find("#select_medicos :selected").each(function(i, selected){ 
							  //$(selected).text(); 
							  medico_checked.push($(selected).val());
							});
							params_servicio.medicos = medico_checked.join();
							
							var crear_servicio = Endosys.servicios.create(TM.content_administracion, params_servicio);
							crear_servicio.done(function(servicio) {

								administracion.mostrar(function() {									
									$("#organizacion").jstree("select_node", "#servicio_"+servicio.id);
									
								});
							})

							
							
						}else{
							alert(_('Debe de completar todos los campos del servicio'));/*IDIOMAOK*/
						}
						

					});
					$( "#eliminar_btn" )
					.button()
					.click(function( event ) {
						
							
						var eliminando_servicio = Endosys.servicios['delete'](TM.content_administracion, datos.datos_servicio.id);
						eliminando_servicio.done(function() {

							administracion.mostrar();	
						})
						eliminando_servicio.fail(function() {
							alert(_('Error al eliminar el servicio'));/*IDIOMAOK*/
						})												

					});					
					
					if(datos){
						$( "#nuevo_btn" ).hide();					
					}else{
						$( "#modificar_btn" ).hide();
						$( "#eliminar_btn" ).hide();						
					}

				});
			},			
			
			obtener_detalle_agenda: function () {
				//_init();
				var params_agenda = {};
				params_agenda.codigo = $("#detalle_elemento").find("#codigo-agenda").val();					
				params_agenda.nombre = $("#detalle_elemento").find("#nombre-agenda").val();
				

				var sala_checked = []; 
				$("#detalle_elemento").find("#select_salas :selected").each(function(i, selected){ 
				  //$(selected).text(); 
				  sala_checked.push($(selected).val());
				});
				
				params_agenda.salas = sala_checked.join();
				
				var medico_checked = []; 
				$("#detalle_elemento").find("#select_medicos :selected").each(function(i, selected){ 
				  //$(selected).text(); 
				  medico_checked.push($(selected).val());
				});
				params_agenda.medicos = medico_checked.join();

				// recoger horarios de pantalla
				var horarios = [];
				
				for (var i=0 ; i < dias_semana.length ; i++) {
					var registro_hora=[];
					$("#"+dias_semana[i].codigo + ">div").each(function(e, selected) {
						registro_hora.push($(selected).find(".hora_ini").val()+"-"+$(selected).find(".hora_fin").val());
					});
					params_agenda[dias_semana[i].codigo] = registro_hora.join();
				}

				return params_agenda;
			},
			
			construir_detalle_agendas: function (datos_servicio, datos_agenda, id_nodo) {
				
				var cargando_contenido_agendas = TM.content_administracion.load_content( $("#detalle_elemento"), "content/agenda.html"+ew_version_param());

				cargando_contenido_agendas.done(function(content_cargado) {
					
					if(datos_agenda){
						//modificar agenda
						$("#detalle_elemento").find("#codigo-agenda").val(datos_agenda.codigo);
						$("#detalle_elemento").find("#nombre-agenda").val(datos_agenda.nombre);
					}
					
					$( "#modificar_btn" )
					.button()
					.click(function( event ) {
						
						
						var iscorrect =  true;
						if ( !$("#detalle_elemento").find("#codigo-agenda").val() || !$("#detalle_elemento").find("#nombre-agenda").val())
							iscorrect = false;
						
						if (iscorrect){
																				  

							var params_agenda = administracion.obtener_detalle_agenda();
							params_agenda.servicio_id = datos_servicio.id;
							
							var modificando_agenda = Endosys.agendas.update(TM.content_administracion, datos_agenda.id, params_agenda);
							modificando_agenda.done(function() {
								//lo ideal seria actualizar el objeto con datos que devuelve el update, aunque siempre serán los mismos
								/*datos_agenda.agenda_nombre = params_agenda.nombre;
								datos_agenda.agenda_codigo = params_agenda.codigo;*/
								administracion.mostrar(function() {
									$("#organizacion").jstree("select_node", "#"+id_nodo);
									
								});	
							})

						}else{
							alert(_('Debe de completar todos los campos de la agenda'));/*IDIOMAOK*/
						}
							

					});
					$( "#nuevo_btn" )
					.button()
					.click(function( event ) {
						
						
						var iscorrect =  true;
						if ( !$("#detalle_elemento").find("#codigo-agenda").val() || !$("#detalle_elemento").find("#nombre-agenda").val())
							iscorrect = false;
						
						if (iscorrect){
							
							var params_agenda = administracion.obtener_detalle_agenda();
							params_agenda.servicio_id = datos_servicio.id;
							
							var creando_agenda = Endosys.agendas.create(TM.content_administracion, params_agenda);
							creando_agenda.done(function(agenda) {

								administracion.mostrar(function() {
									//alert("oky");
									$("#organizacion").jstree("select_node", "#"+agenda.id);
									
								});	
							})

						}else{
							alert(_('Debe de completar todos los campos de la agenda'));/*IDIOMAOK*/
						}
							

					});
					$( "#eliminar_btn" )
					.button()
					.click(function( event ) {
						
							
						var eliminando_agenda = Endosys.agendas['delete'](TM.content_administracion, datos_agenda.id);
						eliminando_agenda.done(function() {

							administracion.mostrar();	
						})
						eliminando_agenda.fail(function() {
							alert(_('Error al eliminar la agenda'));/*IDIOMAOK*/
						})		
										

					});
					
					if(datos_agenda){
						$( "#nuevo_btn" ).hide();					
					}else{
						$( "#modificar_btn" ).hide();	
						$( "#eliminar_btn" ).hide();
					}

					var obteniendo_detalle_servicio = Endosys.servicios.show(	TM.content_administracion, datos_servicio.id );

					obteniendo_detalle_servicio.done( function (arg_detalle_servicio) {
						
						// cargar en el select de salas las salas del servicio
						$("#detalle_elemento").find("#select_salas").multiselect({
							header: false,
							minWidth: 225,
							selectedList: 3,
							noneSelectedText: _('Salas disponibles'),/*IDIOMAOK*/
							//multiple: false,
							selectedText: _('# salas seleccionados...')/*IDIOMAOK*/
						});
						
						var $salas = $("#detalle_elemento").find("#select_salas");
					
						
						for (var j = 0; j < arg_detalle_servicio.salas.length; j++) {
							var id = arg_detalle_servicio.salas[j].id;
							var nombre = arg_detalle_servicio.salas[j].nombre;

							var existe = false;
							if(datos_agenda){
								for(var e = 0; e < datos_agenda.salas.length; e++){
									if (datos_agenda.salas[e].id == id){
										existe = true;
									}
								
								}		
							}
							
							var op = $('<option value="' + id + '">' + nombre + '</option>');
							
							if (existe){
								op.attr('selected', '');
							}
							
							$salas.append(op);
							
					
						}

						$salas.multiselect('refresh');
						//fin de la carga del select salas del servicio
						
						//cargar en el select de medicos los medicos del servicio
						$("#detalle_elemento").find("#select_medicos").multiselect({
							header: false,
							minWidth: 225,
							selectedList: 3,
							noneSelectedText: _('Médicos disponibles'),/*IDIOMAOK*/
							//multiple: false,
							selectedText: _('# médicos seleccionados...')/*IDIOMAOK*/
						});
						
						var $medicos = $("#detalle_elemento").find("#select_medicos");
					
						
						for (var j = 0; j < arg_detalle_servicio.medicos.length; j++) {
							var id = arg_detalle_servicio.medicos[j].id;
							var nombre = arg_detalle_servicio.medicos[j].nombre;

							if (arg_detalle_servicio.medicos[j].tipo === "1") continue;
							var existe = false;
							
							if(datos_agenda){
								for(var e = 0; e < datos_agenda.medicos.length; e++){
									if (datos_agenda.medicos[e].id == id){
										existe = true;
									}
								
								}								
							}
							var op = $('<option value="' + id + '">' + nombre + '</option>');
							
							if (existe){
								op.attr('selected', '');
							}							

							
							$medicos.append(op);
							//	construir html de la agenda
					
						}

						$medicos.multiselect('refresh');
						//fin de lacargar en el select de medicos los medicos del servicio
						if(datos_agenda){
							administracion.pintar_horarios(datos_agenda.horarios);
						}
						administracion.pintar_boton_mas();
					
					});
					
					
				});
			
			
			},
			
			pintar_horarios: function (datos_horarios) {
				//_init();
				for(var i = 0; i < dias_semana.length; i++){
					var dia = dias_semana[i];
					if(datos_horarios[dia.codigo].horas){
						for (var e = 0; e < datos_horarios[dia.codigo].horas.length; e++){
							administracion.pintar_elemento_hora( dia, datos_horarios[dia.codigo].horas[e].ini,datos_horarios[dia.codigo].horas[e].fin);						
							
						}
					}
				
				}
				
			
			},			
			
			pintar_elemento_hora: function (dia,horas_ini,hora_fin) {
				
				var paraf = $('<div class="pure-g"></div>'); 
				
				var label = $('<div class="pure-u-1-4" ><label class="dia"></label></div>');
				label.html(dia.descr);
				label.appendTo(paraf);
				
				var input_ini =  $('<div class="pure-u-1-4" ><input class="hora_ini"></input></div>');
				input_ini.find("input").first().val(horas_ini);
				input_ini.appendTo(paraf);				
				
				var input_fin =  $('<div class="pure-u-1-4" ><input class="hora_fin"></input></div>');
				input_fin.find("input").first().val(hora_fin);
				input_fin.appendTo(paraf);		
							
				
				var id_dia = "#" + dia.codigo;
				$("#horarios").find(id_dia).append(paraf);
				
				administracion.pintar_boton_menos( paraf );					
			
			
			},
//
			pintar_boton_menos: function(paraf_element){
						
				var contenedor = $('<div class="pure-u-1-4" ></div>');				
				var button_menos = $('<button type="button" class="menos_button"></button>');
				button_menos.html('-');
				button_menos.appendTo(contenedor);
				
				//paraf_element.append(button_menos);
				contenedor.appendTo(paraf_element);
				button_menos.button({
					icons: {
						primary: "ui-icon-minusthick"
					},
					text: false
				});       
				button_menos.click(function( event ) {
					paraf_element.remove();

					
				});
			},
			
			pintar_boton_mas: function(){

						button_mas = $("#botones_horarios .mas_button");
						button_mas.button({
							icons: {
								primary: "ui-icon-plusthick"
							},
							text: false
						});       
						button_mas.click(function( event ) {
							var promise = dialogo_hora.crear_dialogo_hora();
							promise.done(function(new_hora) {
								administracion.pintar_elemento_hora( new_hora.dia , new_hora.hora_ini , new_hora.hora_fin );		
							});
							
						});
						
			}			
//
		}

}();
