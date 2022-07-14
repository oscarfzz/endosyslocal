var firma_electronica = function() {

  return {

	_firmar: function(dataB64) {
		/*
		intenta firmar un pdf. Si no lo consigue muestra el error y devuelve cadena vacía.
		Si lo consigue devuelve el pdf formado, en base64.
		*/
		//	XXX	estos valores han de ser configurables...
		//	ademas se ha de filtrar los tipos de certificados a mostrar, y ver si se indica
		//	un tipo de almacén explicito (esto en la llamada a la función "cargarMiniApplet()"
		//	de main.html)
		var formato = 'Adobe PDF';		//	posibles valores: CAdES, Adobe PDF, XAdES, ODF
		var algoritmo = 'SHA1withRSA';	//	posibles valores: SHA1withRSA, SHA256withRSA, SHA384withRSA, SHA512withRSA
		var extraparams = '';

		//	firmar (el resultado está en base64)
		try {
			return MiniApplet.sign(dataB64, algoritmo, formato, extraparams);
		} catch(e) {
			//	XXX mejor usar MiniApplet.getErrorType() y mostrar un error personalizado (mirar la documentación)
			alert(_('Error firmando el PDF') + ': ' + MiniApplet.getErrorMessage());/*IDIOMAOK*/
			return '';
		}
	}
	
/*	,firmar: function(informe_id) {
	
		controles.confirm_dialog('Endosys App', '¿Desea firmar el informe seleccionado?', function() {
			//	obtener el PDF mediante AJAX (se obtiene ya en base64)
	
			$.ajax({
				type: 'GET',
				url: Endotools.informes.resource + '/' + informe_id + '.pdfb64',
				processData: false,
				contentType: 'text/plain; charset=UTF-8'
			})
			
			.done(function(data) {
//					dataB64 = getBase64FromText(data, 'UTF-8');
//					dataB64 = MiniApplet.getBase64FromText(data);
				var dataB64 = data;
				
				//	XXX	estos valores han de ser configurables...
				//	ademas se ha de filtrar los tipos de certificados a mostrar, y ver si se indica
				//	un tipo de almacén explicito (esto en la llamada a la función "cargarMiniApplet()"
				//	de main.html)
				var formato = 'Adobe PDF';		//	posibles valores: CAdES, Adobe PDF, XAdES, ODF
				var algoritmo = 'SHA1withRSA';	//	posibles valores: SHA1withRSA, SHA256withRSA, SHA384withRSA, SHA512withRSA
				var extraparams = '';

				//	firmar (el resultado está en base64)
				var resultado_firmado = MiniApplet.sign(dataB64, algoritmo, formato, extraparams);
				
				//	enviar al servidor...
			})
			
			.fail(function() {
				Endotools.statusbar.mostrar_mensaje("Ha ocurrido un error obteniendo el informe PDF para firmarlo", 1);
			});
			
		});
		
	}*/
	
	
	,preview_firmar_y_enviar: function(exploracion_id, plantilla, comentarios) {
		/*
		obtener una preview de informe, mostrarlo, firmarlo y enviarlo al servidor.
		Devuelve un promise que se resuelve si todo va bien.
		*/
		var $dialog;		
		var requiring = $.Deferred();
		
		//	22/2/2015: Se quita el RequireJS y los modulos. Se ha cargado ya en el main.html
//		require(['/lib/pdfobject/pdfobject.js'], function() { requiring.resolve() });
		requiring.resolve();
		//////////////

		return requiring.promise()
		
		.then(function() {
			//	Obtener la previsualización PDF en base64
			cargando.show("test");
			return $.ajax({
				type: 'GET'
				,url: Endotools.exploraciones.resource + '/' + exploracion_id + '/informes/_FIRMAR.json?plantilla=' + plantilla
				,processData: false
				,contentType: 'text/plain; charset=UTF-8'
				,cache: false
				,success:function(data){cargando.hide("test"); return data}
			}).fail(function(data){
				Endotools.statusbar.mostrar_mensaje(parseError(data.responseText), 1);
				cargando.hide("test");
			})
		})
			
		.then(function(informe_json) {
			//	Mostrar la previsualización al usuario y esperar que pulse el botón "Firmar y guardar" para firmarlo y continuar
			var firmando = $.Deferred();
			cargando.show("preview");
//			var $dialog =
			$dialog =
				$('<div id="dialog-preview-informe" title="' + _('Previsualización del informe') + '" />');/*IDIOMAOK*/
			$dialog.dialog({
				width: 800,
				height: 600,
				modal: true,
				resizable: true,
				close: function() {
					firmando.reject();
					$(this).remove();	//ademas se encarga de eliminar el jquery-ui dialog automaticamente (destroy)
				},

				focus:function(){
					cargando.hide("preview");
				},
				
				buttons: [{
					text: _('Firmar y guardar'),/*IDIOMAOK*/
                    click: function () {
                        if (informe_json.hasOwnProperty('operationId')) {
                            var pdfb64_firmado_promise= viafirma.firmar(informe_json);
                            pdfb64_firmado_promise.then(function(pdfb64_firmado){
	                            if (pdfb64_firmado) {
	                            	firmando.resolve(pdfb64_firmado);
	                            }
                         	});
                         	pdfb64_firmado_promise.fail(function() {
								//	cerrar el dialog (como el promise de firmando ya se ha resuelto, no se puede reintentar)
								$dialog.dialog("close");
							});
                        }
                        else {
						    pdfb64_firmado = firma_electronica._firmar(informe_json.b64pdf);
						    if (pdfb64_firmado) {
							    firmando.resolve(pdfb64_firmado);
							    //$(this).dialog("close");
                                }
                        }
					}
				}, {
					text: _('Cancel'),/*IDIOMAOK*/
					click: function() {
						$(this).dialog("close");
					}
				}]
			});
		
			/*var myPDF = new PDFObject({
				// Solo funciona si se le pasa una URL y no un data:application/pdf;base64
			  	url: Endotools.exploraciones.resource + '/' + exploracion_id + '/informes/_PREVIEW.pdf?uuid=' + informe_json.uuid,
			  	id: "dialog-preview-informe-pdf", width: "100%", height: "100%",
			  	pdfOpenParams: {view: "FitH", scrollbar: 1, navpanes: 0, statusbar: 0, toolbar: 0}
			}).embed("dialog-preview-informe");
			*/
			pdfViewerOptions = {
					width: "100%", 
					height: "100%",
					id: "dialog-preview-informe-pdf",
					pdfOpenParams: {view: "FitH", scrollbar: 1, navpanes: 0, statusbar: 0, toolbar: 0}
			}

			PDFObject.embed(Endotools.exploraciones.resource + '/' + exploracion_id + '/informes/_PREVIEW.pdf?uuid=' + informe_json.uuid, $dialog, pdfViewerOptions);

			return firmando.promise();
		})
			
		.then(function(pdfb64_firmado) {
			//no es posible envia
			var data = {
					'exploracion_id': exploracion_id,
					'plantilla': plantilla,
					'comentarios': comentarios,
					'tipo': 1
			}

			//si el parametro pdfb64_firmado tiene la propiedad binaryPdf implica que es un documento binario
			//si no, se trata de un documento en base64
			if (pdfb64_firmado.hasOwnProperty('binaryPdf')) {
				//para enviar el fichero + los paramentros, utilizamos un multipart form.
				//de esta forma podemos enviar un fichero en binario sin problema

				$dialog.append('<input id="fileupload" type="file" name="files" >')
				$("#fileupload").fileupload();
				var jqXHR = $("#fileupload").fileupload('send', {url: Endotools.informes.resource,
				dataType: 'xml',
                formData:[
                			{
                            	name: 'exploracion_id',
                                value: exploracion_id
                            },
                            {
                            	name: 'plantilla',
                                value: plantilla
                            },
                            {
                            	name: 'comentarios',
                                value: comentarios
                            },
                            {
                            	name: 'tipo',
                                value: 1
                            },
                            {
                            	name: 'firma',
                                value: 'viafirma'
                            },
                        ],

					 files: pdfb64_firmado.binaryPdf

				})
				return jqXHR
				
			}
			else{
				data['pdf']=pdfb64_firmado;
				//	Se ha firmado el informe. enviarlo al servidor
				var enviando = $.ajax({
					type: 'POST'
					,url: Endotools.informes.resource
					,data: data
					,cache: false
				})
				.fail(function() {
					alert(_('Ha ocurrido un error guardando el informe firmado'));/*IDIOMAOK*/
					//	cerrar el dialog (como el promise de firmando ya se ha resuelto, no se puede reintentar)
					$dialog.dialog("close");
				});
			
			return enviando;
			}

			
		})
			
		.then(function(data, textStatus, jqXHR) {
			//	cerrar el dialog
			$dialog.dialog("close");
			//	Se ha enviado al servidor, devolver el id del nuevo informe
			return $(data).find('informe').attr('id');
		});
			
		
	}	

  }

}();