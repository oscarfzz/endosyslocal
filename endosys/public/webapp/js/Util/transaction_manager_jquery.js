/*
Ampliar el objeto _TM de transaction_manager.js con la implementación mediante jQuery, $.ajax()
	Se sustituyen:
		abort()
		_get_transaction_fn()
		load_content()
		
	Se añaden:
		_procesar_resultado_jquery()
		_transaction_jquery()
		
*/

_TM.prototype.abort = function() {
	/*
	Sustituye el "abort" anterior
	*/
	//	abortar transacciones pendientes
	var n = 0;
	while (n < this._transactions.length) {
		var t = this._transactions[n].conn;
		var callback_abort = this._transactions[n].callback ? { failure: this._transactions[n].callback.abort }	: undefined;
		//	si es jQuery...
		if (t.promise) {
			if (t.readyState < 4) {	//	si aun no habia terminado...
				t.abort();
				//this._transactions.splice(n, 1);	//	no hace falta, con el abort() se ha ejecutado el always(), que ya la quita
				if (callback_abort && callback_abort.failure) callback_abort.failure();
			} else {
				//	si no se llega a llamar a abort(), quitarla del array, que si no se puede quedar en un bucle infinito
				this._transactions.splice(n, 1);
			}
		}
		//	si no...
		else {
			if (YAHOO.util.Connect.abort(t, callback_abort)) {
				this._transactions.splice(n, 1);	//	quitarla
//				Y.log("Se ha abortado la transaccion " + t.tId);
			} else {
				n++;
//				Y.log("Ha ocurrido un error abortando la transaccion " + t.tId, "warn");
			}
		}
	}
	return this;
};
	
function _procesar_resultado_jquery(xml, schema) {
	/*
	con esto se sustituye la funcionalidad del DataSource de YUI
	*/
	
	var $resultnodes = null;
	var $xml = $(xml);
	//	buscar el/los nodo/s "padre" (puede ser directamente el raiz, es lo habitual en un show)
	if ($xml.prop('nodeName').toUpperCase() == schema.resultNode.toUpperCase()) {
		$resultnodes = $xml;
	} else {
		$resultnodes = $xml.find(schema.resultNode);
	}
	if (!$resultnodes) return {};
	
	//	si se ha/n encontrado, añadir los campos segun el schema
	//	si era un show solo habrá 1, si era un index habrán varios
	var results = [];
	$resultnodes.each(function(index, resultnode) {
		var result = {};
		$.each(schema.fields, function(index, field) {
			//	interpretar el "locator", que es un XPath:
			//		XPath				Selector jQuery
			//		-----				---------------
			//		padre/hijo	--->	$(resultnode).find('padre>hijo')
			//		@atributo	--->	$(resultnode).attr('atributo')
			//		el1/el2/@atr -->	$(resultnode).find('el1>el2').attr('atr')
//			//		elem/elem/@atr -->	De momento no implementado, revisar si se usa en algún schema...
			var valor = null;

			if (field.locator.indexOf('medico/servicios/servicio[') == 0) {
				//	caso especial en ET_usuarios: medico/servicios/servicio[1..10]/@id... YA NO SE USA
				var n = field.locator.indexOf('[') + 1;
				var n = field.locator.substr( n, field.locator.indexOf(']') - n ) - 1;
				valor = $(resultnode).find('medico>servicios>servicio').eq(n).attr('id');
			} else if (field.locator.indexOf('@') != -1) {
				//	si contiene @ puede ser solo un atributo o una ruta con un atributo al final
				var atr = field.locator.split('/').slice(-1)[0].substr(1);
				var path = field.locator.split('/').slice(0, -1).join('>');
				if (path) {
					valor = $(resultnode).find(path).attr(atr);
				} else {
					valor = $(resultnode).attr(atr);
				}
			} else {
				//	elemento, o arbol tipo elemento1/elemento2...
				valor = $(resultnode).find(field.locator.replace('/', '>')).text();
			}
			result[field.key] = valor;
		});
		results.push(result);
	});
	return results;
};
	
_TM.prototype._transaction_jquery = function(method, url, params, callback, args) {
	/*
	igual que _transaction(), pero usando jQuery en lugar de YUI.
		method:		GET o POST
		url:		destino
		params:		querystring o object
		callback:	callback.success, callback.failure, callback.argument, callback.scope
					es opcional, ya que también funciona por promises.
		args:
		  jquery	  indica si se usa jquery... si ha entrado aqui es que es true.
		  schema	  el show_schema, index_schema, etc... que se usa con un DataSource de YUI,
					  si existe se trata de emular la misma funcionalidad.
		  compatibility	fuerza a que se genere el param adicional aun sin haber schema...
					  se usa si la respuesta es JSON, que no tiene schema.

	devuelve el promise de $.ajax()
	*/
	
	/*
	//	DEBUG
	var _noty = noty({
		text: 'transaccion jQuery: ' + method + ' - ' + url,
		layout: 'topRight'
	});
	*/
	if (cargando) cargando.show(url);
	
	if (!params) params = {};

	// ---
	// 2.4.9: Enviar el parametro v=VERSION en la peticion, NO FUNCIONA CORRECTAMENTE
	// cuando lo que se pide no es html da un error 500. Ej: en las llamadas al REST
	// Seguramente porque intenta usar ese parametro para algo y eso lo hace fallar
	// Una posible solucion seria usar _v= asi el rest no lo procesa.
	// params["v"] = version; M
	// ---
	
	var jqXHR = $.ajax(url, {
		type: method,
		data: params,
		cache: false,
		context: this,
		dataFilter: function(data, dataType) {
			//	si se indica un schema, procesar el resultado XML, como lo haria el DataSource de YUI
			//	si el resultado es JSON no se ha de indicar schema
			if (args && args.schema) {
				return _procesar_resultado_jquery(data, args.schema);
			} else {
				return data;
			}
		}
	})
	
	.always(function() {
		this._remove_transaction(jqXHR);
	})
	
	.done(function(data, textStatus, jqXHR) {
		if (callback && callback.success) {
			var result = null;
			var adicional = undefined;
			if ((args && args.schema) || args.compatibility) {
				result = data;
				//	para compatibilizar con el estilo hasta ahora (usando DataSources), donde el segundo
				//	parametro era oResponse, y el resultado estaba en oResponse.results[0], se añade de esta
				//	manera. El primer parametro	era oRequest, pero como nunca se utiliza, se mantiene ahi el
				//	result directamente. El tercer parametro era oPayload, pero tampoco se usa nunca.
//				adicional = { results: result };
//				adicional = $.isArray(result) { results: result } : { results: [result] };
				adicional = {
					results:	$.isArray(result) ? result : [result]
				}
			} else {
				result = jqXHR;
			}
			
			if (!callback.scope) {
				callback.success(result, adicional);
			} else {
				callback.success.apply(callback.scope, [result, adicional]);
			}
		}
		if (cargando) cargando.hide(url);
	})
		
	.fail(function(jqXHR, textStatus, errorThrown) {
		if (cargando) cargando.hide(url);

		if (textStatus == 'abort') {
			//	el callback.failure() no se ejecutaba si era un abort(), en cambio con jQuery,
			//	al abortar sí que entra en fail(), por lo que se tiene que filtrar.
			return;
		}
		if (callback && callback.failure) {
			if (!callback.scope) {
				callback.failure(jqXHR);
			} else {
				callback.failure.apply(callback.scope, [jqXHR]);
			}
		}

		if (cargando) cargando.hide(url);
	});
	
	//	XXX: se habia probado con un then(), para asi "transformar" la respuesta llamando a
	//		a _procesar_resultado_jquery() y devolviendo una nueva promise con esta linea:
	//			return $.Deferred().resolve(data, textStatus, jqXHR).promise();
	//		el problema es que entonces al final la promise se que devolvia en esta funcion
	//		ya no era un objeto jqXHR, y no tenía la funcion abort(), por lo que no se podía
	//		abortar la transacción.

	this._transactions.push( {'conn': jqXHR, 'callback': callback} );
	return jqXHR;	//	es un promise, y además tiene .abort()
};

_TM.prototype._get_transaction_fn = function() {
	/*
	datasource, params, callback					utilizar el datasource
	method, url, params, callback, {jquery: true}	utilizar jQuery, $.ajax()
	method, url, params, callback					utilizar YAHOO.util.Connect.asyncRequest
	*/
	if (arguments[0] instanceof YAHOO.util.XHRDataSource) {
		throw 'intento de usar _transaction_ds (DataSource)!'
		//return this._transaction_ds;
	} else if (arguments[4] && arguments[4].jquery) {
		return this._transaction_jquery;
	} else {
		throw 'intento de usar _transaction (YAHOO.util.Connect.asyncRequest)!'
		//return this._transaction;
	}
};

_TM.prototype.load_content = function(el, url, callback) {
	/*
		"el" puede ser un selector (string), un objeto jQuery, un elemento HTML, o un objeto de YUI 3
		XXX	no se si en algún caso se llama con un objeto de YUI 2...
	*/

	if (el._yuid && el._node) el = el._node;	//	es un objeto de YUI
	
	return this._transaction_jquery('GET', url)
		.done(function(response) {
			$(el).html(response);
			$(el).i18n();	//	aplicar la traducción a los elementos con atributos "data-i18n"
			if (callback && callback.success) callback.success(response);
		});

};
