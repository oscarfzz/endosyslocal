var ejecutar_busqueda = function() {

	return {

		EXIST: 'EXIST',
		NO_EXIST: 'NO_EXIST',

		modo: null,	//	CON_CITA o SIN_CITA
		activo: false,

		_lanzar_busqueda: function() {
			var xml_camps = editor_busqueda2.construir_xml();
			var lista_campos = editor_busqueda2.lista_campos_gen;
			if (lista_campos.length) {
				set_titulo_pantalla(null, _('Resultados búsqueda'));/*IDIOMAOK*/
				set_atras(function() {
					contenido_principal.mostrar(editor_busqueda2)
					.done(function() {
						editor_busqueda2.reconstruir_listado_condiciones(lista_campos);
						if (editor_busqueda2.desc_busqueda != undefined) {
							set_titulo_pantalla(null, editor_busqueda2.desc_busqueda);
						} else {
							set_titulo_pantalla(null, _('Nueva'));/*IDIOMAOK*/
							editor_busqueda2.desc_busqueda = undefined;
						}
						set_atras(null);
						set_continuar(ejecutar_busqueda._lanzar_busqueda);
					});
				});
				set_continuar(null);
				ejecutar_busqueda.activo = true;

				contenido_principal.mostrar(gestion_exploraciones.avanzada, xml_camps);
			}
		},
			
		mostrar_modificar_busqueda_exist: function(id_busqueda, desc) {
			set_titulo_pantalla(_('Edición búsqueda'));/*IDIOMAOK*/
			activar_asistente();
			ejecutar_busqueda.modo = ejecutar_busqueda.EXIST;

			
			ejecutar_busqueda._mostrar_editor_busquedas_mod(id_busqueda,desc);
		},

		_mostrar_editor_busquedas_mod: function(id_busqueda, desc) {
			editor_busqueda2.desc_busqueda = desc;
			set_titulo_pantalla(null, editor_busqueda2.desc_busqueda);
			editor_busqueda2.id_busqueda = id_busqueda;
			set_atras(null);
			contenido_principal.mostrar(editor_busqueda2)
			.done(function() {
				editor_busqueda2.cargar_busqueda_existente(editor_busqueda2.id_busqueda);
			});
			set_continuar(ejecutar_busqueda._lanzar_busqueda);
		},

		mostrar_ejecutar_busqueda_exist: function(id_busqueda) {
			ejecutar_busqueda.modo = ejecutar_busqueda.EXIST;
			id = id_busqueda;
			contenido_principal.mostrar(gestion_exploraciones.avanzada, id);
		},

		mostrar_ejecutar_busqueda_no_exist: function() {
			set_titulo_pantalla(_('Edición búsqueda'));/*IDIOMAOK*/
			activar_asistente();
			ejecutar_busqueda.modo = ejecutar_busqueda.NO_EXIST;

			
			ejecutar_busqueda._mostrar_editor_busquedas();
		},

		_mostrar_editor_busquedas: function() {
			set_titulo_pantalla(null, _('Nueva'));/*IDIOMAOK*/
			editor_busqueda2.desc_busqueda = undefined;
			editor_busqueda2.id_busqueda = undefined;
			contenido_principal.mostrar(editor_busqueda2);
			set_atras(null);
			set_continuar(ejecutar_busqueda._lanzar_busqueda);
		}

	}

}();