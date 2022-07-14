var menu_textos_predefinidos = function() {

	return {

		_crear_menu: function(campo, $parent, target_id) {
			var menu_content =
				'<div class="styled-select">\
								   <select id="predefinido-' + campo.id + '" data-target="' + target_id + '">\
				   </select>\
				 </div>'
			var $menu = $(menu_content).appendTo($parent);
			var $select = $menu.children('select');
			$select.click(function(event){
				// No procesar click si no fue hecho sobre un tag option. Como chrome no registra los
				// clicks sobre options, usamos un valor por defecto como workaround.
				if ((event.target.tagName === 'SELECT' && !$.browser.webkit) ||
						(event.target.tagName === 'SELECT' && $(event.target).val() === "")) {
					return;
				}
				$select = $(event.target);
				if (event.target.tagName != 'SELECT') {
					// Normalizamos chrome con el resto de navegadores.
					$select = $select.parent();
				}
				var predefined_id = $select.val();
				var $target = $('#' + $select.data('target'))
				menu_textos_predefinidos._introducir_texto_predefinido(predefined_id, $target, campo);
				
				$select.val("");
				document.getElementById($select.attr("id")).selectedIndex=-1;
			});

			$select.blur(function(){

				document.getElementById($select.attr("id")).selectedIndex=-1;

			});

			return $menu;
		},
		
		_attach_default_value: function($select) {
			$('<option selected id="predefinido-default" value="">default</option>')
			.appendTo($select).hide();
		},

		_introducir_texto_predefinido: function(predefined_id, $target, campo) {
			/*	  Descarga el contenido del texto predefinido y lo inserta en el textfield $target.
			 *	  Si el campo tiene un campo relacionado, inserta el titulo en el campo relacionado.
			 */

			if (predefined_id !=null){

				Endotools.predefinidos.show(TM.content_exploraciones.detalles.textospredefinidos, predefined_id)
				.done(function(predefinido) {
					//	añadir
					var s = $target.val();
					if (s) s = [$target.val()]; else s = [];
					s.push(predefinido.texto);
					s = s.join('\n');
					$target.focus().val(s);
					$target.scrollTop($target.prop("scrollHeight"));

					// 2.4.9: Si tiene un campo relacionado, busca si el predefinido.nombre existe 
					// como valor del campo relacionado. El campo relacionado tiene que ser de tipo multiselect 
					if (campo.campo_rel_id != "" &&
						campo.campo_rel_id != undefined &&
						campo.campo_rel_id != null){

						params = {'activo': 1,'campo_id': campo.campo_rel_id, 'nombre': predefinido.nombre};

						Endotools.elementos.index(TM.content_exploraciones.detalles.elementoscampos, params)
						.done(function(elementos) {
							// donde se insertará el option
							var control_destino = $("#form-"+campo.formulario_id + "-campo-"+campo.campo_rel_id);
							cant = elementos.length;

							// recorre todos los elementos disponibles del campo relacionado, para
							// saber si se tiene que crear o solamente es agregarlo
							encontrado = false;
							i = 0
							while (i < cant && encontrado == false){
								if (predefinido.nombre.trim().toUpperCase() == elementos[i].nombre.trim().toUpperCase()){
									encontrado = true;
									index = i
								}
								i++;
							}
							
							if (encontrado){ // Existe el elemento con ese valor de nombre
								
								// verificar que no este agregado
								ya_existe = false;
								
								tipo_control = control_destino.attr("data-tipo-control") || "0";
								control_destino.children("option").each(function(i){
									if (this.value==elementos[index].id){
										// No hace falta agregarlo.
										ya_existe = true;
									}
								});

								if (!ya_existe){ // No existe, entonces agregar el option
									elementos[index].cantidad = 0;
									var $nodo = input_tipo_multi.generar_option(elementos[index], tipo_control)
									control_destino.append($nodo);	
								}

							}else{
								// #777: se lee este atributo para saber si es de cantidades o no
								tipo_control = control_destino.attr("data-tipo-control") || "0";
								nuevo_elemento.crear(predefinido.nombre, campo.campo_rel_id, control_destino, tipo_control );
							}
						});
					}
				});
			
			}
			
		},

		crear: function(campo, $parent, target_id) {
			/*	  Crea el menu de textos predefinidos de un campo.
			 *	  Se devuelve el promise que carga los predefinidos.
			 */
			var menu = menu_textos_predefinidos._crear_menu(campo, $parent, target_id);
			
			return Endotools.predefinidos.index(
				TM.content_exploraciones.detalles.textospredefinidos,
				{'campo_id': campo.id}, {fail404: false})
				//{'campo_id': campo.id, activo: true}, {fail404: false})
			.done(function(predefinidos) {
				var $select = menu.find("select");
				$select.attr("disabled", true);
				$select.empty();
				menu_textos_predefinidos._attach_default_value($select);
				for (var i=0; i < predefinidos.length; i++) {
					$('<option \
							id="predefinido-' + campo.id + '-' + predefinidos[i].id + '" ' +
							'value="' + predefinidos[i].id + '">' + predefinidos[i].nombre +
						'</option>')
					.data('predefinido_id', predefinidos[i].id).appendTo($select);
				}
				if (predefinidos && (predefinidos.length > 0)) {
					$select.removeAttr("disabled");
				}
			});
		}

	}
}();