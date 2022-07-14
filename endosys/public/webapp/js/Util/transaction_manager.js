/*
poder crear TMs temporales, es decir, sin nombre, y que al terminar se eliminen automaticamente.

o mejor:
poder crear TMs que permitan multiples transacciones simultaneas, es decir, que al crear una transaccion no aborte las anteriores.


*/

function _TM(name, parent, multi, dont_abort) {
	this._parent = parent;
	this._name = name;
	this._groups = {};
	this._transactions = [];
	this._multi = multi;
	this._dont_abort = dont_abort;
}

function _TM_group(name) {
	this._name = name;
	this.TMs = {};
}


_TM.prototype = {
	
	_name: null,
	_parent: null,
	_group: null,
	_groups: null,
	_transactions: null,
	_multi: null,
	_dont_abort: null,
	
	_active: null,
	
	add: function(name, multi, dont_abort) {
		//	añade un nuevo TM a éste
		//	si se pasa por ejemplo "content:pacientes" se convierte a "content_pacientes".
		//	esto se utiliza para definir TMs mutuamente exclusivos, es decir, que al activarse uno automaticamente se
		//	desactivarán el resto del mismo grupo (el grupo es la primera parte del nombre, en el ejemplo "content")	
		
		//	multi: indica si el TM permite varias transacciones simultaneas, o si aborta las anteriores al crear una nueva.		
		
		//	dont_abort: indica que en el caso de no ser multi, en vez de abortar las anteriores no se ejecutará si hay alguna pendiente
		var i;
		
		if (name in _TM.prototype) throw new Error('No se puede añadir un TM con el nombre "' + name + '"');
		i = name.indexOf(":");
		if (i >= 0) name[i] = '_';	//	XXX	esto no va con IE7
		
		if (!multi) multi = false;
		if (!dont_abort) dont_abort = false;
		this[name] = new _TM(name, this, multi, dont_abort);

		//	comprobar si pertenece a un grupo
		i = name.indexOf("_");
		if (i >= 0) {
			var group_name = name.substring(0, i);
			//	si existe el grupo añadir el TM, si no crearlo antes
			if (!this._groups[group_name]) this._groups[group_name] = new _TM_group(group_name);
			this._groups[group_name].TMs[name] = this[name];
			this[name]._group = this._groups[group_name];
		}

		return this[name];
	},
	
	get_pending: function() {
		//	devuelve cuantas transacciones hay pendientes por finalizar
		var n = this._transactions.length;
		//Y.log("transaction_manager " + this._name + ", transacciones pendientes = " + n);
		return n;
	},
	
	deactivate: function() {
		if (!this._active) return this;
		this.abort();
		this._active = false;
		return this;
	},

	activate: function() {
		//	comprobar si pertenece a un grupo, y si es asi desactivar el resto de TMs del grupo
		if (this._active) return this;
		if (this._group) {
			for (var tm in this._group.TMs) {
				this._group.TMs[tm].deactivate();
			}
		}
		this._active = true;
		return this;
	},
	
	_remove_transaction: function(t) {
		if (typeof t == "number") {
			for (var i in this._transactions) {
				if (this._transactions[i].conn.tId == t) {
					this._transactions.splice(i, 1);
					break;
				}
			}
		} else {		
			for (var i in this._transactions) {
				if (this._transactions[i].conn == t) {
					this._transactions.splice(i, 1);
					break;
				}
			}		
		}
	},
	
	_do_success: function(response) {
//		var tm = response.argument.tm;
		var callback = response.argument.callback;
		response.argument = callback.argument;
		this._remove_transaction(response.tId);
		if (callback.success) {
			if (!callback.scope) callback.success(response);
			else {
				callback.success.apply(callback.scope, [response]);
			}
		}
	},
	
	_do_failure: function(response) {
		//var tm = response.argument.tm;
		var callback = response.argument.callback;
		response.argument = callback.argument;
		//tm._remove_transaction(response.tId);
		this._remove_transaction(response.tId);
		if (callback.failure) {
			if (!callback.scope) callback.failure(response);
			else {
				callback.failure.apply(callback.scope, [response]);
			}
		}
	},
	
	/*_transaction: function(method, url, params, callback) {
		//	callback.success, callback.failure, callback.argument, callback.scope
		
		if (params == null) params = {};
		//	sacado del Connection Manager (YUI2): para evitar la cache (cambiando el nombre del parametro a "_rand")
		if (typeof params == "string") {
			params += ((params != '') ? '&' : '') + "_rand=" + new Date().valueOf().toString();			
		} else {
			params["_rand"] = new Date().valueOf().toString();
			params = Y.QueryString.stringify(params);
		}
		//////////

		if (method.toUpperCase() == 'GET') {
		
			if (url && (url.charAt(url.length-1) != '?')) url += '?';			
			url += params;
			params = null;
		}
		
		//var tm = this;
		var conn = YAHOO.util.Connect.asyncRequest(method, url, {
						success: this._do_success,
						failure: this._do_failure,
						argument: {callback: callback},
						scope: this
			}, params);
		this._transactions.push( {'conn': conn, 'callback': callback} );
		
		return true;
	},*/
	
	
	/*_transaction_ds: function(datasource, params, callback) {
		//	callback.success, callback.failure, callback.argument, callback.scope

		//	el datasource deberia tener el '?' o '&' al final en el liveData		
		if ((datasource.liveData.charAt(datasource.liveData.length-1) != '?') && (datasource.liveData.charAt(datasource.liveData.length-1) != '&'))
			throw new Error("Error Transaction Manager: 'datasource.livedata' debe terminar con el caracter '?' o '&' para poder concatenar paarámetros");
			
		if (params == null) params = {};
		//	sacado del Connection Manager (YUI2): para evitar la cache (cambiando el nombre del parametro a "_rand")
		if (typeof params == "string") {
			params += ((params != '') ? '&' : '') + "_rand=" + new Date().valueOf().toString();			
		} else {
			params["_rand"] = new Date().valueOf().toString();
			params = Y.QueryString.stringify(params);
		}
		
		datasource.doBeforeParseData = function(oRequest, oFullResponse, oCallback) { return oFullResponse; };
		
		//////////
		//	XXX
		var tm = this;
		datasource.sendRequest(params, {
						success: function(oRequest, oResponse, oPayload) {
							tm._remove_transaction(conn);
							if (callback.success) callback.success(oRequest, oResponse, oPayload);
							//	XXX	scope?
						},
						failure: function(oRequest, oResponse, oPayload) {
							tm._remove_transaction(conn);
							if (callback.failure) callback.failure(oRequest, oResponse, oPayload);
							//	XXX	scope?						
						}
			});
		var conn = datasource._oQueue.conn;
		this._transactions.push( {'conn': conn, 'callback': callback} );
		
		return true;		
	},*/

	
	transaction: function() {
		if (!this._active) return false;
		
		//	abortar las transacciones pendientes (si no permite multiples simultaneas)
		if (!this._multi) {
			if ((this._dont_abort) && (this.get_pending() > 0)) {
				//	en el caso de "dont_abort", si hay transacciones pendientes
				//	no ejecutar esta.
				return false;
			} else {
				this.abort();
			}
		}

		if (arguments.length < 3) throw new Error('transaction debe ser llamada con al menos 3 argumentos.');	//	puede que esta linea deba ir en _get_transaction_fn()
		
		//	obtener la funcion "_transaction" según el tipo de argumentos y ejecutarla
		//	además retorna el valor... para YUI retorna true, pero para jQuery retorna un promise
		fn = this._get_transaction_fn.apply(this, arguments);
		return fn.apply(this, arguments);
	}

	
};


_TM_group.prototype = {

	TMs: null
	
};


//	raiz
var TM = new _TM("TM", false);
