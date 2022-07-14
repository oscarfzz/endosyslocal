/*
Antes se llamaba "permisos", ahora "userinfo".
asi, ademas de tener la info de los permisos, se puede tener también los servicios.
*/
var userinfo = function() {

	var array_permisos;
	var opciones_menu = new Array();
	var arrayPermUser;
	var _usuario;
	
	return {
		
		get_opciones_menu: function() {
			return opciones_menu;
		}
		
		,get_usuario: function() {
			return _usuario;
		}
		
		,inicializar: function(username) {
			return Endotools.usuarios.show(TM.operaciones, username/*, {_showmode: '1'}*/)
			
			.then(function(usuario) {
				_usuario = usuario;
				arrayPermUser = usuario.permisos;
				userinfo._relacionar_menu_permisos();
				return opciones_menu;
			});
		}

		,tiene_permiso: function(permiso){
			return _usuario.permisos.map(function(i){return i.id;}).indexOf(permiso)!=-1;
		}
		
		,_relacionar_menu_permisos: function() {
			/*
			nombre de las opciones de menu de primer nivel
			
			ORDEN	NOMBRE							PERMISOS NECESARIOS
			---------------------------------------------------------------
			1		menu-principal-gestioncitas				
			2		menu-principal-citaspendientes			
			3		menu-principal-nuevaexpl			REALIZAR EXPLORACIONES
			4		menu-principal-buscarexpl		CONSULTAR EXPLORACIONES
			5		menu-principal-gestionpacientes			
			6		menu-principal-tablas
			7		menu-principal-editortiposexpl	ADMIN TIPOS EXPLORACION
			8		menu-principal-usuarios				ADMIN USUARIOS
			9		menu-principal-busquedas				
			10		test_visual_menu (ELIMINADO)
			11		menu-principal-group-administracion	
			16		menu-principal-tareas
			17		menu-principal-mensaje
			*/
			 
			//opciones siempre visibles
			opciones_menu = [
					{num: 1, id: 'menu-principal-gestioncitas',		desc: _('Gestión de agenda')},/*IDIOMAOK*/
					{num: 2, id: 'menu-principal-citaspendientes', 	desc: _('Citas pendientes')},/*IDIOMAOK*/
					{num: 4, id: 'menu-principal-buscarexpl', desc: _('Buscar exploraciones')},//ahora pueden entrar todos los usuarios/*IDIOMAOK*/
					{num: 5, id: 'menu-principal-gestionpacientes',	desc: _('Gestión de pacientes')},/*IDIOMAOK*/
					{num: 6, id: 'menu-principal-tablas',			desc: _('Tablas')},/*IDIOMAOK*/
					{num: 9, id: 'menu-principal-busquedas',		desc: _('Búsquedas avanzadas')},/*IDIOMAOK*/
					{num: 11, id: 'menu-principal-group-administracion',		desc: _('Administración')},/*IDIOMAOK*/
					{num: 16, id: 'menu-principal-tareas',		desc: _('Tareas')},/*IDIOMAOK*/
			];
			
			if (Endotools.auth.username=="sysadmin"){
				opciones_menu.push({num: 17, id: 'menu-principal-mensaje', desc: _('Enviar Mensaje')});/*IDIOMAOK*/
			}

			//opciones variables
			for (var i = 0; i < arrayPermUser.length; i++) {
			
				//	realizar exploraciones
				if (arrayPermUser[i].id == "realizar_exploraciones") {
					opciones_menu.push({num: 3, id: "menu-principal-nuevaexpl", desc: _('Nueva exploración')});/*IDIOMAOK*/
					
				//	consultar exploraciones
				} /*else if (	arrayPermUser[i].id == "consultar_exploraciones_user" ||
							arrayPermUser[i].id == "consultar_exploraciones_todas") {
					var exist = false;
					for (var e = 0; e < opciones_menu.length; e++) {
						if (opciones_menu[e].id == "menu-principal-buscarexpl") {
							exist = true;
						}
					}
					if (!exist) {
						opciones_menu.push({num: 4, id: "menu-principal-buscarexpl", desc: "Buscar exploraciones"});
					}
					
				
				} */
				//	admin. tipos exploracion
				else if (arrayPermUser[i].id == "admin_tipos_exploracion" ){
					opciones_menu.push({num: 7,id:"menu-principal-editortiposexpl", desc:_('Editor de tipos de exploración')});/*IDIOMAOK*/
					
				//	admin. usuarios
				} else if (	arrayPermUser[i].id == "admin_usuarios" ||
							arrayPermUser[i].id == "admin_usuarios_restringido") {
					var exist = false;
					for (var e = 0; e < opciones_menu.length; e++) {
						if (opciones_menu[e].id == "menu-principal-usuarios") {
							exist = true;
						}
					}
					if (!exist) {
						opciones_menu.push({num: 8,id:"menu-principal-usuarios", desc:_('Gestión de usuarios')});/*IDIOMAOK*/
					}
				//el permiso admin_organizacion  para la opcion de "Configuración de endosys"
				} else if (arrayPermUser[i].id == "admin_organizacion" ){
					opciones_menu.push({num: 12,id:"menu-principal-administracion", desc:_('Administración de EndoTools')});/*IDIOMAOK*/
					
				
				}
			}
			userinfo._ordenar();
		},
		
		_ordenar: function() {
			for (var i = 0; i < opciones_menu.length -1; i++) {
				for (var e = 0; e < opciones_menu.length -1; e++) {
					if (opciones_menu[e].num > opciones_menu[e+1].num) {
						var aux = opciones_menu[e];
						opciones_menu[e] = opciones_menu[e + 1];
						opciones_menu[e + 1] = aux;
					}				
				}					
			}
		}
		
	}

}();