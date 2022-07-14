var gestion_paginacion = function(){

	return {

		_limite_inferior: undefined,
		_limite_superior: undefined,
		cant_por_pagina: undefined,
		total: undefined,
		cant_paginas: undefined,
		pagina_actual: undefined,
		el_paginacion: undefined,
		el_total: undefined,
		error_404: false,
		resource: undefined,
		resource_anterior: undefined,
		parametros: undefined, //parametros de la consulta 
		
		// Establece el resource sobre el que esta haciendo la paginacion 
		// Solo informativo, no usado realmente.
		set_resource: function(res){
			if (this.resource!=undefined){
				this.resource_anterior = this.resource;
			}
			this.resource = res;
		},

		son_distintos_resources: function(){
			return this.resource_anterior == this.resource;
		},

		// Este metodo es que el que se usa para reiniciar la paginacion
		// ya que si los parametros son distintos quiere decir que se esta
		// realizando otra busqueda, y por lo tanto necesita volver a la pagina 1
		set_params: function(parametros){

			//borra el key _pagina para poder comparar la busqueda
			if (this.parametros!=undefined){
				delete this.parametros["_pagina"];	
				delete parametros["_pagina"];
			}

			//compara si los parametros son distintos
			if ((JSON.stringify(this.parametros) === JSON.stringify(parametros))==false){
				// vuelve a la pagina 1, porque quiere decir que se hizo otra busqueda
				this.pagina_actual = 1;
				this.parametros = parametros;
			}
			
		},

		// Parsea el contenido del Content-Range que viene en el header
		grabar_content_range: function(content_range){

			if (content_range!=null){
				
				this.error_404 = false;
				
				/* content_range es el encabezado de Content-Range de la respuesta de la peticion.
				   Content-Range esta formateado de la siguiente forma:
				   RegistroInicial-RegistroFinal/CantidadTotal.
				   Ejemplo: Si viene la pagina 2 y tiene 50 items por pagina y hay 900 registros en total
				   			el Content-Range va a venir de la siguiente manera 50-99/900
				*/

				this.total = parseInt(content_range.split("/")[1],10);	
						
				this._limite_inferior = parseInt(content_range.split("/")[0].split("-")[0],10);
				this._limite_superior = parseInt(content_range.split("/")[0].split("-")[1],10);
				
				if (this._limite_inferior==0){
					this.cant_por_pagina = this._limite_superior - this._limite_inferior + 1;
				
					if (this.total==this.cant_por_pagina){
						//Este es el caso especial que tiene una sola página
						this.cant_paginas = 1;
					}else{
						this.cant_paginas = parseInt(this.total/this.cant_por_pagina,10)+1;

						// El caso especial de que el total / cant_por_pagina de resto=0
						// Para que agregue una pagina extra al final que no da resultados
						if (this.total%this.cant_por_pagina == 0){
							this.cant_paginas -=1;
						}

					}
				}
			}
		},

		// Este metodo es llamado en el fail del ET_REST
		set_error_404: function(){
			this.error_404 = true;
		},
		
		// Limpia todo el gestion_paginador, este metodo es usado
		// en el main.js cuando se pincha en cualquier elemento del menu
		reset: function(){

			this._limite_inferior = undefined;
			this._limite_superior = undefined;
			this.cant_por_pagina = undefined;
			this.total = undefined;
			this.cant_paginas = undefined;
			this.pagina_actual = undefined;
			this.error_404 = false;
			this.resource = undefined;
			this.resource_anterior = undefined;
			this.params = undefined;
			
			//Si tiene contenido la paginacion, la borra.
			if (this.el_paginacion!= undefined){
				if (this.el_paginacion.contents().length>0){
					this.el_paginacion.html("");
				}
				//Reinicia el total en 0
				this.el_total.text("0");
			}

		},
		
		// Se guardan los elementos de la paginacion en variables
		asignar_contenedores: function(elemento_paginacion, elemento_total){
			this.el_paginacion = elemento_paginacion;
			this.el_total = elemento_total;
		},

		// Esta funcion sirve para debugear, da informacion acerca de las variables
		informacion: function(){
			var info = "Limite Inferior: "+ this._limite_inferior + "\n";
			info += "Limite Superior: "+ this._limite_superior + "\n";
			info += "Cantidad por página: "+ this.cant_por_pagina + "\n";
			info += "Total de registros: "+ this.total + "\n";
			info += "Cantidad de páginas: "+ this.cant_paginas + "\n";
			info += "Página actual: "+ this.pagina_actual + "\n";
			info += "Error 404: "+ this.error_404 + "\n";
			info += "Resource: "+ this.resource + "\n";
			info += "Resource Anterior: "+ this.resource_anterior + "\n";
			info += "Params: "+ this.params;
					
			console.log(info);
		},

		// Comprueba si hay siguiente pagina
		hay_siguiente_pagina: function(){
			if (this.pagina_actual == gestion_paginacion.cant_paginas){
				return false;
			}else{
				return true;
			}
		},

		// Comprueba si hay anterior pagina
		hay_anterior_pagina: function(){
			if (this.pagina_actual==1){
				return false;
			}else{
				return true;
			}
		},

		// Realiza un cambio de pagina, de acuerdo al valor de la pagina
		// que se le pase en el elemento	
		cambiar_pagina: function(elemento){
			
			/* Cuando se usa cambiar_pagina se tiene que pasar un elemento.
			   Este elemento es el boton que se presiono de la paginacion.
			*/
			this.mostrar_cargando();

			var nueva_pagina;
			if (elemento.attr("data-pagina")){
				//viene de un link
				nueva_pagina = parseInt(elemento.attr("data-pagina"),10);
			}else{
				//viene de un input
				nueva_pagina = parseInt(elemento.attr("value"),10);
			}

			if (nueva_pagina >=1 && nueva_pagina <= this.cant_paginas){
				this.pagina_actual = nueva_pagina;
				return this.pagina_actual;
			}else{
				console.error("El número de pagina no existe.")
				return this.pagina_actual;
			}

		},

		// Muestra el gif del "cargando...""
		mostrar_cargando: function(){
			this.el_paginacion.children("input").attr("disabled",true);
			this.el_paginacion.children("a").unbind("click");
			this.el_paginacion.children("#cargando-pagina").children("img").show();
		},

		// comprueba que exista el contenedor de paginacion
		existe_contenedor: function(){
			return this.el_paginacion.length==0;
		},

		// crea el html del paginador
		crear_paginador: function(){

			/*	Esta funcion crea el html de los botones de la paginacion
				Ejemplo del estilo de la paginacion:
					1) |<  <<   1   2  [3]  4  5 >>  >|
					2) Si es primera pag:         [1]  2   3   4  5 >>  >|
					3) Si es ultima  pag:  |<  <<  10  11  12  13  [14]
			
			*/

			// si hay un error 404, como por ejemplo cuando los criterios de 
			// busqueda no encuentran nigun resultado, aqui se comprueba y se limpia
			// el html del paginador.
			if (this.error_404){
				if (this.el_paginacion!=undefined){
 					this.el_paginacion.html("");
					this.el_total.text(0);
				}
				return false;
			}

			var html_generado = "";
	
			//div de cargando-pagina
			var cargando_pagina = '<div id="cargando-pagina"><img src="/web/assets/unused/progress.gif" style="display:none" /></div>';

			//Crear botones fijos
			var primera_pagina = '<a href="#" id="primera_pagina" data-pagina="1" class="boton-paginacion">1</a>...';
			var ultima_pagina = '...<a href="#" id="ultima_pagina" data-pagina="'+this.cant_paginas+'" class="boton-paginacion">'+this.cant_paginas+'</a>';

			//COMIENZO: Crea numeracion de 5 botones 
 			var html_numeracion = "";
 			var template = '<a href="#" data-pagina="%s" class="boton-paginacion pagina %s">%s</a>';
 			var mostrar_ultima_pagina = false;
 			var mostrar_primera_pagina = false;

 			if (this.pagina_actual > 2){
 				mostrar_primera_pagina = true;
 			}

 			if (this.pagina_actual < this.cant_paginas-1){
 				mostrar_ultima_pagina = true;
 			}

 			//anterior
 			if (this.pagina_actual-1 > 0){
 				html_numeracion += sprintf(template,this.pagina_actual-1,"",this.pagina_actual-1);
 			}

 			//actual
 			html_numeracion += '<input type="text" id="pagina-actual" value="'+this.pagina_actual+'" />'
 			//html_numeracion += sprintf(template,this.pagina_actual,"pag-activa",this.pagina_actual);

 			//siguiente
 			if (this.pagina_actual+1 <= this.cant_paginas){
 				html_numeracion += sprintf(template,this.pagina_actual+1,"",this.pagina_actual+1);
 			}

 			if (mostrar_primera_pagina){
 				html_generado += primera_pagina;
 			}

 			html_generado += html_numeracion;

 			if (mostrar_ultima_pagina){
 				html_generado += ultima_pagina;
 			}

 			html_generado += cargando_pagina;

 			// Inserta el html al elemento pasado por parametro 
 			// y crea los botones del estilo jQuery UI
 			if (this.el_paginacion!=undefined){
 				this.el_paginacion.html(html_generado);
				this.el_paginacion.children("a");
			}else{
				console.error('No esta definido el elemento contenedor del Paginador');
			}

			// escribe el total de registros en un elemento.
			if (this.el_total!=undefined){
				this.el_total.text(this.total);
			}

			// EVENTO: selecciona todo el texto cuando se hace foco en el input
			this.el_paginacion.children("#pagina-actual").bind("click",function(e){
 				$(this).select();
			});

		},
	}
}();