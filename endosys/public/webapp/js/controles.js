/*
OJO:
-Solo puede mostrarse un dialog de cada tipo simultaneamente, ya que
 no se generan Ids.
 
TODO:
-Hacer los dialogs como el "confirm_dialog", sin funcion mostrar(), que sean
 directamente una funcion.
*/


//	además se inicializa un plugin de jquery-ui, "ettabs", que
//	toma como base "tabs" y añade el metodo "add()"

//	$.ui.ettabs
/*(function($, undefined) {
    $.widget('ui.ettabs', $.ui.tabs, {
        add: function() {
			alert('add tab!');
		}
    });

    $.extend($.ui.ettabs, {version:'v0.1'});
})(jQuery);*/

//	NECESARIO PARA jQueryUI >= 1.10 ¿?
//	expandir $.ui.tabs
$.ui.tabs.prototype.add = function(id, title) {
	//	xxx	hacer que se pueda pasar el contenido ya creado
	var li = $("<li> <a href='#" + id + "'>" + title + "</a> </li>");
	this.element.find(".ui-tabs-nav").append(li);
	$content = $("<div id='" + id + "' />");
	this.element.append($content);
}


var controles = function() {

	return {
	
		init_YUI_datatable: function(datatable, options) {
			/*
			Inicializa un objeto DataTable de YUI 2:
				-Asigna eventos de mouse hover
				-Cambia un color del fondo del header que no se puede por CSS
				-Opcionalmente, permite cambiar el tamaño (el alto) automáticamente
				 para que se ajuste a un panel de un ui-layout
			
			datatable:
				El objeto DataTable de YUI que se quiere inicializar.
				
			options:
				layoutPaneResizing		Si se indica una pane del layout, se cambiará el
										alto de la tabla en el evento resize para ocupar
										hasta abajo del pane. Ha de ser un objeto jQuery.
			*/
			/*
			COMPATIBILIDAD CON IE 9 se ha de pasar un height en las propiedades del datatable
			si no se visualiza mal			
			*/
			datatable.subscribe("rowMouseoverEvent", datatable.onEventHighlightRow);
			datatable.subscribe("rowMouseoutEvent",  datatable.onEventUnhighlightRow);
			//	obtener el color del fondo del header definido por CSS y configurar la opción COLOR_COLUMNFILLER
			//datatable.set("COLOR_COLUMNFILLER", "#C4E5D6");
			var colorfondo = $('.yui-skin-endosys .yui-dt th').first().css('background-color')
			datatable.set("COLOR_COLUMNFILLER", colorfondo);
			
			if (options && options.layoutPaneResizing) {
				//	averiguar la posicion del pane en el layout
				var positions = ['center', 'east', 'west', 'north', 'south'];
				var position = '';
				for (var i=0; i<positions.length; i++) {
					if (options.layoutPaneResizing.hasClass('ui-layout-' + positions[i])) {
					position = positions[i];
					break;
					}
				}
				if (!position) throw "Error en controles.js: init_YUI_datatable(): No se ha identificado la posición en el layout del parámetro 'layoutPaneResizing'";
				//	asignar el evento
				options.layoutPaneResizing.parent().layout().options[position].onresize = function() {
					//	datatable._elContainer		--> elemento del Datatable
					//	datatable._elBdContainer    --> el body (que tiene la clase .yui-dt-bd)

					//Se agrega esto para que tenga mas espacio inferior en caso que se desee
					var margin_inferior = 12;
					if (options.m_inferior!=undefined){
						margin_inferior = options.m_inferior;
					}
					
					var h =
						options.layoutPaneResizing.innerHeight()
						- $(datatable._elBdContainer).position().top
						- margin_inferior;	//	margen de abajo
					datatable.set('height', h + 'px');
				}
				//	ejecutar ya un resize por si es necesario
				options.layoutPaneResizing.parent().layout().resizeAll();
			}
			
			return datatable;
		},

		confirm_dialog: function(titulo, prompt, callback_fn, args) {
		
			var deferred = $.Deferred();
			args = args || {};
			var _Si = function() {
				//	this		es el $dialog
				if (callback_fn) callback_fn();
				deferred.resolve();
				$(this).dialog("close");
			}
			
			//	devuelve un promise.
			var $dialog =
				$('<div id="dialog-confirm" title="' + titulo + '">' +
					'<p>' +
						'<span class="ui-icon ui-icon-alert" style="float: left; margin: 0 7px 0 0;"></span>' +
						prompt +
					'</p>' +
				'</div>');
			$dialog
			 .keypress(function(e) {
				if (e.keyCode == $.ui.keyCode.ENTER) _Si.call($('#dialog-confirm'))
			})
			 .dialog({
				//height: 160,
				modal: true,
				resizable: false, 
				width: args.width || 300,
				close: function() {
					$(this).remove();	//ademas se encarga de eliminar el jquery-ui dialog automaticamente (destroy)
					if (deferred.state() == "pending") deferred.reject();
				},
				buttons: [{
					text: _('Sí'),/*IDIOMAOK*/
					click: _Si
				}, {
					text: _('No'),/*IDIOMAOK*/
					click: function() {
						$(this).dialog("close");
					}
				}]
			});
			return deferred.promise();
		},

		input_dialog: {
			/*
			dialog genérico para que el usuario pueda introducir un valor, de forma modal.
			devuelve un promise.
			*/
			_deferred: null,
			
			_Aceptar: function() {
				//	this		es el $dialog
				var nuevo_valor = $('#generic-input-dialog input').val();
				controles.input_dialog._deferred.resolve(nuevo_valor);
				$(this).dialog('close');
			},
			
			mostrar: function(titulo, prompt, valor) {
				if (!$('#generic-input-dialog').length) controles.input_dialog._crear_dialog();
				$('#generic-input-dialog').dialog('option', 'title', titulo);
				$('#generic-input-dialog label').html(prompt);
				$('#generic-input-dialog input').val(valor);
				
				controles.input_dialog._deferred = $.Deferred();
				$('#generic-input-dialog')
				 .one("dialogopen", function() {
					//	no debería ser necesario esto, pero si no parece que el Dialog en algunos casos no pone el focus
					setTimeout(function() { $('#generic-input-dialog input').focus(); }, 0);
				 })
				 .dialog('open');

				return controles.input_dialog._deferred.promise();
			},
			
			_crear_dialog: function() {
				$('<div id="generic-input-dialog" />')
				 .html($(
					'<form class="pure-form pure-form-stacked"  onsubmit="return false">' +
						'<fieldset>' +
						'<label for="generic-input-dialog-valor">' + _('elemento') + '</label>' +/*IDIOMAOK*/
						'<input id="generic-input-dialog-valor" type="text" class="pure-input-1" />' +						
						'</fieldset>' +
					'</form>'
				 ))
				 .appendTo($('body'))
				 .keypress(function(e) {
					if (e.keyCode == $.ui.keyCode.ENTER) controles.input_dialog._Aceptar.call($('#generic-input-dialog'))
				})
				 .dialog({
					resizable: false,
					title: '',
					width: "360px",
					autoOpen: false,
					modal: true,
					close: function() {
						//	si no se ha hecho el resolved() es que no se ha dado
						//	a "Aceptar", asi que se hace el reject()
						if (controles.input_dialog._deferred.state() == "pending")
							controles.input_dialog._deferred.reject();
					},
					buttons: [{
						text: _('Aceptar'),/*IDIOMAOK*/
						click: controles.input_dialog._Aceptar
					}, {
						text: _('Cancelar'),/*IDIOMAOK*/
						click: function() {
							$(this).dialog('close');
						}
					}]
				});
			}

		},

		modal_dialog: {
			/*
			dialog modal genérico para que cualquier uso.
			devuelve un promise.
			*/
			_deferred: null,
			_check: null,
			_enterAccept: null,
			
			_Aceptar: function(param) {
				//	this		es el $dialog
				var $dialog = $(this);
				/*if (controles.modal_dialog._check.call($dialog, $dialog)) {
					controles.modal_dialog._deferred.resolve(
						controles.modal_dialog._result.call($dialog, $dialog, param)
					);
				} else {
					controles.modal_dialog._deferred.reject($dialog);
				}
				$(this).dialog('close');*/
				
				// si no pasa el check, no cierra el dialog
				if (controles.modal_dialog._check.call($dialog, $dialog)) {
					controles.modal_dialog._deferred.resolve(
						controles.modal_dialog._result.call($dialog, $dialog, param)
					);
					$(this).dialog('close');
				}

			},
			
			mostrar: function(args) {
				/*
					args	(opcional) puede contener cualquier option del dialog de jqueryui, y además:
								init	funcion para inicializar el dialog. Recibe como parametro una funcion
										"accept" que se puede llamar para simular que se pulsa Aceptar.
										El valor devuelto se pasará a un $.when(), es decir, puede devolver
										un promise, al que se espera para abrirse el dialog.
										NUEVO: ahora "accept" acepta un argumento, que llegará a "check" y "result" si se usan.
								check	funcion ejecutada al Aceptar, que comprueba que se ha rellenado
										el dialog correctamente.
										El primer argumento es el dialog. XXX: no sirve de nada, es lo mismo que el this. Revisar que no se use y quitar este primer argumento.
										NUEVO: el segundo argumento es opcional y puede venir desde la función "accept" del "init".
								result	funcion ejecutada al Aceptar y pasar el check, que extrae el valor del
										dialog a devolver en el done(). Si no se indica, se devuelve el $dialog.
										El primer argumento es el dialog. XXX: no sirve de nada, es lo mismo que el this. Revisar que no se use y quitar este primer argumento.
										NUEVO: el segundo argumento es opcional y puede venir desde la función "accept" del "init".
								enterAccept	indica si al pulsar Enter desde el dialog se simula el botón
										Aceptar. Por defecto es true.
								buttons	Para configurar los botones. Debe tener el mismo formato que
										el parámetro "buttons" del Dialog como objeto (NO como array), pero si
										se pasa "Aceptar" o "Cancelar", se comporta asi:
										valor null:		quita el botón
										valor string:	renombra el botón
										valor function:	cambia el callback (NO IMPLEMENTADO)
				*/
				args = args || {};
				if (!$('#generic-dialog').length) controles.modal_dialog._crear_dialog();
				var $dialog = $('#generic-dialog');

				//	reset a opciones por defecto
				$dialog.dialog('option', {
					appendTo:		'body',
					closeOnEscape:	true,
					closeText:		_('Cerrar'),/*IDIOMAOK*/
					dialogClass:	'',
					draggable:		true,
					hide:			null,
					maxHeight:		false,
					maxWidth:		false,
					minHeight:		150,
					minWidth:		150,
					position:		{my: "center", at: "center", of: window},	//	OK para jQueryUI >= 1.10
					show:			null,
					resizable:		false,
					title:			'',
					width:			400,
					height:			400,
					autoOpen:		false,
					modal:			true,
					buttons:		[{
						text: _('Aceptar'),/*IDIOMAOK*/
						click: controles.modal_dialog._Aceptar
					}, {
						text: _('Cancelar'),/*IDIOMAOK*/
						click: function() { $(this).dialog('close'); }
					}]
				});
				
				//	Controlar botones
				if (args.buttons) {
					//	también acepta todo minúsculas
					if (args.buttons.aceptar !== undefined) {
						args.buttons.Aceptar = args.buttons.aceptar;
						delete args.buttons.aceptar;
					}
					if (args.buttons.cancelar !== undefined) {
						args.buttons.Cancelar = args.buttons.cancelar;
						delete args.buttons.cancelar;
					}
				
					if (args.buttons.Aceptar === undefined) {
						args.buttons.Aceptar = controles.modal_dialog._Aceptar;
					} else {
						if (args.buttons.Aceptar) {
							if (typeof args.buttons.Aceptar == 'string') {
								var nombrebotonaceptar = args.buttons.Aceptar;
								delete args.buttons.Aceptar;
								args.buttons[nombrebotonaceptar] = controles.modal_dialog._Aceptar;
							}
						} else {
							delete args.buttons.Aceptar
						}
					}
					
					if (args.buttons.Cancelar === undefined) {
						args.buttons.Cancelar = function() { $(this).dialog('close'); };
					} else {
						if (args.buttons.Cancelar) {
							if (typeof args.buttons.Cancelar == 'string') {
								args.buttons[args.buttons.Cancelar] = function() { $(this).dialog('close'); };
								delete args.buttons.Cancelar;
							}
						} else {
							delete args.buttons.Cancelar
						}
					}
					
					//	traducir los botones Aceptar y Cancelar
					if ("Aceptar" in args.buttons) {/*NO TRADUCIR*/
						args.buttons[_('Accept')] = args.buttons.Aceptar;/*IDIOMAOK*/
						delete args.buttons.Aceptar;
					}
					if ("Cancelar" in args.buttons) {/*NO TRADUCIR*/
						args.buttons[_('Cancel')] = args.buttons.Cancelar;/*IDIOMAOK*/
						delete args.buttons.Cancelar;
					}
				}
				
				//	opciones pasadas como args
				$.each(args, function(key, value) {
					if ($.inArray(key, ['autoOpen','buttons','closeOnEscape','closeText','dialogClass',
					'draggable','height','hide','maxHeight','maxWidth','minHeight','minWidth','modal','position',
					'resizable','show','title','width','open']) != -1) {
						$dialog.dialog("option", key, args[key]);
					}
				});
				
				var initializing = undefined;
				if (args.init) initializing = args.init.call($dialog, function(param) { controles.modal_dialog._Aceptar.call($dialog, param) });
				controles.modal_dialog._check = args.check || function() {return true};
				controles.modal_dialog._result = args.result || function() {return $dialog};
				controles.modal_dialog._enterAccept = (args.enterAccept == false) ? false : true;
				controles.modal_dialog._deferred = $.Deferred();

				$.when(initializing)
				.done(function() {
					//	nota: antes de mostrar el dialog se comprueba que no se haya aceptado
					//	ya desde el init(), llamando a accept(). Si se ha hecho, el _deferred ya estará resolved
					if (controles.modal_dialog._deferred.state() == "pending")
						$dialog.dialog('open');
				})
				.fail(function() {
					controles.modal_dialog._deferred.reject($dialog);
				});
				
				return controles.modal_dialog._deferred.promise();
			},
			
			_crear_dialog: function() {
				$('<div id="generic-dialog" />')
				 .appendTo($('body'))
				 .keypress(function(e) {
					if ((e.keyCode == $.ui.keyCode.ENTER) && (controles.modal_dialog._enterAccept))
						controles.modal_dialog._Aceptar.call($('#generic-dialog'))
				 })
				 .dialog({
					resizable: false,
					title: '',
					width: 400,
					autoOpen: false,
					modal: true,
					close: function() {
						if (controles.modal_dialog._deferred.state() == "pending")
							controles.modal_dialog._deferred.reject($(this));
						$(this).html('').removeClass();	//	vaciar y quitar clases adicionales
						$(".ui-dialog-titlebar-close").show(); //vuelve a mostrar el boton de cerrar por si se oculto
						//	XXX	ojo, al crear el dialog se asignan dos clases de jqueryui, asi que las vuelvo a poner...
						$(this).addClass('ui-dialog-content').addClass('ui-widget-content');
					},
					buttons: [{
						text: _('Accept'),/*IDIOMA*/
						click: controles.modal_dialog._Aceptar
					}, {
						text: _('Cancel'),/*IDIOMA*/
						click: function() { $(this).dialog('close'); }
					}]
				});
			}			
		}

	}

}();