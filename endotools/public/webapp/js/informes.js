var informes = function() {

	var datatable_informes;

	return {
		informe_id: null,	
		informe_invalido: null,
		datatable_informes: undefined,

		nombre_sin_extension: function(nombre_informe) {
			if (!!nombre_informe) {
				var s = nombre_informe.split('.');
				s.pop();		//	quitar el ultimo elemento, que es la extension
				s = s.join('');	//	rejuntar todos los elementos (excepto la extension)
				return s;
			}
		},
		
		nombre_sin_ruta: function(nombre_informe) {
			if (!!nombre_informe) {
				var s = nombre_informe.split('\\');
				s = s.pop();		//	obtener el ultimo elemento, que es el nombre de archivo
				s = s.split('/');	//	por si acaso separar también por /
				return s.pop();
			}
		},
		
		ini_form_expl: function() {
			//	crear datatable de informes
			informes.informe_id = null;
			informes.informe_borrado = null;

			 YAHOO.widget.DataTable.formatTipo = function(elLiner, oRecord, oColumn, oData) {
			    var tipo = parseInt(oData, 10);
			    switch(tipo) {
			        case 0:
			            elLiner.innerHTML = '<i class="fa fa-file-text" aria-hidden="true" title="' + _("Informe") + '"></i>';
			            break;
			        case 1:
			            elLiner.innerHTML = '<i class="fa fa-pencil-square-o" aria-hidden="true" title="' + _("Informe firmado") + '"></i>';
			            break;
			        case 10:
			            elLiner.innerHTML = '<i class="fa fa-paperclip" aria-hidden="true" title="' + _("Adjunto") + '"></i>';
			            break;
			        default:
			            elLiner.innerHTML = '<i class="fa fa-file-o" aria-hidden="true" title="' + _("Otros") + '"></i>';
			    }
			 };

			 YAHOO.widget.DataTable.formatComentario = function(elLiner, oRecord, oColumn, oData) {
			    if (!!oData) {
					elLiner.innerHTML = oData;
				} else {
					if (!!oRecord._oData.plantilla) {
						elLiner.innerHTML = "<em>" + oRecord._oData.plantilla + "</en>";
					} else {
						elLiner = "";
					}
				}
			 };

			var fielddef = [
					{key: 'tipo', label: '', width: 8, formatter:YAHOO.widget.DataTable.formatTipo, resizable: false, sortable: true},
					{key: 'numero', label: 'Nº', width: 60, resizeable: true, sortable: true},
					{key: 'fecha', label: _('Fecha'), width: 80, resizeable: true, sortable: true},/*IDIOMAOK*/
					{key: 'comentarios', label: _('Comentarios'), formatter:YAHOO.widget.DataTable.formatComentario, width: "auto", resizeable: false, sortable: false},
				];
				
			// Define un custom row formatter para tachar los no válidos
			var rowFormatter = function(elTr, oRecord) {
				if (oRecord.getData('borrado') == true) {
					$(elTr).addClass('informe-invalido');
				}
				return true;
			};
				
			informes.datatable_informes = new YAHOO.widget.ScrollingDataTable("exploracion-datatable-informes",
																fielddef,
																dummyDataSource,
																{ initialLoad: false,
																  MSG_EMPTY: '<div style="width:550px;"><em>' + _('La exploración no tiene informes') + '</em></div>',/*IDIOMAOK*/
																  height: "200px",
																  //width: "360px",
																  width: "100%",
																  formatRow: rowFormatter
																});
			datatable_informes = informes.datatable_informes;
			controles.init_YUI_datatable(datatable_informes)
			
			//	quitar la extension a la columna plantilla
			datatable_informes.doBeforeLoadData = function (sRequest, oResponse, oPayload) {
				for (var n=0; n < oResponse.results.length; n++) {
					oResponse.results[n].plantilla = informes.nombre_sin_extension(informes.nombre_sin_ruta(oResponse.results[n].plantilla));
				}
				return true;
			};
			
			//	evento click en una fila de la tabla de informes
			datatable_informes.subscribe("rowClickEvent", function(oArgs) {
				this.unselectAllRows();
				this.selectRow(oArgs.target);
				this.clearTextSelection();
				if (datatable_informes.getRecord(oArgs.target)) {
					informes.informe_id = datatable_informes.getRecord(oArgs.target).getData("id");
					informes.informe_borrado = datatable_informes.getRecord(oArgs.target).getData("borrado");
				}
			});
			
			//	boton ver
			$("#exploracion-ver-btn").button().click(function() {
				if (informes.informe_id) {
					informes.mostrar_informe(informes.informe_id);
				}
			});

			//	boton No Válido
			$("#exploracion-invalido-btn").off();
			$("#exploracion-invalido-btn").button().click(function() {
				// 2.4.10
				informes.marcar_no_valido(informes.informe_id);

				/* amtes de las 2.4.10
				//	modificar el informe, invalido=1 (si ya lo está no hacer nada)
				if ((informes.informe_id) && (informes.informe_borrado != true)) {
					controles.confirm_dialog(
					_('Informe no válido'),//IDIOMAOK
					_('¿Marcar el informe seleccionado como no válido? la operación no se puede deshacer'),//IDIOMAOK
					function() {
						
					});
				}*/
			});

			if (!userinfo.tiene_permiso("borrado_logico")){
				$("#exploracion-invalido-btn").hide();
			}

			//	boton firmar
			/*Y.on('click', function() {
					//	firmar electrónicamente el informe
					if (informes.informe_id) {
						informes.firmar_informe(informes.informe_id);
					}
				}, firmar_btn._button);*/

			//	dbl click = ver
			datatable_informes.subscribe("rowDblclickEvent", function() {
				$("#exploracion-ver-btn").click();
			});
			
			//	boton generar
			$("#exploracion-generar-btn").button().click(function() {
				//	generar un nuevo informe
				//	XXX	elegir plantilla!
				informes.generar_nuevo_informe(gestion_exploraciones.exploracion_id, null)
				.done(function(nuevoinforme) {
					//	actualizar la lista de informes
					informes.buscar_informes(gestion_exploraciones.exploracion_id);
					//	mostrar el nuevo
					informes.mostrar_informe(nuevoinforme.id);
				})
				.fail(function(respuesta){
					error = parseError(respuesta.responseText);
					if (error!=undefined){
						Endotools.statusbar.mostrar_mensaje(error, 1);	
					}
				});
			});

			//	boton adjuntar
			$("#exploracion-adjuntar-btn").button();

			document.getElementById('file').onchange = function () {
				if (( this.files[0].type !== "application/pdf" )) {
					alert (_("El fichero ha de ser un pdf."));
					return;
				} else if (( this.files[0].size > 5242880 )) {
					alert (_("El fichero ha de ser menor de 5Mb."));
					return;
				}
				var file = this.files[0];
				var reader = new FileReader();
				reader.readAsDataURL(file);
				reader.onload = function (e) {
					informes.adjuntar_documento(gestion_exploraciones.exploracion_id, e.target, file.name);
				}
				reader.onerror = function (error) {
					alert('Error: ' + error);
				}
			};
				
			//	boton generar informe con firma
			$('#exploracion-generarfirmado-btn').button().click(function() {
				//	previsualizar un informe
				informes.generar_nuevo_informe_firmado(gestion_exploraciones.exploracion_id, null)
				.done(function(nuevoinforme) {
					//	actualizar la lista de informes
					informes.buscar_informes(gestion_exploraciones.exploracion_id);
				});
			});
				
			//	buscar todos los informes de la expl
			informes.buscar_informes(gestion_exploraciones.exploracion_id);
		},
		
		desactivar_form: function() {

			$('#exploracion-tab-informes').html('<div class="pure-u-1-1"><p>' + _('Antes de poder generar informes se debe finalizar la exploración') + '</p></div>');/*IDIOMAOK*/
		

		},
		

		crear_btn_informes_anteriores: function(paciente_id){

			$("#exploracion-tab-informes").append('<hr /><button id="exploracion-ver-todos-informes">'+_("Ver todos los informes del paciente")+'</button>');//IDIOMAOK
			$("#exploracion-ver-todos-informes").button().click(function() {
				window.open("/rest/informes.html?_agrupado=si&paciente_id="+paciente_id+"&centro_id="+Endotools.auth.servicio_activo.centro_id,"_blank");
			});

		},

		buscar_informes: function(exploracion_id) {
			informes.informe_id = null;
			Endotools.informes.index(TM.content_exploraciones.detalles.informes,
									{'exploracion_id': exploracion_id},
									{datatable: datatable_informes});
		},
		
		mostrar_informe: function(id) {
			//	comprobar si es pdf o html segun la opcion de config			
			var ext = '.' + opciones_config.formato_informes;
			
			var show_toolbar = 'yes';
			var show_menubar = 'yes';
			var show_scrollbars = 'yes';
			if (ext == '.pdf') {
				show_toolbar = 'no';
				show_menubar = 'no';
				show_scrollbars = 'no';
			}			
			var w = screen.availWidth - 64;
			var h = screen.availHeight - 64;
			var l = (screen.availWidth - w) / 2;
			var t = (screen.availHeight - h) / 2;
			var ventana = window.open(Endotools.informes.resource + '/' + id + ext, "_blank",
					"resizable=yes," +
					"scrollbars=" + show_scrollbars + "," + 
					"location=no," +
					"menubar=" + show_menubar + "," + 
					"status=no," +
					"toolbar=" + show_toolbar + "," + 
					"fullscreen=no," +
					"width=" + w + ",height=" + h + ",left=" + l + ",top=" + t );
			if(!!ventana) {
				ventana.moveTo(l, t);
				ventana.resizeTo(w, h);
			}
		},

		marcar_no_valido: function(id) {
			
			// 2.4.10 Borrado logico de informe - reemplza a invalido
			controles.confirm_dialog(_('Borrar informe'), _('¿Está seguro de que desea borrar el informe?'),/*IDIOMAOK*/
				function() {														
					controles.input_dialog.mostrar(_('Motivo'), _('Ingrese el motivo por el cual desea borrar:'), '')//IDIOMAOK
					.then(function(motivo) {
						if (motivo!=""){
							Endotools.informes['delete'](TM.operaciones, id, {'borrado_motivo': motivo})
							.done(function()
							{
								informes.ini_form_expl();
							}).fail(function(data){
								var error = parseError(data);
								Endotools.statusbar.mostrar_mensaje(error, 1);
							});
						}else{
							Endotools.statusbar.mostrar_mensaje(_("Debe completar el motivo"), 1);//IDIOMAOK
						}
						
					});							
				});				

		}	
	
		,_generar_nuevo_informe_pre: function(exploracion_id, resultado) {
			//	preparación para generar un nuevo informe: guardar la expl y seleccionar la plantilla.
			//	devuelve un promise que en el resolved pasa la plantilla a usar finalmente como argumento.

			var crear_informe = function() {
				//	antes de crear el nuevo informe, se guarda la exploración
				return gestion_exploraciones.guardar_exploracion(TM.operaciones,
					gestion_exploraciones.exploracion_id,
					$("#exploracion_form"), $("#exploracion-tab-imagenes"))
					.then(function() { return resultado; });
			}
			
			if (resultado === null || resultado.plantilla === null) {
				//	seleccionar plantilla
				return plantillas_dialog.mostrar(exploracion_id)
				
				.then(function(resultado_usuario) {
					resultado = resultado_usuario;
					return crear_informe();
				});
			} else {
				/*	si ya se indica la plantilla, al no mostrarse el dialog donde también
					se advierte de que se guardarán los datos de la expl, mostrar esta
					advertencia antes.
					XXX este codigo no está probado.
				*/				
				return controles.confirm_dialog(_('Generar informe'),/*IDIOMAOK*/
					_('Antes de generar el informe se guardará cualquier cambio realizado en los datos de la exploración. ¿Desea continuar?'))/*IDIOMAOK*/
					
				.then(function() {
					return crear_informe();
				});
			}
		}
		
		,generar_nuevo_informe: function(exploracion_id, resultado) {

			//	genera un nuevo informe.
			//	devuelve un promise que en el resolved pasa el informe como argumento.
			return informes._generar_nuevo_informe_pre(exploracion_id, resultado)
			.then(function(resultado) {
				var params = {};
				params.tipo = 0;
				if (!!exploracion_id) params.exploracion_id = exploracion_id;
				if (!!resultado && !!resultado.comentarios) params.comentarios = resultado.comentarios;
				if (!!resultado && !!resultado.plantilla) {
					params.plantilla = resultado.plantilla;
					return Endotools.informes.create(TM.operaciones, params);
				} else {
					alert(_("No ha seleccionado ninguna plantilla"));
				}
			});
		}
		
		,generar_nuevo_informe_firmado: function(exploracion_id, resultado) {
			//	genera un nuevo informe firmado.
			//	devuelve un promise que en el resolved pasa el id del informe como argumento.
			return informes._generar_nuevo_informe_pre(exploracion_id, resultado)
			.then(function(resultado) {
				if (resultado !== null && resultado.plantilla !== null) {
					return firma_electronica.preview_firmar_y_enviar(exploracion_id, resultado.plantilla, resultado.comentarios);
				} else {
					alert(_("No ha seleccionado ninguna plantilla"));
				}
			});
		}

		,adjuntar_documento: function(exploracion_id, file, file_name) {
			controles.confirm_dialog(file_name, _('¿Está seguro de que desea subir el documento?'),/*IDIOMAOK*/
			function() {
				controles.input_dialog.mostrar(_('Comentario'), _('Ingrese un comentario:'),
					informes.nombre_sin_extension(file_name))//IDIOMAOK
				.then(function(comentario) {
					var params = {};
					params.tipo = 10;
					params.pdf = file.result;
					if (comentario!="") params.comentarios = comentario;
					if (!!exploracion_id) params.exploracion_id = exploracion_id;
					Endotools.informes.create(TM.operaciones, params)
					.done(function(nuevoinforme) {
					//	actualizar la lista de informes
						informes.buscar_informes(gestion_exploraciones.exploracion_id);
					});
				});
			});
		}
	}


}();