var gestion_agenda = function() {

	var dias_semana = null;
	var _initialized = false;
	function _init() {
		if (_initialized) return;
		dias_semana = [
			{num: 0, codigo: "LUNES"/*NO TRADUCIR*/,	descr: _('Lunes')},	/*IDIOMAOK*/
			{num: 1, codigo: "MARTES"/*NO TRADUCIR*/,	descr: _('Martes')},	/*IDIOMAOK*/
			{num: 2, codigo: "MIERCOLES"/*NO TRADUCIR*/,descr: _('Miércoles')},/*IDIOMAOK*/
			{num: 3, codigo: "JUEVES"/*NO TRADUCIR*/,	descr: _('Jueves')},	/*IDIOMAOK*/
			{num: 4, codigo: "VIERNES"/*NO TRADUCIR*/,	descr: _('Viernes')},	/*IDIOMAOK*/
			{num: 5, codigo: "SABADO"/*NO TRADUCIR*/,	descr: _('Sábado')},	/*IDIOMAOK*/
			{num: 6, codigo: "DOMINGO"/*NO TRADUCIR*/,	descr: _('Domingo')}	/*IDIOMAOK*/
		];
		_initialized = true;
	}

	var tipos_expl = null;
	var prioridades = null;
	
	return {
		hora_min: null,
		hora_max: null,
		weekend: false,
		cita_highligth: null,	
		agendas: null,					

		//buscar_cita: {
		//	cita_seleccionada: null,
		//},
		
		mostrar: function() {
			_init();
			
			TM.gestion_agenda.activate();
			//TM.content_tiposExploracion.activate();
			TM.content_administracion.activate();
			
			Endosys.statusbar.mostrar_mensaje(_('Loading...'));/*IDIOMAOK*/
			return TM.gestion_agenda.load_content(mainlayout, "content/calendario.html"+ew_version_param())
			.done(function() {
			    
				//CREACION DE LAYOUT
				$('.layout_main_content').layout({
					west__size:			325,
					spacing_closed:		10,
					slideTrigger_open:	"click",
					initClosed:			false,
					resizable:			false,
					center: {
						onresize: function() {
							$('#calendar').resize();
						}
					}
				});
				
				$('.contenedor2').layout({
					north: {
						size:	410
					},
					resizable:	false,
					slidable:	false,
					closable:	false,											
				});		
				
				$('#agenda-filter')
				.add('#sala-filter')
				.add('#medico-filter')
				.add('#exam-type-filter')
				.add('#prioridad-filter')
				//.addClass('selectboxit-small')
				/*.selectBoxIt({
					copyClasses: "container",	//	necesario para aplicar el estilo
					autoWidth:	false,
					theme:		"jqueryui"
				})*/
				//	estos eventos son para que el dropdown quede por encima de los demas paneles, del resizer, etc...
				.on('open', function() {
					$('.contenedor2').layout().allowOverflow('north');
				})
				.on('close', function() {
					$('.contenedor2').layout().resetOverflow('north');
				});

				var peticion_agendas = gestion_agenda.get_agendas().done(function(agendas) {
					/*gestion_agenda.pintar_zona_filtros(agendas);
					gestion_agenda.crear_calendario(agendas);*/
					return agendas;
				});
				
				//content_tiposExploracion
				var peticion_tipos_exploracion = Endosys.tipos_exploracion.index(TM.content_administracion, {activo: 1}).done(function(tipos_exploracion) {					
					return tipos_exploracion;
				});
				
				//content prioridades
				var cargando_prioridades = Endosys.prioridades.index(TM.content_administracion);
					
				cargando_prioridades.done(function(lista_prioridades) {
					//cargar las prioridades en el arbol

					return lista_prioridades;

				});
				$.when(peticion_tipos_exploracion,peticion_agendas,cargando_prioridades)
				.done(function(tipos_exploracion, agendas, lista_prioridades) {
					tipos_expl = tipos_exploracion[0];
					prioridades = lista_prioridades[0];
					gestion_agenda.pintar_zona_filtros(agendas, tipos_expl, prioridades);
					gestion_agenda.crear_calendario(agendas);

					gestion_agenda.tipos_expl = tipos_expl;
					gestion_agenda.agendas = agendas;
					gestion_agenda.prioridades = prioridades;

				});
				Endosys.statusbar.mostrar_mensaje(_('Ready'));/*IDIOMAOK*/
				

				/*Crea el boton de buscar paciente*/
				$("#paciente-filter-btn").button().click(function(){
					if(!dialogo_paciente.existe_dialog()){
						dialogo_paciente.mostrar_dialogo_paciente()
						.done(function(datos_paciente) {
							var titulo_dialog = (datos_paciente.nombre || "") + " " +
												(datos_paciente.apellido1 || "") + " " +
												(datos_paciente.apellido2 || "") +
												(" - " + datos_paciente.idunico || "");

							var content_busqueda_citas = $("<div id='content_busqueda_citas' class='layout-background'></div>");
							var mostrando_dialog = $.Deferred();
							$('body').append(content_busqueda_citas);
							busqueda_citas.mostrar_para_dialogo(function() {
								$('#content_busqueda_citas').dialog({
									modal: true,
									autoOpen: false,
									resizable: false,						
									title: _('Seleccionar cita del paciente')+": "+ titulo_dialog,/*IDIOMAOK*/
									//show: 'clip', 
									//hide: 'clip',
									height: 600,
									//height: 700,
									width: 1000,
									close: function() {
										$('#content_busqueda_citas').dialog( "destroy" );
										$('#content_busqueda_citas').remove();
									},
									buttons: [{
										text: _('Seleccionar'),/*IDIOMAOK*/
										click: function() {
											if (busqueda_citas.cita_id==null){
												alert(_('Debe seleccionar una cita'));//IDIOMAOK
											}else{
												datos_cita =  busqueda_citas.datos_cita_seleccionada;
												$( this ).dialog( "close" );
												mostrando_dialog.resolve(datos_cita);
											}
										}
									}, {
										text: _('Cancelar'),/*IDIOMAOK*/
										click: function() {
											$( this ).dialog( "close" );							
											mostrando_dialog.reject();
										}	
									}]
								});
								$('#content_busqueda_citas').dialog( "open" );
							}, content_busqueda_citas, 

							//filtros de las cita
							{
								'paciente_id': datos_paciente.id,
							 	'exploracion_id': null,
							 	'cancelada': '0'}
							);
							
							mostrando_dialog.done(function(datos_cita) {
								//gestion_agenda.buscar_cita.cita_seleccionada = datos_cita;
								gestion_agenda.mostrar_cita_en_calendario(datos_cita);
							});


						});
					}
				});
					
			});
		},
		
		crear_calendario: function(agendas, dia_seleccionado) {
			var params_filter = gestion_agenda.obtener_valores_filtros();	
			var minTime;
			var maxTime;
			if (params_filter.agenda_id) {
				var horario_no_laboral = gestion_agenda.obtener_horario_agenda(params_filter.agenda_id);
				var date_min_max = gestion_agenda.interpretar_date(gestion_agenda.hora_min,gestion_agenda.hora_max);
				minTime = date_min_max.hora_ini+":"+date_min_max.minuto_ini;
				maxTime = date_min_max.hora_fin+":"+date_min_max.minuto_fin;;
			}
			
			var date = new Date();
			if (dia_seleccionado){
				date = dia_seleccionado;
			}
			
			var d = date.getDate();
			var m = date.getMonth();
			var y = date.getFullYear();

			/*$("window").on("resize", "#agenda-content", function(e){
				e.stopPropagation();
				$('#calendar').fullCalendar('option', 'height', $("#agenda-content").height());
			});*/
			
			var calendar = $('#calendar').fullCalendar({
				header: {
					left:		'prev,next today',
					center:		'title',
					right:		'agendaWeek,agendaDay' //'month,agendaWeek,agendaDay'
				},
				defaultView:	'agendaWeek',
				allDaySlot:		false, //visualizar allday
				minTime:		minTime, //hora inicio
				maxTime:		maxTime, //hora fin				
				firstDay:		1, //dia en que empieza la semana
				selectable:		true,							
				selectHelper:	true,
				weekends:		gestion_agenda.weekend, //mostrar fines de semana si o no por defecto los muestra
				axisFormat:		'HH:mm', //formato en que sale la barra X del tiempo
				slotMinutes:	opciones_config["GESTION_AGENDA.CELDA.MINUTOS"],
				allDayText:		"", //texto que substituye al texto all-day de la barra all-day
				editable:		true,
				theme: true,
				themeButtonIcons: {
					prev: 'triangle-1-e',
					next: 'triangle-1-w'				
				},
				year: y,
				month: m,
				date: d,
				//contentHeight: 1000,
				height: $("#agenda-content").height(),
				handleWindowResize: false,
				
				windowResize: function(view){
					$('#calendar').fullCalendar('option', 'height', $("#agenda-content").height());
				},
				
				dayClick: function(date, allDay, jsEvent, view) {
					//EN ESTA FUNCION SE IMPLEMENTA el salto a la vista agendaDay
					//pero solo se permite desde la vista agendaWeek y haciendole click en la casilla de allDay de la agendaWeek
					//en un futuro si se implementa la vista año se tendra que modificar
					var view = $('#calendar').fullCalendar('getView');
					if (allDay == true && view.name=='agendaWeek') {
						var dia = date.getDate();
						var mes = date.getMonth();
						var year = date.getFullYear();
						$('#calendar').fullCalendar('changeView', 'agendaDay');
						$('#calendar').fullCalendar('gotoDate', year, mes, dia);
					}
				},
				
				eventDrop: function(cal_event,dayDelta,minuteDelta,allDay,revertFunc, jsEvent, ui, view ) {
					//retorna true si esta haciendo overlap sobre un evento no_labora
					if (gestion_agenda.event_is_overlapping(cal_event)) {
						revertFunc();
					} else {
						var hoy = new Date();
						hoy.setHours(0, 0, 0, 0);
						if (cal_event.start < hoy){
							Endosys.statusbar.mostrar_mensaje(_('No puede asignar una fecha anterior a la actual'), 1);
							revertFunc();
						} else {
							gestion_agenda.modificar_horario(cal_event);
						}
					}
				},
				
				eventResize: function(cal_event,dayDelta,minuteDelta,revertFunc, jsEvent, ui, view ) {
					//retorna true si esta haciendo overlap sobre un evento no_labora
					if (gestion_agenda.event_is_overlapping(cal_event)) {
						revertFunc();
					} else {
						gestion_agenda.modificar_horario(cal_event);
					}
				},
				
				eventRender: function(cal_event, element) {
					element.bind('dblclick', function() {
					//doble click para el evento
						gestion_agenda.mostrar_pantalla_modificar(cal_event);
					});
				},
				
				eventAfterRender: function(cal_event, element, view) {
					if (cal_event.title == "no_laboral" ) {
						if (view.name == "agendaWeek") {
							element.css('left', element.position().left-2 + 'px');
							element.css('border-width', '0px');							
							element.width(element.width()+14);
							element.height(element.height()+1);
							//si NO el explorador es ie y version inferior o igual a la 7.0
							if ( !( $.browser.msie && $.browser.version <= 7.0) ) {
								element.css('opacity', '0.5');
							}
						} else if(view.name == "agendaDay") {
							element.css('left', element.position().left-2 + 'px');
							element.width(element.width()+46);
							element.height(element.height()+1);
							element.css('border-width', '0px');
							//si NO el explorador es ie y version inferior o igual a la 7.0
							if ( !( $.browser.msie && $.browser.version <= 7.0) ) {
								element.css('opacity', '0.5');
							}
						}
					}else{
						element.attr("id", cal_event.id);
						if ("cita-"+gestion_agenda.cita_highligth==cal_event.id){
							$(".fc-agenda > div > div").scrollTop(element.position().top);
							element.effect("pulsate",1500);
							gestion_agenda.cita_highligth=null;
						}
						
					}

				},
				
				select: function(start, end, allDay) {
					//crear la llamada del dialogo para generar el event
					//solo dejamos que lo ejecute si viene de un rango de celdas de las horas (timeSlot), nunca xa allday
					if (!allDay) { //solo se ejecuta la opcion desde la vista de dia
						var data_cita;
						var cal_event = new Object();
						cal_event.start = start;		
						cal_event.end = end;
						if (gestion_agenda.event_is_overlapping(cal_event)) {
							$('#calendar').fullCalendar( 'unselect' );
						} else {
							data_cita = gestion_agenda.interpretar_date(start,end);
							if(!dialogo_paciente.existe_dialog()){
								dialogo_paciente.mostrar_dialogo_paciente(true)
								.done(function(datos_paciente) {
									gestion_agenda.get_agendas().done(function(agendas) {
										var params_default = gestion_agenda.obtener_valores_filtros();
										if (datos_paciente) {
											dialogo_cita.mostrar_dialogo_cita(datos_paciente, data_cita, agendas, null, params_default, tipos_expl, prioridades)
											.always(function() {
												$('#calendar').fullCalendar( 'refetchEvents' );
											});
										}
									});
								});
							}
						}
					}
				},
				
				monthNames:		[_('Enero'), _('Febrero'), _('Marzo'), _('Abril'), _('Mayo'), _('Junio'), _('Julio'),/*IDIOMAOK*/
								_('Agosto'), _('Septiembre'), _('Octubre'), _('Noviembre'), _('Diciembre')],/*IDIOMAOK*/

				monthNamesShort:[_('Ene'), _('Feb'), _('Mar'), _('Abr'), _('May'), _('Jun'), _('Jul'),/*IDIOMAOK*/
								_('Ago'), _('Sep'), _('Oct'), _('Nov'), _('Dic')],/*IDIOMAOK*/
								
				dayNames:		[_('Domingo'), _('Lunes'), _('Martes'), _('Miércoles'),/*IDIOMAOK*/
								_('Jueves'), _('Viernes'), _('Sábado')],/*IDIOMAOK*/
								
				dayNamesShort:	[_('Dom'), _('Lun'), _('Mar'), _('Mie'), _('Jue'), _('Vie'), _('Sab')],/*IDIOMAOK*/
				
				timeFormat: {
					agenda:		'HH:mm{ - HH:mm}', //formato de la fecha en el evento en la vista agenda
					agendaDay:	'HH:mm{ - HH:mm}',
					'':			'HH:mm{ - HH:mm}'
				},
				
				columnFormat: {
					week:		'ddd d/M/yyyy', //formato de las columnas en dicha vista
					day:		'dddd d/M/yyyy',
					'':			'HH:mm{ - HH:mm}'
				},
				
				titleFormat: {//no funciona
					month:		'MMMM yyyy',                             // September 2009
					week:		"MMM d[ yyyy]{ '&#8212;'[ MMM] d yyyy}", // Sep 7 - 13 2009
					day:		'dddd, MMM d, yyyy'      
				},
				
				buttonText: {
					today:		_('Hoy'),/*IDIOMAOK*/
					week:		_('Semana'),/*IDIOMAOK*/
					day:		_('Día')/*IDIOMAOK*/
				},
				
				events: function(start, end, callback) {
				//llamada a las citas
				
					//En start siempre viene el primer dia de la semana para la vista weekagenda
					
					//intrepretear las fecha del objeto Date a nuestro modelo de datos 'dia/mes/año'
					var dia = start.getDate();
					//al mes se le suma uno xq va de 0...11
					var mes = start.getMonth() + 1;
					var year = start.getFullYear();
					var cadena_fecha = dia+"/"+mes+"/"+year;
					var view = $('#calendar').fullCalendar('getView');
					
					var params = gestion_agenda.obtener_valores_filtros();						
					if (view.name == 'agendaDay') {
						//obtenemos las citas de este dia
						params.fecha = cadena_fecha;
					} else if (view.name=='agendaWeek') {
						//obtenemos todas las citas de la semana a la que pertenece ese dia
						params.semana = cadena_fecha;
					}

					params.exploracion_id = '';	//	buscar las citas que no tienen expl. asignada, es decir, no realizadas
					params.cancelada = '0';
					Endosys.citas.index(TM.gestion_agenda, params)
					
					.done(function(citas) {
						var events = [];
						for (var i=0; i < citas.length; i++) {
							var fecha_data_start = gestion_agenda.desglosar_fecha_hora(citas[i].fecha, citas[i].hora);
							
							//definimos una fecha end igual que fecha star, pero con 30 minutos mas
							//PROVISIONAL											
							var duracion;
							if (!citas[i].duracion) {
								duracion = 30;
							} else {
								duracion =  parseInt(citas[i].duracion, 10);
							}
							
							var fecha_data_end = new Date();											
							fecha_data_end.setTime(fecha_data_start.getTime());
							//fecha_data_end.setMinutes(fecha_data_end.getMinutes()+30);
							fecha_data_end.setMinutes(fecha_data_end.getMinutes()+duracion);
							
							//-
							// Genera el titulo de acuerdo al formato del ini, busca variables en la 'cadena' 
							// que vienen con el formato '$campo' y los reemplaza por el valor
							var re = /\$(\w*)/gi; 
							var cadena = opciones_config["GESTION_AGENDA.CITA.FORMATO_TITULO"];
							var title = opciones_config["GESTION_AGENDA.CITA.FORMATO_TITULO"];
							var m;

							while ((m = re.exec(cadena)) !== null) {
							  if (m.index === re.lastIndex) {
							    re.lastIndex++;
							  }
							  if (citas[i].paciente[m[1].toString()]!=undefined){
								title = title.replace(m[0].toString(), citas[i].paciente[m[1].toString()]);
							  } else{
							  	title = title.replace(m[0].toString(), "");
							  }
							}
							//-

							var event = {
								id: "cita-"+ citas[i].id,
								title: title, //citas[i].paciente["historia"],//citas[i].paciente.historia,
								start: fecha_data_start,
								end: fecha_data_end,
								allDay: false,
							};

							//-- Color del evento dado por la exploracion, sino deja el por defecto
							if (citas[i].tipoExploracion !=null){
								event.color = citas[i].tipoExploracion.color;
								event.rendering = "background";
								bg_rgb = hexToRgb(event.color);
								event.textColor = textColorForBg(bg_rgb);
							}
							//--

							$(event).data("datos_cita", citas[i]);
							events.push(event);
						}
						gestion_agenda.crear_events_no_laboral(start,events);	



						callback(events);					
					})
					
					.fail(function(r) {
						var events = [];
						gestion_agenda.crear_events_no_laboral(start, events);
						if (r.status != 404) {
							Endosys.statusbar.mostrar_mensaje(_('Error al cargar las citas'),1);/*IDIOMAOK*/
							callback(events);
						} else {
							Endosys.statusbar.mostrar_mensaje(_('No se ha encontrado ninguna cita'));/*IDIOMAOK*/
							callback(events);
						}					
					});
				}
			});
		},
		
		event_is_overlapping: function(cal_event) {
			var validDrop = true;
			var ev = $("#calendar").fullCalendar("clientEvents");
			for (var e in ev) {
				if (ev[e].className.length > 0 && ev[e].className[0] == "no_laboral") {
					if (ev[e].start>=cal_event.start && ev[e].end<=cal_event.end)
						validDrop=false;
					if (ev[e].start<=cal_event.start && ev[e].end>=cal_event.end) 
						validDrop=false;
					if (ev[e].start<cal_event.start && ev[e].end<cal_event.end && ev[e].end>cal_event.start)
						validDrop=false;
					if (ev[e].end>cal_event.end && ev[e].start>cal_event.start && ev[e].start<cal_event.end)
						validDrop=false;
				}
			}
			return (!validDrop);
		},
		
		crear_events_no_laboral: function(start, events) {
			// CREAR LOS ENVENTOS DE HORARIO NO LABORAL
			var horario_no_laboral;
			var params = gestion_agenda.obtener_valores_filtros();		
			if (params.agenda_id) {
				horario_no_laboral = gestion_agenda.obtener_horario_agenda(params.agenda_id);
			}
			
			var view = $('#calendar').fullCalendar('getView');		
			
						
			//var desc_dia = gestion_agenda.obtener_codigo_dia(start.getDay());
			for (var i=0; i < horario_no_laboral.length; i++) {

				for (var j = 0; j < horario_no_laboral[i].no_laboral.length ; j++) {
					var fecha_data_start_party = new Date();
					var fecha_data_end_party = new Date();
					
					fecha_data_start_party.setTime(start.getTime());
					fecha_data_end_party.setTime(start.getTime());

					if (view.name=='agendaDay') {
						//cuando hay que cargar en la vista de dia
						var num_dia = start.getDay() - 1;//	getDay() interpreta 0-domingo, 1-lunes, 2-martes etc... y nosotros 0-lunes, 1-martes... 6-domingo
						if (num_dia == -1) num_dia = 6;//caso domingo
						var desc_day = gestion_agenda.obtener_codigo_dia(num_dia);
						if ( horario_no_laboral[i].dia != desc_day ) {
							break;
						}
					} else {
						var num_dia = gestion_agenda.obtener_num_dia(horario_no_laboral[i].dia);					
						fecha_data_start_party.setDate(start.getDate() + num_dia);
						fecha_data_end_party.setDate(start.getDate() + num_dia);
					}					
				
					fecha_data_start_party.setHours(horario_no_laboral[i].no_laboral[j].hora_ini);
					fecha_data_start_party.setMinutes(horario_no_laboral[i].no_laboral[j].minuto_ini);
					fecha_data_end_party.setHours(horario_no_laboral[i].no_laboral[j].hora_fin);
					fecha_data_end_party.setMinutes(horario_no_laboral[i].no_laboral[j].minuto_fin);
					
					var event_party = {
						title: "no_laboral",
						start: fecha_data_start_party,
						end: fecha_data_end_party,
						className: "no_laboral", 
						editable:false,
						backgroundColor: '#999999',
						textColor: '#999999',
						color: '#999999',
						allDay: false									
					};
					events.push(event_party);
				}
			}
			
			
			// FIN CREAR LOS ENVENTOS DE HORARIO NO LABORAL				
		
		},
		
		obtener_codigo_dia: function(num_dia) {
			for (var i=0; i<dias_semana.length; i++) {
				if (dias_semana[i].num == num_dia) return dias_semana[i].codigo;
			}
/*			//esta funcion es optima xa pasarle el resultado de start.getDay();
			//y nos devuelve la descripcion del dia en español			
			if( num_dia == 0) return 'sunday';
			if( num_dia == 1) return 'monday';
			if( num_dia == 2) return 'tuesday';
			if( num_dia == 3) return 'wednesday';
			if( num_dia == 4) return 'thursday';
			if( num_dia == 5) return 'friday';
			if( num_dia == 6) return 'saturday';*/
		},
		
		obtener_num_dia: function(codigo_dia) {
			for (var i=0; i<dias_semana.length; i++) {
				if (dias_semana[i].codigo == codigo_dia) return dias_semana[i].num;
			}
			return null;
/*			if( codigo_dia == 'DOMINGO') return 6;
			if( codigo_dia == 'LUNES') return 0;
			if( codigo_dia == 'MARTES') return 1;
			if( codigo_dia == 'MIERCOLES') return 2;
			if( codigo_dia == 'JUEVES') return 3;
			if( codigo_dia == 'VIERNES') return 4;
			if( codigo_dia == 'SATURDAY') return 5;*/
		},
		
		desglosar_fecha_hora: function(fecha,hora) {
			var array_fecha = fecha.split("/"); 
			var array_hora = hora.split(":"); 
			var obj_date = new Date(parseInt(array_fecha[2]), parseInt(array_fecha[1],10)-1,parseInt(array_fecha[0],10), parseInt(array_hora[0],10), parseInt(array_hora[1], 10));
			return obj_date;
		},
		
		interpretar_date: function(start,end){
			var data_cita = {};
			data_cita.dia = start.getDate();
			data_cita.mes = start.getMonth() + 1;
			data_cita.year = start.getFullYear();
			data_cita.hora_ini = start.getHours();
			data_cita.minuto_ini = start.getMinutes();
			if (data_cita.minuto_ini.toString().length == 1) {
				data_cita.minuto_ini = "0" + data_cita.minuto_ini;
			}
			data_cita.hora_fin = end.getHours();
			data_cita.minuto_fin = end.getMinutes();
			if (data_cita.minuto_fin.toString().length == 1) {
				data_cita.minuto_fin = "0" + data_cita.minuto_fin;
			}			
			return data_cita;

		},
		
		desglosar_fecha: function(fecha) {},
		
		desglosar_hora: function(hora) {
			var array_hora = hora.split(":"); 
			var obj_date = new Date(0,0,0, parseInt(array_hora[0],10), parseInt(array_hora[1], 10));
			
			return obj_date;
		},
		

		// Obtiene las agendas
		get_agendas: function() {
			if (gestion_agenda.agendas) {
				return $.Deferred().resolve(gestion_agenda.agendas).promise();
			} else {
				// devuelve solo las agendas del medico
				extra_params = {"medico_id": userinfo.get_usuario().medico.id};

				return Endosys.agendas.index(TM.gestion_agenda, extra_params)
				.then(function(response) {
					gestion_agenda.agendas = response;
					gestion_agenda.interpretar_datos_agenda(gestion_agenda.agendas);
					return gestion_agenda.agendas;
				});
			}
		},
										
        mostrar_pantalla_modificar: function(cal_event) {
			var data_cita ;							
			data_cita = gestion_agenda.interpretar_date(cal_event.start,cal_event.end);
			var datos_cita;
			datos_cita = $(cal_event).data("datos_cita");
			var datos_paciente = datos_cita.paciente;

			gestion_agenda.get_agendas().done(function(agendas) {
				dialogo_cita.mostrar_dialogo_cita(datos_paciente, data_cita, agendas, datos_cita, null, tipos_expl, prioridades)
				.done(function() {
					$('#calendar').fullCalendar( 'refetchEvents' );
				});
			});
		},
		
        modificar_horario: function(cal_event) {
			var data_cita ;							
			data_cita = gestion_agenda.interpretar_date(cal_event.start,cal_event.end);
			var datos_cita;
			datos_cita = $(cal_event).data("datos_cita");

			var params = {};
			params.fecha = data_cita.dia +"/"+data_cita.mes+"/"+data_cita.year;
			params.hora = data_cita.hora_ini +":"+ data_cita.minuto_ini; 
			params.hora_fin = data_cita.hora_fin +":"+ data_cita.minuto_fin;
			
			Endosys.citas.update(TM.gestion_agenda, datos_cita.id, params)
			.done(function() {
				$('#calendar').fullCalendar( 'refetchEvents' );
				Endosys.statusbar.mostrar_mensaje(_('La cita se ha modificado correctamente'));/*IDIOMAOK*/
			})
			.fail(function(r) {
				$('#calendar').fullCalendar( 'refetchEvents' );
				if (r.status != 400) {
					Endosys.statusbar.mostrar_mensaje(_('Error al modificar la cita'), 1);/*IDIOMAOK*/
				} else {
					Endosys.statusbar.mostrar_mensaje(_('Los datos de la cita no son válidos'));/*IDIOMAOK*/
				}
			});
		},			

		pintar_select_filter_tipos_expl: function(content_filter, tipos_expl) {
			var select_tipo_expl = content_filter.find("#exam-type-filter");
			select_tipo_expl.find("option").remove();
			select_tipo_expl.append($('<option value="-1" class="selectboxit-especial-item">' + _('Ninguno') + '</option>'));/*IDIOMAOK*/
			for (var i=0; i < tipos_expl.length; i++) {
				var option = $('<option value='+tipos_expl[i].id+'>'+tipos_expl[i].nombre+'</option>');
				option.data("datos_expl", tipos_expl[i]);
				option.appendTo( select_tipo_expl );
			}
			//select_tipo_expl.selectBoxIt('refresh');
		},
		pintar_select_filter_prioridades: function(content_filter, prioridades) {
			var select_prioridades = content_filter.find("#prioridad-filter");
			select_prioridades.find("option").remove();
			select_prioridades.append($('<option value="-1" class="selectboxit-especial-item">' + _('Ninguno') + '</option>'));/*IDIOMAOK*/
			for (var i=0; i < prioridades.length; i++) {
				var option = $('<option value='+prioridades[i].id+'>'+prioridades[i].nombre+'</option>');
				option.data("datos_prioridad", prioridades[i]);
				option.appendTo( select_prioridades );
			}
			//select_prioridades.selectBoxIt('refresh');
		},
		pintar_select_filter_medicos: function(content_filter, datos_agenda) {
			var select_medico = content_filter.find("#medico-filter");
			select_medico.find("option").remove();
			select_medico.append($('<option value="-1" class="selectboxit-especial-item">' + _('Ninguno') + '</option>'));/*IDIOMAOK*/
			for (var i=0; i < datos_agenda.medicos.length; i++) {
				var option = $('<option value='+datos_agenda.medicos[i].id+'>'+datos_agenda.medicos[i].nombre+'</option>');
				option.data("datos_medico", datos_agenda.medicos[i]);
				option.appendTo( select_medico );
			}
			//select_medico.selectBoxIt('refresh');
		},
		
		pintar_select_filter_salas: function(content_filter,datos_agenda){
			var select_sala = content_filter.find("#sala-filter");
			select_sala.find("option").remove();
			select_sala.append($('<option value="-1" class="selectboxit-especial-item">' + _('Ninguno') + '</option>'));/*IDIOMAOK*/
			for (var i=0; i<datos_agenda.salas.length; i++) {
				var option = $('<option value='+datos_agenda.salas[i].id+'>'+datos_agenda.salas[i].nombre+'</option>');
				option.data("datos_sala", datos_agenda.salas[i]);
				option.appendTo( select_sala );
			}
			//select_sala.selectBoxIt('refresh');
		},
		
		pintar_zona_filtros: function(agendas, tipos_expl, prioridades) {
			//preparacion de los filtros de las citas (agendas, medicos,salas)
			var content_filter = $(".layout_main_content");
			var select_agenda = content_filter.find("#agenda-filter");
			select_agenda.find("option").remove();

			//select_agenda.append($('<option value="-1">Select</option>'));

			for(var i=0;i<agendas.length;i++){
			
				var option = $('<option value='+agendas[i].agenda_id+'>'+agendas[i].agenda_nombre+'</option>');
				option.data("datos_agenda", agendas[i]);
																	
				option.appendTo( select_agenda );

			}
			var datos_agenda = select_agenda.find("option:selected").data().datos_agenda;
			gestion_agenda.pintar_select_filter_medicos(content_filter,datos_agenda);
			gestion_agenda.pintar_select_filter_salas(content_filter,datos_agenda);

			select_agenda.change(function() {
				var datos_agenda2 = $(this).find("option:selected").data().datos_agenda;
				gestion_agenda.pintar_select_filter_medicos(content_filter,datos_agenda2);
				gestion_agenda.pintar_select_filter_salas(content_filter,datos_agenda2);
				$('#calendar').fullCalendar('destroy');
				gestion_agenda.get_agendas().done(function(agendas) {
					gestion_agenda.crear_calendario(agendas);
				});
			});
			//select_agenda.selectBoxIt('refresh');
			
			$("#medico-filter").change( function(){
				$('#calendar').fullCalendar( 'refetchEvents' );
			});			
			$("#sala-filter").change( function(){				
				$('#calendar').fullCalendar( 'refetchEvents' );				
			});
			$("#exam-type-filter").change( function(){				
				$('#calendar').fullCalendar( 'refetchEvents' );				
			});			
			$("#prioridad-filter").change( function(){				
				$('#calendar').fullCalendar( 'refetchEvents' );				
			});			
			gestion_agenda.pintar_select_filter_tipos_expl(content_filter,tipos_expl);
						
			gestion_agenda.pintar_select_filter_prioridades(content_filter,prioridades);
			////FIN preparacion de los filtros 		
		},
		
		obtener_valores_filtros: function() {
			var content_filter = $(".layout_main_content");
			
			var select_agenda = content_filter.find("#agenda-filter");
			var select_medico = content_filter.find("#medico-filter");
			var select_sala = content_filter.find("#sala-filter");
			var select_tipo_expl = content_filter.find("#exam-type-filter");
			var select_prioridad = content_filter.find("#prioridad-filter");
			
			var params_filter = {};
			if (select_agenda.find("option:selected").val() != "-1") params_filter.agenda_id = select_agenda.find("option:selected").val();
			if (select_medico.find("option:selected").val() != "-1") params_filter.medico_id = select_medico.find("option:selected").val();			
			if (select_sala.find("option:selected").val() != "-1") params_filter.sala_id = select_sala.find("option:selected").val();
			if (select_tipo_expl.find("option:selected").val() != "-1") params_filter.tipoExploracion_id = select_tipo_expl.find("option:selected").val();
			if (select_prioridad.find("option:selected").val() != "-1") params_filter.prioridad_id = select_prioridad.find("option:selected").val();
			return params_filter;
		
		},
		
		obtener_horario_agenda: function(agenda_id) {
			//CONSTRUCCION DEL HORARIO NO LABORAL EN JAVASCRIPT
		
			var horario;
			gestion_agenda.hora_min = null;
			gestion_agenda.hora_max = null;
			gestion_agenda.weekend = false;
			//localizar la agenda seleccionada y recoger su horario
			for( var i = 0; i < gestion_agenda.agendas.length; i++){
				if( gestion_agenda.agendas[i].agenda_id == agenda_id ) horario = gestion_agenda.agendas[i].horarios;		

			}
			
			//recorrer horario para saber cual es la hora minima y maxima del horario
			//utilizada para pintar el calendario dinamicamente
			var no_limit = false; //variable xa controlar si hay hora min y max // si no hay se aplica por defecto 0-24
			for( var j = 0; j < horario.length; j++){
				for( var e = 0; e < horario[j].horas.length; e++){
					if(no_limit == false) no_limit = true;
					//si es sabado o domingo
					if(horario[j].numero == "5" || horario[j].numero == "6" ){
					//habilitar la opcion fin de semana
						gestion_agenda.weekend = true;
						//delete horario[j];
					}	 
					if(gestion_agenda.hora_min == null)	
						gestion_agenda.hora_min = gestion_agenda.desglosar_hora(horario[j].horas[e].ini);	
					if(gestion_agenda.hora_max == null)	
						gestion_agenda.hora_max = gestion_agenda.desglosar_hora(horario[j].horas[e].fin);
					
					var aux_hora_min = gestion_agenda.desglosar_hora(horario[j].horas[e].ini);
					var aux_hora_max = gestion_agenda.desglosar_hora(horario[j].horas[e].fin);
					
					if(gestion_agenda.hora_min > aux_hora_min) gestion_agenda.hora_min = aux_hora_min;	
					if(gestion_agenda.hora_max < aux_hora_max) gestion_agenda.hora_max = aux_hora_max;	
				}
			}
			
			if (no_limit == false) { //aplicamos horas minimas y maxima por defecto / estas horas son las que definen los limites del calendario
				gestion_agenda.hora_min = gestion_agenda.desglosar_hora("00:00:00");
				gestion_agenda.hora_max = gestion_agenda.desglosar_hora("23:59:00");
			}
			
			var horario_no_laboral = [];
			
			for( var j = 0; j < horario.length; j++){
				var horas_ini = [];
				var horas_fin = [];
				var no_laboral = {};
				no_laboral.numero = horario[j].numero;		
				no_laboral.dia = horario[j].dia;
				
				//invertimos los limites del intervalo
				horas_ini.push(gestion_agenda.hora_max.getTime());
				horas_fin.push(gestion_agenda.hora_min.getTime() )
				for( var e = 0; e < horario[j].horas.length; e++){
					
					var aux_ini = gestion_agenda.desglosar_hora(horario[j].horas[e].ini);
					var aux_fin = gestion_agenda.desglosar_hora(horario[j].horas[e].fin);
					horas_ini.push(aux_ini.getTime());
					horas_fin.push(aux_fin.getTime())
				}
				horas_ini.sort();
				horas_fin.sort();
				
				no_laboral.horas_ini = horas_ini;
				no_laboral.horas_fin = horas_fin;
				horario_no_laboral.push(no_laboral);
				
			}
			for( var j = 0; j < horario_no_laboral.length; j++){
				var intervalo_ini_fin = []
				for(var h = 0; h < horario_no_laboral[j].horas_fin.length; h++){
					var d1 = new Date(horario_no_laboral[j].horas_fin[h]);
					var d2 = new Date(horario_no_laboral[j].horas_ini[h]);
					var hora_ini_fin = {};
					
					hora_ini_fin.hora_fin  = d2.getHours();
					hora_ini_fin.minuto_fin = d2.getMinutes();
					hora_ini_fin.hora_ini = d1.getHours();
					hora_ini_fin.minuto_ini =  d1.getMinutes();
					
					//filtro para eliminar intervalos cerrados ej 18:00 - 18:00 
					if( hora_ini_fin.hora_fin != hora_ini_fin.hora_ini){																
						intervalo_ini_fin.push(hora_ini_fin);							
					}else{
						if (hora_ini_fin.minuto_fin != hora_ini_fin.minuto_ini) {						
							intervalo_ini_fin.push(hora_ini_fin);								
						}
					}
				
				}
				horario_no_laboral[j].no_laboral = 	intervalo_ini_fin;
				delete horario_no_laboral[j].horas_fin;
				delete horario_no_laboral[j].horas_ini;
			}
			
			return horario_no_laboral;
			
			
		
		}

		,interpretar_datos_agenda: function(agendas) {
			/*
			se transforman algunos datos de las agendas devueltas, para adaptarse
			al formato usado en las funciones.
			Antes esta funcion estaba en ET_agendas y interpretaba por completo
			el XML.
			*/
			_init();
			for (var i=0; i < agendas.length; i++) {
				//	info de la agenda
				agendas[i].agenda_codigo =	agendas[i].codigo;
				agendas[i].agenda_nombre =	agendas[i].nombre;
				agendas[i].agenda_id =		agendas[i].id;
				//	horarios
				agendas[i]._horarios = agendas[i].horarios;
				agendas[i].horarios = [];
				for (var j=0; j < 7; j++) {
					var dia = dias_semana[j].codigo;
					agendas[i]._horarios[dia].dia = dia;
					if (!agendas[i]._horarios[dia].horas)
						agendas[i]._horarios[dia].horas = [];
					agendas[i].horarios[j] = agendas[i]._horarios[dia];
				}
				//	servicio
				agendas[i].servicio.servicio_codigo =	agendas[i].servicio.codigo;
				agendas[i].servicio.servicio_nombre =	agendas[i].servicio.nombre;
				agendas[i].servicio.servicio_id =		agendas[i].servicio.id;
			}
		
		}		
		
		,mostrar_cita_en_calendario: function(datos_cita){
			var agenda_seleccionada = datos_cita.agenda_id;
			
			var dia_seleccionado = gestion_agenda.desglosar_fecha_hora(datos_cita.fecha, datos_cita.hora);
			
			gestion_agenda.pintar_zona_filtros(gestion_agenda.agendas, gestion_agenda.tipos_expl, 
											   gestion_agenda.prioridades);

			var content_filter = $(".layout_main_content");
			var select_agenda = content_filter.find("#agenda-filter");

			// Selecciona la agenda de la cita
			select_agenda.find('option[value="'+agenda_seleccionada+'"]').prop("selected",true);
			//select_agenda.selectBoxIt('refresh');


			var datos_agenda2 = select_agenda.find("option:selected").data().datos_agenda;
			gestion_agenda.pintar_select_filter_medicos(content_filter,datos_agenda2);
			gestion_agenda.pintar_select_filter_salas(content_filter,datos_agenda2);
			$('#calendar').fullCalendar('destroy');
			
			gestion_agenda.cita_highligth=datos_cita.id;
			gestion_agenda.crear_calendario(gestion_agenda.agendas, dia_seleccionado);

			
		}
		
	}


}();