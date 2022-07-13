/*	clase Contenido	*/

/*	
	Permite 'destruir' un contenido al mostrar otro.
	al llamar a mostrar():
		ejecuta la function "mostrar" del contenido actual (si existe)
		ejecuta la function "cerrar" del contenido anterior (si existe)
		
	De momento solo se usa en main.html, variable "contenido_principal"

*/

var Contenido = function() {
	this._actual = null;
}

Contenido.prototype = {

	mostrar: function (contenido) {
		if ((this._actual) && (this._actual.cerrar)) {
//			try {
				this._actual.cerrar();
//			} catch(err) {
//				Y.log(err);
//			}
		}
		this._actual = contenido;
		var a = [];
		for (var n = 1; n < arguments.length; n++) {
			a.push(arguments[n]);
		}
		if ((this._actual) && (this._actual.mostrar)) return this._actual.mostrar.apply(this._actual, a);
	}
	
	,cerrar: function (contenido) {
		//	cierra el contenido actual pero no muestra ninguno nuevo.
		//	"contenido" se vaciará, debería ser el mismo sitio donde estaba el
		//	contenido actual... es un poco lio y creo que no del todo lógico,
		//	se debería rehacer esta parte de gestión contenidos, mostrar, cerrar...		
		if ((this._actual) && (this._actual.cerrar)) {
			try {
				this._actual.cerrar();
			} catch(err) {
				Y.log(err);
			}
		}
		this._actual = null;
		
		if (contenido) {
			$(contenido).html("");
		}
	}

}
