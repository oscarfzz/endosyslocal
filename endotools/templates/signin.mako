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
    <title>Sign in</title>
</%def>

<%def name="javascript_tags()">
    <script type="text/javascript">
	do_signin = function() {
            var form = $("formulario");
            var user = $F(form["username"]);
            var pass = $F(form["password"]);
            new Ajax.Request('FORM_ACTION', {
			method: 'post',
			parameters: {username: user, password: pass},
			asynchronous: true,
			onSuccess: function(request){ok(request)},
			onFailure: function(request){error(request)}
		})
            return false;

	}

    	function ok(request) {
//		alert(this.url);
//		new Ajax.Updater($('content'), '/web/pacientes', {method: 'get', evalScripts: true})
	}

    	function error(request) {
//		alert(this.url);
	}

    </script>
</%def>


<form id="formulario">
    <table border=0>
    <tr><td class="text9" colspan=2></td></tr>
    <tr>
    	<td class="text9">Usuario: </td><td><input id="username" type="text" class="campo"></td>
    	<td class="text9">Contrase&ntilde;a </td><td><input id="password" type="password" class="campo"></td>
    </tr>
    <tr>
        <td align="center" colspan="4"><button type="button" onclick="do_signin()" class="boton">Sign In</button>
        <button type="reset" class="boton">Reset</button></td>
    </tr>
	</table>
	<!--
	${h.text_field("username", "")}
    ${h.password_field("password", "")}
	${h.button_to_function("Sign In", "do_signin()")}
	-->

</form>




  </body>
</html>
