/* ---------------------- */
/* ESTE ES EL VISOR NUEVO */
/* V >= 2.4.9.1 --------- */
var imagenes_expl = function () {

	return {

		tm: TM,						// Por defecto el principal, por si no se asigna ninguno
		hay_sin_finalizar: false, 	// True cuando hay imagenes sin finalizar / False cuando no hay
		viewer_div: null,			// El div del visor viewerjs
		viewer_js: null,			// El objeto instanciado del viewerjs
		imagenes: null,				// La ultima respuesta de imagenes del rest
		exploracion_id: null, 		// La exploracion_id sobre la que se estan obteniendo las imagnes
		// Solo informativo para hacer o no la precarga
		precarga: false,			// Realiza la precarga del visor antes de hacer doble click en la imagen
		// para que genere el visor antes de que el usuario ingrese y no cuando
		// hace doble click. Con la variable exploracion_id ya alcanzaria para hacer la
		// precarga pero asi es mas claro a la hora de leer el codigo.


		set_transactionmanager: function (tm) {
			imagenes_expl.tm = tm;
		},

		update_check_btn: function ($input) {
			//	sincroniza el icono de los inputs tipo checkbox de selección de las imágenes con el estado (checked/unchecked)
			if ($input.prop('checked')) {
				$input.button('option', 'icons', { primary: 'ui-icon-check' });
			} else {
				$input.button('option', 'icons', { primary: null });
			}
		},

		find_image_data_by_id: function (id) {
			for (var n = 0; n < imagenes_expl.imagenes.length; n++) {
				if (imagenes_expl.imagenes[n].id == id.toString()) {
					return imagenes_expl.imagenes[n];
				}
			}
		},

		set_comment_to_image_data_by_id: function (id, comment) {
			for (var n = 0; n < imagenes_expl.imagenes.length; n++) {
				if (imagenes_expl.imagenes[n].id == id.toString()) {
					imagenes_expl.imagenes[n].commentario = comment;
					return;
				}
			}
		},

		set_selected_to_image_data_by_id: function (id, selected) {
			for (var n = 0; n < imagenes_expl.imagenes.length; n++) {
				if (imagenes_expl.imagenes[n].id == id.toString()) {
					imagenes_expl.imagenes[n].seleccionada = selected;
					return;
				}
			}
		},

		// Construye la estructura DOM para hacer el visor
		construir_viewer: function () {

			// Contenedor del viewerjs. El tamaño es 0px x 0px porque solo se usa la funcionalidad del lightbox.
			if (imagenes_expl.viewer_div == null) {
				var container = $("#viewerjs-container");
				if (container.length == 0) {
					// no existia, entonces lo creo
					imagenes_expl.viewer_div = $('<div id="viewerjs-container" style="display:block; height:0px; width:0px; overflow:hidden;"><ul id="viewerjs"></ul></div>');
					$("body").append(imagenes_expl.viewer_div);
				} else {
					// ya existia, reasigno
					imagenes_expl.viewer_div = container;
				}
			}

			// vaciarlo
			imagenes_expl.viewer_div.children("ul").html("");

			// popularlo con imagenes, ordenadas como estan en las miniaturas,
			// de esta forma cuando el usuario ordene, se reordenada el viewer
			$(".li-type-image").each(function (index) {
				// obtiene los datos de las imagenes
				imagen = $(this).children("a").data("imagen");

				var multimedia = imagenes_expl.get_multimedia(imagen);
				// si no es video crea la imagen

				if (multimedia.type == "image") {
					// crea el li del viewer y lo agrega al UL

					$viewer_li = $('<li id="viewer-li' + imagen.id + '" class="' /*+ disponible_class*/ + '"></li>')
						.appendTo(imagenes_expl.viewer_div.children("ul"));

					var comentario = " ";//= _("Comentario") + ': ';//IDIOMAOK
					if (imagen.comentario) {
						comentario = comentario + imagen.comentario;
					} else {
						//comentario = comentario + "-";
					}
					$viewer_li.append('<img data-id="' + imagen.id + '" alt="' + comentario + '" src="' + multimedia.url + '" />');//IDIOMAOK
				}


			});

			// Actualiza la instancia del ViewerJS o lo crea si no existe
			if (imagenes_expl.viewer_js) {
				imagenes_expl.viewer_js.update();
			} else {
				//inicializar el visor
				options = {
					'rotatable': false,
					'transition': false,
					'zIndex': 95, // asi queda debajo del dialog del comentario
					'fullscreen': false,
					'minZoomRatio': 0.4,
					'hide': function (event) {
						var id_seleccionada = imagenes_expl.viewer_js.images[imagenes_expl.viewer_js.index].attributes["data-id"].nodeValue;
						$(".endosys-imagen-container").css("background-color", "transparent");
						// $("#captura" + id_seleccionada + "").css("background-color", "#ec948d");
					},
					'viewed': function (event) {

						var image_id = event.detail.originalImage.attributes["data-id"].nodeValue;
						var imagen = imagenes_expl.find_image_data_by_id(image_id);
						//Agrega el boton de comentario
						$(".viewer-comment").remove();
						var comment_btn = $('<li data-id="' + image_id + '" class="viewer-comment" data-action="comment"><i class="fa fa-comment"></i></li>');
						comment_btn.click(function () {
							imagen = imagenes_expl.find_image_data_by_id(image_id);
							imagenes_expl.abrir_dialog_comentario(imagen);
						})
						comment_btn.appendTo(".viewer-toolbar");

						//Agrega el boton de agregar al informe
						$(".viewer-add-to-report").remove();
						var report_btn = $('<li data-id="' + image_id + '" class="viewer-add-to-report" data-action="add-to-report"><i class="fa fa-file"></i></li>');
						if (imagen.seleccionada) {
							report_btn.addClass("imagen-seleccionada");
						}
						report_btn.click(function () {
							imagen = imagenes_expl.find_image_data_by_id(image_id);
							$input_checkbox = $('#imagen-checkbox-' + imagen.id);
							$input_checkbox.prop("checked", (!imagen.seleccionada));
							$input_checkbox.change();
							//imagenes_expl.set_selected_to_image_data_by_id(imagen.id, !imagen.seleccionada);
							//imagenes_expl.update_check_btn($input_checkbox);
							report_btn.toggleClass("imagen-seleccionada");
						})
						report_btn.appendTo(".viewer-toolbar");

					}
				};
				imagenes_expl.viewer_js = new Viewer(document.getElementById('viewerjs'), options);

				// activa la funcionalidad de que si se hace click feuera de la imagen
				// en la seccion gris transparente se sale del visor
				$("body").on("click", ".viewer-canvas", function (e) {
					imagenes_expl.viewer_js.hide();
				});
				$("body").on("click", ".viewer-move", function (e) {
					// para que el hide del visor no afecte al click de la imagen
					e.stopPropagation();
				});
			}






		},

		// Devuelve informacion del multimedia, si es image o video y la url correspondiente
		get_multimedia: function (imagen) {
			var multimedia = { 'type': null, 'url': null };

			// es mpg
			if ((imagen.tipo) && (imagen.tipo.toUpperCase() == 'MPG')) {
				url = Endosys.imagenes.resource + '/' + imagen.id + '.mpg';
				multimedia.url = url;
				multimedia.type = "video";
				return multimedia;
			}
			// es ts
			if ((imagen.tipo) && (imagen.tipo.toUpperCase() == 'TS')) {
				url = Endosys.imagenes.resource + '/' + imagen.id + '.ts';
				multimedia.url = url;
				multimedia.type = "video";
				return multimedia;
			}
			// es avi
			if ((imagen.tipo) && (imagen.tipo.toUpperCase() == 'AVI')) {
				url = Endosys.imagenes.resource + '/' + imagen.id + '.avi';
				multimedia.url = url;
				multimedia.type = "video";
				return multimedia;
			}

			// es wmv
			if ((imagen.tipo) && (imagen.tipo.toUpperCase() == 'WMV')) {
				url = Endosys.imagenes.resource + '/' + imagen.id + '.wmv';
				multimedia.url = url;
				multimedia.type = "video";
				return multimedia;
			}

			// sino es imagen
			multimedia.url = Endosys.imagenes.resource + '/' + imagen.id + '.' + imagen.tipo;
			multimedia.type = "image";
			return multimedia;
		},


		// muestra imagen o  con su visor, y si es video abre llama a la funcion de mostrar video con
		// el popup para descargar
		mostrar_imagen: function () {

			// Datos de la imagen
			var imagen = $(this).children("a").data("imagen");
			if (imagen.disponible == false) {
				alert(_("Imagen no disponible en este momento."));//IDIOMAOK
				return;
			}


			// construye el viewer
			imagenes_expl.construir_viewer();

			// saca el foco del tab para que cuando en el visor se usan las flechas no se
			// cambien los tabs en el fondo.
			$(".ui-tabs-nav li a").blur();

			// obtiene el multimedia
			var multimedia = imagenes_expl.get_multimedia(imagen);

			// Obtiene el indice de la imagen que se quiere abrir para abrir esa en el visor
			// solo las del mismo tipo para que no se mezcle
			var index = $(".li-type-" + multimedia.type).index($(this));

			//mostrar imagen
			imagenes_expl.viewer_js.show();
			imagenes_expl.viewer_js.view(index);


		},

		// Muestra el dialogo del video para descargar
		mostrar_video: function () {

			var imagen = $(this).children("a").data("imagen");
			if (imagen.disponible == false) {
				alert(_("Video no disponible en este momento."));//IDIOMAOK
				return;
			}


			var multimedia = imagenes_expl.get_multimedia(imagen);

			controles.modal_dialog.mostrar({
				title: _('Descargar Video'),/*IDIOMAOK*/
				width: 400,
				height: "auto",
				buttons: { Aceptar: _("Descargar") },/*IDIOMAOK*/
				resizable: true,
				enterAccept: false,

				result: function () {
					window.open(multimedia.url);
				},

				init: function (accept) {
					this.append('<p style="font-size:11px; font-style:italic">' +
						_("Descargue el video en su ordenador y utilice un reproductor para visualizarlo (Windows Media Player o VLC)")//IDIOMAOK
						+ '</p>');
					comentario = "<strong>" + _("Comentario") + ': </strong>' + (imagen.comentario || "-"); //IDIOMAOK
					this.append(comentario);
				}
			});
		},


		// Muestra el dialogo del comentario para editarlo
		abrir_dialog_comentario: function (img_data) {

			// 2 modos de obtener la imagen
			// 1 - que se le pase por parametro img_data
			// 2 - si no viene por parametro, que lo busque en el .data del objeto que llama a la fnc

			var thumb;
			var imagen;
			if (img_data.id != undefined) {
				imagen = img_data;
				thumb = $("#btn-comentario-" + img_data.id);
			} else {
				thumb = $(this);
				console.log(thumb);
				imagen = thumb.data("imagen");
			}

			controles.modal_dialog.mostrar({
				title: _('Ingresar comentario'),/*IDIOMAOK*/
				width: 400,
				height: "auto",
				buttons: { Aceptar: _("Guardar") },/*IDIOMAOK*/
				resizable: true,
				enterAccept: true,

				result: function () {
					return $("#comentario-imagen").val();
				},

				init: function (accept) {

					this.append(
						'<form class="pure-form">' +
						'<input id="comentario-imagen" class="pure-input-1" placeholder="' + _('Comentario') + '">' +/*IDIOMAOK*/
						'</form>');

					if (imagen.comentario) {
						$("#comentario-imagen").focus().val("").val(imagen.comentario);
					}

				}

			})
				.done(function (comentario) {
					if (comentario != imagen.comentario) {
						Endosys.imagenes.update(imagenes_expl.tm, imagen.id, { 'comentario': comentario })
							.done(function () {
								imagen.comentario = comentario;
								// actualiza el objeto data del thumb
								thumb.data("imagen", imagen);
								//actualiza el viewer title del visor
								$(".viewer-title").html(imagen.comentario);
								imagenes_expl.set_comment_to_image_data_by_id(imagen.id, comentario)
							});
					}
				});

		},


		/**
		 * Obtiene las miniaturas de las imagenes capturadas
		 *
		 * @param {int} exploracion_id - La exploracion sobre la cual se quieren obtener las miniaturas
		 * @param {JQuery DOMObject} $parent - El div donde se insertaran las miniaturas
		 *
		 */
		obtener_thumbs: function (exploracion_id, $parent) {

			// Obtiene las miniaturas al REST
			Endosys.imagenes.index(imagenes_expl.tm, { 'exploracion_id': exploracion_id })
				.done(function (imagenes) {
					imagenes_expl.imagenes = imagenes;

					// Ordena el array de imagenes por el campo orden ascendentemente
					imagenes.sort(function (x, y) { return Number(x.orden) - Number(y.orden) });

					imagenes_expl.hay_sin_finalizar = false; // antes de recorrer setea si hay sin finalizar en false

					// Inserta las imagenes obtenidas del rest al $parent
					for (var n = 0; n < imagenes.length; n++) {

						var imagen = imagenes[n];
						var disponbile;
						var thumb_src;
						var img_src;
						var disponible_class = "";
						var $container;

						multimedia = imagenes_expl.get_multimedia(imagen);

						// Si no existe el atributo disponible o si esta disponibles => Disponible
						if (imagen.disponible == undefined || imagen.disponible) {
							disponible = true;
							thumb_src = Endosys.imagenes.resource + '/' + imagen.id + '.thumb';
							img_src = multimedia.url;
							disponible_class = " img-disponible ";

						} else {
							// Si la imagen no esta disponible pueden pasar dos cosas.
							// 1. este en el pacs, tiene dicom_stgcmt=1
							// 2. este subiendose por el ewc, no tiene dicom_stgcmt=1

							//La imagen no esta disponible, el thumb será un loading
							disponible = false;
							imagenes_expl.hay_sin_finalizar = true; // si encuentra alguna sin finalizar pone en true
							thumb_src = "/webapp/assets/unused/loading-big.gif";
							img_src = thumb_src;
						}

						// Estructura de la imagen es: li > a > img
						// Verifica si existe
						$container_li = $('#captura' + imagen.id);

						//$viewer_li = $('#viewer-li'+imagen.id);

						if ($container_li.length > 0) {
							//Si no tiene la clase img-disponible tengo actualizar su estado.
							if (!($container_li.hasClass("img-disponible"))) {
								// Si la imagen agrega la clase
								if (imagen.disponible) {
									$container_li.addClass("img-disponible");

								}
							}
						} else {

							// Si no existia el LI entonces lo crea. Esto lo hace 1 sola vez
							$container_li = $('<li id ="captura' + imagen.id + '" class="endosys-imagen-container' +
								' li-type-' + multimedia.type +
								' ' + disponible_class + '"></li>')
								.appendTo($parent);

							// Le asigna el evento click para que funcione la seleccion y la flecha.
							$container_li.click(function () {

								var id_flecha = $(this).attr("id").replace("captura", "flecha");
								// Existe la flecha¿?
								if ($("#" + id_flecha + "").length > 0) {
									$("#" + id_flecha + "").click();
								} else {
									// En el caso de que la imagen no disponga de una flecha se ha
									// de marcar la imagen como seleccionada y deseleccionar todas las fleclas
									imagenes_expl.inicializar_seleccion();

									// Seleccionar la imagen que le han hecho click
									// $(this).css("background-color", "#ec948d");
								}

							});
						}

						//	Añadir un elemento 'img' por cada imagen, con un link que con dblclick la muestra
						if ($container_li.html().length > 0) { //Es una imagen existente

							// actualiza los elemntos existentes
							$container_li.children("a").children("img").attr("src", thumb_src);
							$container_li.children("a").data("imagen", imagen);
							//$viewer_li.children("img").attr("src", multimedia.url);

						} else { // es una imagen nueva

							var $img_link = $('<a href="#"></a>')
								.appendTo($container_li)
								.data('imagen', imagen)
								.append($('<img src="' + thumb_src + '" class="endosys-imagen"></img>'));


							//$viewer_li.append('<img src="'+img_src+'" />')

							//	crear el boton check, para seleccionar para informe
							// var $checkbtn = $('<input type="checkbox">')
							// 	.attr('id', 'imagen-checkbox-' + imagen.id)
							// 	.after($('<label/>').attr('for', 'imagen-checkbox-' + imagen.id))
							// 	.appendTo($container_li)
							// 	.data('imagen', imagen)
							// 	.button({ text: false })
							// 	.prop('checked', imagen.seleccionada)
							// 	.change(function () {
							// 		var $checkbox = $(this);
							// 		if ($checkbox.parent().hasClass('li-type-image') || !$checkbox.prop('checked')) {
							// 			imagenes_expl.update_check_btn($checkbox);
							// 			Endosys.imagenes.update(imagenes_expl.tm, $checkbox.data('imagen').id, {
							// 				'seleccionada': $checkbox.prop('checked') ? '1' : '0'
							// 			}).done(function () {
							// 				imagenes_expl.set_selected_to_image_data_by_id($checkbox.data('imagen').id, $checkbox.prop("checked"));
							// 			});
							// 		}
							// 		else {
							// 			Endosys.statusbar.mostrar_mensaje(_("Sólo puede añadir imágenes a la generación de informes"), 1);
							// 			$checkbox.prop('checked', false);
							// 		}
							// 	});

							// imagenes_expl.update_check_btn($checkbtn);

							//	crear el boton comentar
							var $commentbtn = $(`<button class="icon-button icon-button-primary comentariobtn">
							<svg xmlns="http://www.w3.org/2000/svg" aria-hidden="true" role="img" width="1em" height="1em" preserveAspectRatio="xMidYMid meet" viewBox="0 0 512 512"><path fill="currentColor" d="M256 32C114.6 32 0 125.1 0 240c0 49.6 21.4 95 57 130.7C44.5 421.1 2.7 466 2.2 466.5c-2.2 2.3-2.8 5.7-1.5 8.7S4.8 480 8 480c66.3 0 116-31.8 140.6-51.4c32.7 12.3 69 19.4 107.4 19.4c141.4 0 256-93.1 256-208S397.4 32 256 32z"/></svg>
							</button>`)
								.attr('id', 'btn-comentario-' + imagen.id)
								.appendTo($container_li)
								.button({ text: false })
								.data('imagen', imagen)
								.click(imagenes_expl.abrir_dialog_comentario);

							var $deletetbtn = $(`<button class="icon-button icon-button-alert deletebtn" style="display:none !important;">
							<svg xmlns="http://www.w3.org/2000/svg" aria-hidden="true" role="img" width="1em" height="1em" preserveAspectRatio="xMidYMid meet" viewBox="0 0 1024 1024"><path fill="currentColor" d="M864 256H736v-80c0-35.3-28.7-64-64-64H352c-35.3 0-64 28.7-64 64v80H160c-17.7 0-32 14.3-32 32v32c0 4.4 3.6 8 8 8h60.4l24.7 523c1.6 34.1 29.8 61 63.9 61h454c34.2 0 62.3-26.8 63.9-61l24.7-523H888c4.4 0 8-3.6 8-8v-32c0-17.7-14.3-32-32-32zm-200 0H360v-72h304v72z"/></svg>
							</button>`)
								.attr('id', 'btn-delete-' + imagen.id)
								.appendTo($container_li)
								.button({ text: false })
								.data('imagen', imagen)
								.click(( ) => $(`#captura${imagen.id}`).remove());


							if (imagen.posx && imagen.posy) {
								imagenes_expl.pintar_flecha($('#exploracion_form_tabview #exploracion-tab-imagenes>.ui-layout-east'), imagen, imagen.posx, imagen.posy);
							}
						}

					}
					refresh_imagenes.set_sumar_intentos(imagenes_expl.hay_sin_finalizar);

					//si nunca se hizo una precarga, entonces la hace
					/*if (imagenes_expl.precarga == false){
						imagenes_expl.exploracion_id = exploracion_id;
						if (imagenes_expl.imagenes.length>0){
							imagenes_expl.construir_viewer();
							imagenes_expl.precarga = true;
						}
					}else{
						// es una exploracion nueva, hay que realizar la precarga nuevamente
						if (imagenes_expl.exploracion_id != exploracion_id){
							imagenes_expl.precarga = false;
							imagenes_expl.exploracion_id = exploracion_id;
							imagenes_expl.construir_viewer();
							imagenes_expl.precarga = true;
						}
					}*/

					// Genera los eventos para abrir las imagenes.
					$("body").off("dblclick", ".li-type-image", imagenes_expl.mostrar_imagen);
					$("body").on("dblclick", ".li-type-image", imagenes_expl.mostrar_imagen);

					$("body").off("dblclick", ".li-type-video", imagenes_expl.mostrar_video);
					$("body").on("dblclick", ".li-type-video", imagenes_expl.mostrar_video);
					// --- Finaliza el for que agrega o actualiza las imagenes


					$parent.sortable({

						scroll: true,
						stop: function (event, ui) {
							if (gestion_exploraciones._MOUSE_EN_GRAFICO) {
								$parent.sortable("cancel");

								// Datos de la imagen
								var imagen = ui.item.find("a").data("imagen");

								//Obtener la posicion
								var $contenedor = $('#exploracion_form_tabview #exploracion-tab-imagenes>.ui-layout-east');
								var position = $contenedor.offset();
								var posX = Math.floor(event.pageX - position.left) - 24;
								var posY = Math.floor(event.pageY - position.top) - 30;

								// Grabar la posicion en la BD
								Endosys.imagenes.update(imagenes_expl.tm, imagen.id, { 'posx': posX, 'posy': posY })
									.done(function () {
										// Cuando se graba la posicion, pintar flecha
										imagenes_expl.pintar_flecha($contenedor, imagen, posX, posY);
									});

							}
						}
					}).disableSelection();

				});
		},

		pintar_flecha: function ($contenedor, imagen, posX, posY) {

			var seleccionada = false;

			//verificamos si la flecha que vamos a dibujar ya existe
			var $flecha_existente = $('#exploracion_form_tabview #exploracion-tab-imagenes>.ui-layout-east').find("#flecha" + imagen.id + "");
			if ($flecha_existente.length > 0) {
				//SI que existe la flecha

				//si la flecha que vamos a dibujar estaba en rojo la tendremos que dibujar en rojo
				if ($flecha_existente.attr("src") == "/res/flecha_grafico_seleccionada.png") {
					seleccionada = true;
				}

				//si existe la eliminamos y luego se volvera a crear
				$flecha_existente.remove();

			} else {
				//no existe la flecha
				//si la flecha no existe y la captura esta seleccionada se ha de pintar la flecha tambien seleccionada
				if ($("#captura" + imagen.id + "").css("background-color") != "transparent") {
					seleccionada = true;
				}

			}


			var link = "/res/flecha_grafico.png";
			if (seleccionada) {
				link = "/res/flecha_grafico_seleccionada.png";
			}

			var $flecha = $('<img id="flecha' + imagen.id + '" class="flecha" src="' + link + '" style="position: absolute;">');
			$flecha.css('left', posX + 'px');
			$flecha.css('top', posY + 'px');
			$flecha.data('imagen', imagen);
			$contenedor.append($flecha);
			$flecha.draggable({
				containment: "#exploracion_form_tabview #exploracion-tab-imagenes>.ui-layout-east>div",
				scroll: false,
				stop: function () {
					Endosys.imagenes.update(imagenes_expl.tm, $(this).data("imagen").id, { 'posx': this.x, 'posy': this.y });
				}
			});
			$flecha.click(function () {

				imagenes_expl.inicializar_seleccion();

				//seleccionar la flecha
				$(this).attr("src", "/res/flecha_grafico_seleccionada.png");
				//seleccionar su captura correspondiente
				$("#captura" + $(this).data("imagen").id + "").css("background-color", "#ec948d");

			});
		},
		inicializar_seleccion: function () {
			//funcion para desmarcar todas las captura y flechas seleccionadas en pantalla

			//deseleccionar todas las imagenes/capturas
			$('.endosys-imagen-container').each(function (index, el) {
				$(el).css("background-color", "transparent");
			});

			//deseleccionar todas flechas
			$('#exploracion_form_tabview #exploracion-tab-imagenes>.ui-layout-east').find("img").each(function (index, el) {
				if ($(el).attr("id") != "papelera") {
					$(el).attr("src", "/res/flecha_grafico.png");
					//$("#captura"+$(el).data("imagen").id+"").css("background-color", "transparent");
				}

			});


		}


	}


}();



/* Controla la busqueda de nuevas imaganees de captura
   Se configura para que se ejecute cada XX segundos
   EWC_MODO.ACTIVO == 1
*/
//Antes estaba en misc.js
var refresh_imagenes = function () {

	return {

		interval: null,
		intentos_capturas_todas_disponibles: 0, // suma los intentos en que las capturas que se pidieron
		// fueron todas disponibles

		exploracion_estado: 0, //de acuerdo al estado se realizan algunas acciones
		// por cada peticion al rest de imagenes, se ejecuta esta funcion cuando se termina de recorrer el for que recorre
		// las capturas, si todas estan finalizadas se suma un intento, a los 10 intentos, se para el interval
		set_sumar_intentos: function (hay_sin_finalizar) {
			if (refresh_imagenes.exploracion_estado != 0) {
				if (hay_sin_finalizar == false) {
					refresh_imagenes.intentos_capturas_todas_disponibles += 1;
				}
				if (refresh_imagenes.intentos_capturas_todas_disponibles >= 10) {
					refresh_imagenes.terminar();
					refresh_imagenes.intentos_capturas_todas_disponibles = 0;
				}
			}
		},


		set_exploracion_estado: function (exploracion_estado) {
			refresh_imagenes.exploracion_estado = exploracion_estado;

			//Refrescar del ENDOSYSWEBCLIENT
			//if (opciones_config["EWC_MODO.ACTIVO"]==1){
			if (refresh_imagenes.exploracion_estado == 0) {
				// Si tiene estado sin finalizar
				refresh_imagenes.comenzar(refresh_imagenes.exploracion_estado);
			} else {
				// Se fija si hay imagenes sin finalizar
				if (imagenes_expl.hay_sin_finalizar) {
					refresh_imagenes.comenzar(refresh_imagenes.exploracion_estado);
				}
			}
			//}else{
			// cancelar refresco porque no esta activado el modo ENDOSYSWEBCLIENT
			//	refresh_imagenes.terminar();
			//}

		},

		comenzar: function (exploracion_estado) {

			imagenes_expl.set_transactionmanager(TM.content_exploraciones.detalles.imagenes);

			console.log("comenzar hilo de busqueda de imagnes")

			Endosys.imagenes.index(imagenes_expl.tm, { 'exploracion_id': gestion_exploraciones.exploracion_id })
				.done(function (imagenes) {
					for (var n = 0; n < imagenes.length; n++) {
						console.log(imagenes[n]);
						// esta en el pacs, hago un llamado al show para obtenerla
						if (!imagenes[n].disponible && imagenes[n].dicom_stgcmt) {
							console.log(imagenes[n].id);
							Endosys.imagenes.show(imagenes_expl.tm, imagenes[n].id, { 'format': imagenes[n].tipo })
								.done(function (imagen) {
									console.log("cargo la imagen desde el pacs");
								}).fail(function (text) {
									console.log(text);
								});
						}
					}

				}).then(function () {
					refresh_imagenes.exploracion_estado = exploracion_estado.toString();

					//Comienza un intervalo
					if (refresh_imagenes.interval == null) {
						imagenes_expl.obtener_thumbs(gestion_exploraciones.exploracion_id, $('#exploracion-tab-imagenes>.ui-layout-center>ul'));

						refresh_imagenes.interval = setInterval(function () {
							//solo hace el refresco si esta el tab disponible
							if ($("#exploracion-tab-imagenes").length) {
								imagenes_expl.obtener_thumbs(gestion_exploraciones.exploracion_id, $('#exploracion-tab-imagenes>.ui-layout-center>ul'));
							} else {
								// sino cancela
								refresh_imagenes.terminar();
							}

						}, 2000);
					}
				});
		},

		terminar: function () {
			clearInterval(refresh_imagenes.interval);
			refresh_imagenes.interval = null;
		}

	}

}();
