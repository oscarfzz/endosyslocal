/*
Todos los métodos (show, index, update, create y delete) admiten el uso
mediante jQuery. (indicando rest_cfg.jquery = True).

Además, en ese caso devuelven el promise de $.ajax().
*/

Endotools.REST = function() {

//	var datasource;
	var datasources = [];
		
	return {
   
		init: function() {
//			datasource = Endotools.REST._new_datasource();
		}
		
		/*,_new_datasource: function() {
			var datasource = new YAHOO.util.XHRDataSource();
			datasource.connMethodPost = false;
			datasource.useXPath = true;
			datasource.responseType = YAHOO.util.DataSource.TYPE_XML;
			datasources.push(datasource);
			return datasource;
		}*/
		
		/*,_datasource_in_progress: function() {
			return datasource.connMgr.isCallInProgress(datasource._oQueue.conn);
		}*/

		,_get_datasource: function() {
			throw 'Trying to use DataSource object!';/*NO TRADUCIR*/
			//	XXX	para poder acceder a datasource desde fuera
			if (Endotools.REST._datasource_in_progress()) {
				return Endotools.REST._new_datasource();
			} else {
				return datasource;
			}				
		}
		
		//	REVISADO 22-2-2013, NO SE UTILIZA
		,abort_all: function() {
			Y.log('abort: ' + YAHOO.util.Connect.abort( datasource._oQueue.conn ));
			for (var n in datasources) {
				Y.log('abort: ' + YAHOO.util.Connect.abort( datasources[n]._oQueue.conn ));
			}
		}
		
		
		//	jquery ok		
		,show: function(tm, rest_cfg, id, callback, params, resource_params) {
			/*
			tm					El Transaction Manager a utilizar
			rest_cfg			Configuración:
				resource		 recurso al que accede
				jquery			 indica si usa jQuery, $.ajax(). En este caso se devuelve un promise
				jquery_datatype	 xml|json
				raw_show		 indican si se procesa o no el resultado mediante un datasource (YUI)
				show_schema		 si se procesa el resultado con un datasource (raw: false), se ha de definir un schema para mapear el XML
				format			 formato, puede ser null, 'xml' o 'json'. Se añade al final de la url
			id					id del recurso a mostrar
			callback			objeto callback (con success, failure...)
			params				parametros adicionales que se pasan en la petición
			resource_params		parametros para sustituir en la cadena resource
			*/
			var res;
			if (resource_params) {
				res = vsprintf(rest_cfg.resource, resource_params);
			} else {
				res = rest_cfg.resource;
			}
			
			//	concatenar el id
			res += "/" + id;
			
			//	formato
			if (rest_cfg.format) {
				if (rest_cfg.format.charAt(0) != '.') res += '.';
				res += rest_cfg.format;
			}

			//	concatenar el '?'
			//	XXX si se usa rest_cfg.jquery, no haría falta el ? del final, aunque parece que tampoco molesta
			res += "?";
		
			//	segun si ha de devolver el response parseado o 'raw', usar dataasource o no
			if (rest_cfg.jquery) {
				var promise = null;
				if (rest_cfg.raw_show) {
					//	el callback recibe un objeto "response" igual que usando YUI raw (un objeto XMLHttpRequest
					//	con .responseXML, etc...), por lo que debería poder sustituirse sin cambios en el código.
					promise = tm.transaction('GET', res, params, callback, {jquery: true});
				} else {
					//	jQuery sin raw show, es decir, procesando la respuesta asi:
					//		si es xml, devuelve el .responseXML
					//		si es text, devuelve el .responseText
					//		si es json, lo parsea y devuelve el objeto
					//		si es html, ejecuta los scripts y devuelve un string con el HTML
					//		si es script, ejecuta el script y no devuelve nada
					//	De momento como siempre es XML, lo que hará es procesar el .responseXML emulando lo
					//	que hace el datasource, usando el show_schema.
					promise = tm.transaction('GET', res, params, callback, {jquery: true, schema: rest_cfg.show_schema, compatibility: rest_cfg.compatibility});
				return promise || $.Deferred().reject().promise();
				}
			} else {
				if (rest_cfg.raw_show) {
					tm.transaction('GET', res, params, callback);
				} else {
					var ds = Endotools.REST._get_datasource();
					ds.connMethodPost = false;
					ds.liveData = res;
					ds.responseSchema = rest_cfg.show_schema;
					tm.transaction(ds, params, callback);				
				}
			}			
			
		}

		//	jquery ok		
		,index: function(tm, rest_cfg, callback, params, resource_params) {
			/*
			tm					El Transaction Manager a utilizar
			rest_cfg			configuración:
				resource		 recurso al que accede
				jquery			 indica si usa jQuery, $.ajax(). En este caso se devuelve un promise
				raw_index		 indican si se procesa o no el resultado mediante un datasource (YUI)
				index_schema	 si se procesa el resultado con un datasource (raw: false), se ha de definir un schema para mapear el XML
				format			 formato, puede ser null, 'xml' o 'json'. Se añade al final de la url
			callback			objeto callback (con success, failure...)
			params				parametros adicionales que se pasan en la petición
			resource_params		parametros para sustituir en la cadena resource
			*/
			var res;
			res = rest_cfg.index_resource || rest_cfg.resource;
			if (resource_params) {
				res = vsprintf(res, resource_params);
			}
			
			//	formato
			if (rest_cfg.format) {
				if (rest_cfg.format.charAt(0) != '.') res += '.';
				res += rest_cfg.format;
			}
			
			//	si no tiene el '?' o '&' al final, ponerlo
			if (res.indexOf('?') == -1)
				res += '?'
			else if ((res.charAt(res.length-1) != '?') && (res.charAt(res.length-1) != '?'))
				res += '&'
			
			//	segun si ha de devolver el response parseado o 'raw', usar dataasource o no			
			if (rest_cfg.jquery) {
				var promise = null;
				if (rest_cfg.raw_index) {
					//	el callback recibe un objeto "response" igual que usando YUI raw (un objeto XMLHttpRequest
					//	con .responseXML, etc...), por lo que debería poder sustituirse sin cambios en el código.
					promise = tm.transaction('GET', res, params, callback, {jquery: true});
				} else {
					//	jQuery sin raw index.
					//	De momento como siempre es XML, lo que hará es procesar el .responseXML emulando lo
					//	que hace el datasource, usando el show_schema.
					promise = tm.transaction('GET', res, params, callback, {jquery: true, schema: rest_cfg.index_schema, compatibility: rest_cfg.compatibility});
				}
				return promise || $.Deferred().reject().promise();
			} else {
				if (rest_cfg.raw_index) {
					tm.transaction('GET', res, params, callback);
				} else {						
					var ds = Endotools.REST._get_datasource();
					ds.connMethodPost = false;
					ds.liveData = res;
					ds.responseSchema = rest_cfg.index_schema;
					tm.transaction(ds, params, callback);
				}
			}

		}
	    
		//	jquery ok		
		,update: function(tm, rest_cfg, id, callback, params, resource_params) {
			var res;
			if (resource_params) {
				res = vsprintf(rest_cfg.resource, resource_params);
			} else {
				res = rest_cfg.resource;
			}

			//	concatenar el id
			res += "/" + id;
			
			if (!params) params = {};
			params['_method'] = 'put';
			
			if (rest_cfg.jquery)
				var jquery_param = {jquery: true};
			
			return tm.transaction('POST', res, params, callback, jquery_param);
		}
		
		//	jquery ok
		,create: function(tm, rest_cfg, callback, params, resource_params) {
			var res;
			if (resource_params) {
				res = vsprintf(rest_cfg.resource, resource_params);
			} else {
				res = rest_cfg.resource;
			}

			//	formato
			if (rest_cfg.format) {
				if (rest_cfg.format.charAt(0) != '.') res += '.';
				res += rest_cfg.format;
			}
			
			//	si no tiene el '?' al final, ponerlo
			if (res.indexOf('?') == -1) res += '?';
				
				
			//	segun si ha de devolver el response parseado o 'raw', usar dataasource o no			
			if (rest_cfg.jquery) {
				var promise = null;
				if (rest_cfg.raw_create) {
					promise = tm.transaction('POST', res, params, callback, {jquery: true});
				} else {
					promise = tm.transaction('POST', res, params, callback, {jquery: true, schema: rest_cfg.create_schema, compatibility: rest_cfg.compatibility});
				}
				return promise || $.Deferred().reject().promise();
			} else {
				if (rest_cfg.raw_create) {
					tm.transaction('POST', res, params, callback);
				} else {						
					var ds = Endotools.REST._get_datasource();
					ds.connMethodPost = true;
					ds.liveData = res;
					ds.responseSchema = rest_cfg.create_schema;
					tm.transaction(ds, params, callback);
				}
			}
		}
		
		//	jquery ok
		,delete_: function(tm, rest_cfg, id, callback, params, resource_params) {
			var res;
			if (resource_params) {
				res = vsprintf(rest_cfg.resource, resource_params);
			} else {
				res = rest_cfg.resource;
			}
			
			//	concatenar el id
			res += "/" + id;
			
			if (!params) params = {};
			params['_method'] = 'delete';
			
			if (rest_cfg.jquery)
				var jquery_param = {jquery: true};
			
			return tm.transaction('POST', res, params, callback, jquery_param);
		}
		,generic_fail: function(jqXHR, textStatus, errorThrown) {
			if (jqXHR && jqXHR.status == 403) {
				Endotools.statusbar.mostrar_mensaje('El usuario no tiene permiso', 1);/*IDIOMAOK*/
			}else if (jqXHR && jqXHR.status == 401) {
				Endotools.statusbar.mostrar_mensaje('El usuario no está autenticado', 1);/*IDIOMAOK*/
			}
		}
		,make: function(resource) {
			/*
			inicializa un objeto con los metodos de acceso index, show, etc...
			a un recurso concreto. Solo para Jquery+JSON, y sin resource_params.
			*/
			
			var rest_cfg = {
				jquery: true,
				format: 'json',
				'resource': resource
			}
				
			return {
				init: function() {}
				
				,'resource': resource
				
				,index: function(tm, params, args) {
					/*
					args.datatable:	DataTable de YUI 2
					args.preprocess: function que se ejecuta en un then()
					args.fail404:	si es true, al recibir un status 404 se lanzará el fail(). Si
									no, se lanzará igualmente el done() con el resultado vacío.
					args.format:	indica el formato. Por defecto es 'json', si se indica otro cambia la funcionalidad
					*/
					var _rest_cfg = rest_cfg;
					if (args && args.format) {
						_rest_cfg = {
							jquery: true,
							format: args.format,
							'resource': resource
						}
					}
					var promise = Endotools.REST.index(tm, _rest_cfg, null, params);
					if (args && args.preprocess) {
						promise = promise.then(args.preprocess);
					}
					if (args && args.datatable) {
						gestion_paginacion.set_resource(resource);

						promise
							.done(function(results,textStatus,jqXHR) {
								//Actualizar los valores de la paginacion
								gestion_paginacion.grabar_content_range(jqXHR.getResponseHeader("Content-Range"));
								args.datatable.onDataReturnInitializeTable(null, { results: results });
							})
							.fail(function() {
								gestion_paginacion.set_error_404();
								args.datatable.getRecordSet().reset();
								args.datatable.render();
							});
					}
					///////					
					if (args && args.fail404) {
						//	ejecutar fail si es un 404... es el comportamiento por defecto del ajax().
						//return promise;
					} else {
						//	ejecutar done si es un 404. Se ha de modificar el comportamiento del ajax().
						var deferred = $.Deferred();
						promise
							.done(function(data, textStatus, jqXHR) {
								deferred.resolve(data, textStatus, jqXHR);
							})
							.fail(function(jqXHR, textStatus, errorThrown) {
								if (jqXHR && (jqXHR.status == 404)) {
									deferred.resolve([], textStatus, jqXHR);
								} else {
									deferred.reject(jqXHR, textStatus, errorThrown);
								}
							});
						promise = deferred.promise();
					}


					return promise.fail(Endotools.REST.generic_fail);					

					
				}
				,show: function(tm, id, params) {
                    
                    var _rest_cfg = rest_cfg;
					if (params && params.format) {
						_rest_cfg = {
							jquery: true,
							format: params.format,
							'resource': resource
						}
					}
                
					var promise = Endotools.REST.show(tm, _rest_cfg, id, null, params);

					return promise.fail(Endotools.REST.generic_fail);;
			
				}
				,update: function(tm, id, params) {

					var promise = Endotools.REST.update(tm, rest_cfg, id, null, params);
					
					return promise.fail(Endotools.REST.generic_fail);;

				}
				,create: function(tm, params) {
					
					var promise = Endotools.REST.create(tm, rest_cfg, null, params);
					
					return promise.fail(Endotools.REST.generic_fail);;

				}
				,'delete': function(tm, id, params, args) {	//	el nombre "delete" falla en IE7 ! aunque se puede usar obj['delete'](...)
					/*
					args.datatable: DataTable de YUI 2
					*/
					var promise = Endotools.REST.delete_(tm, rest_cfg, id, null, params);
					if (args && args.datatable) {
						//	si se indica un datatable, buscar el row con el mismo id
						//	y quitarlo.
						promise.done(function() {
								for (var i=0; i < args.datatable.getRecordSet().getLength(); i++) {
									if (args.datatable.getRecord(i).getData('id') == id) {
										args.datatable.deleteRow(i);
										break;
									}
								}
							});
					}
							
					return promise.fail(Endotools.REST.generic_fail);;
				}
			}

		}
		
   }
}();