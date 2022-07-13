# -*- coding: utf-8 -*-

<html>
  <head>
    ${self.head_tags()}
    ${h.javascript_include_tag(builtins=True)}
    <script src="/javascripts/endotools.js" type="text/javascript"></script>
    ${self.javascript_tags()}
    ##${h.stylesheet_link_tag('/css/endotools.css')}
    ##${h.stylesheet_link_tag('/css/layout.css')}
  </head>
  <body>






<%def name="head_tags()">
    <title>test REST</title>
</%def>

<%def name="javascript_tags()">
    <script type="text/javascript">

        opChange = function() {
                var form = $(formulario);
                var operacion = $F(form["op"]);
                if ((operacion == 'obtener') || (operacion == 'modificar') || (operacion == 'eliminar')) {
                    Element.extend(form["rest_id"]).enable();
                } else if ((operacion == 'nuevo') || (operacion == 'lista')) {
                    Element.extend(form["rest_id"]).disable();
                }
        }

    	Event.observe(window, 'load', function() {
                var form = $(formulario);
                Event.observe(form["op"], 'change', opChange);
    	})

        getParametros = function() {
            var form = $(formulario);
            var params = $F(form["params"]).split("\n");
            var i;
            var result = {};
            for(i=0; i<params.length; i++) {
                //result[ params[i].split("=")[0] ] = params[i].split("=")[1];

				//  permitir el simbolo "=" dentro del valor
            	var s = params[i].split("=");
            	var key = s[0];
				var value = s[1];
				for (var j=2; j < s.length; j++) {
					value = value + '=' + s[j];
				}

                result[key] = value;
            }

            return result;
        }

        testClick = function() {
            var form = $(formulario);
            var operacion = $F(form["op"]);
            var url = '/rest/' + $F(form["rest_resource"]);
            var metodo;
            var parametros = {};

            if (Element.extend(form["rest_id"]).readAttribute("disabled") == null) {
                url = url + '/' + $F(form["rest_id"]);
            }

            if (operacion == 'obtener') {
                metodo = 'get';
            } else if (operacion == 'lista') {
                metodo = 'get';
                parametros = getParametros();
            } else if (operacion == 'modificar') {
                metodo = 'put';
                parametros = getParametros();
            } else if (operacion == 'eliminar') {
                metodo = 'delete';
                parametros = getParametros();
            } else if (operacion == 'nuevo') {
                metodo = 'post';
                parametros = getParametros();
            }

            new Ajax.Request(url, {
                        method: metodo,
                        parameters: parametros,
                        asynchronous:true,
                        evalScripts:true,
                        onSuccess:function(request){requestSuccess(request)},
                        onFailure:function(request){requestFailure(request)}
                    })

            return false;
        }

    	function requestSuccess(request) {
//            xmlDoc = request.responseXML;
            //  cargar la respuesta
            $(resultado).update(request.responseText);
            alert('Success');
        }

        function requestFailure(request) {
            $(resultado).update(request.responseText);
            alert('ERROR. http status: ' + request.status);
        }


    </script>
</%def>

<h1>test REST</h1>

<form id="formulario">

    recurso REST: /rest/
    ${h.text_field("rest_resource", "pacientes", size=15)}
    /
    ${h.text_field("rest_id", "1", size=3)}
    <br>
    <br>
    operación:
    ${h.select("op", "<option>obtener</option><option>lista</option><option>nuevo</option><option>modificar</option><option>eliminar</option>")}
    <br>
    <br>
    parámetros (1 parámetro en cada linea. Separar el nombre del parámetro y su valor con "="):
    <br>
    ${h.text_area("params", "historia=1\r\nnombre=Juan\r\napellido1=Garcia\r\napellido2=Fernandez\r\nDNI=324536", size="30x15")}
    <br>
    pacientes: historia= nombre= apellido1= apellido2= DNI=
    <br>
    pruebas: fecha= hora= paciente_id=
    <br>
    ${h.button_to_function("enviar", "testClick()")}

</form>

<h2>Respuesta:</h2>
<div id="resultado"></div>



  </body>
</html>
