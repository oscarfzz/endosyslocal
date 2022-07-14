# -*- coding: utf-8 -*-

<%inherit file="base.mako" />

<%def name="head_tags()">
    <title>PYTHON interpreter</title>
</%def>

<%def name="javascript_tags()">
    <script type="text/javascript">
    
        ejecutarClick = function() {
            var form = $(formulario);
            var codigo = $F(form["codigo"]);

            new Ajax.Request('/interpreter/ejecutar', {
                        method: 'get',
                        parameters: {command: codigo},
                        asynchronous:true,
                        evalScripts:true,
                        onSuccess:function(request){requestSuccess(request)},
                        onFailure:function(request){requestFailure(request)}
                    })

            return false;
        }
        
    	function requestSuccess(request) {
            //  cargar la respuesta
            $(salida).update(request.responseText);
        }
        
        function requestFailure(request) {
            alert('ERROR. http status: ' + request.status);
        }

        
    </script>
</%def>

<h1>PYTHON interpreter</h1>

<form id="formulario">

    ${h.text_area("codigo", "", size="100x15")}
    <br>
    ${h.button_to_function("ejecutar", "ejecutarClick()")}
    
</form>

<h2>salida:</h2>
<div id="salida"></div>