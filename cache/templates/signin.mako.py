from mako import runtime, filters, cache
UNDEFINED = runtime.UNDEFINED
_magic_number = 2
_modified_time = 1652869559.126
_template_filename='c:\\endotoolsweb\\endosysapp\\endosys\\templates/signin.mako'
_template_uri='/signin.mako'
_template_cache=cache.Cache(__name__, _modified_time)
_source_encoding='utf-8'
_exports = ['javascript_tags', 'head_tags']


def render_body(context,**pageargs):
    context.caller_stack.push_frame()
    try:
        __M_locals = dict(pageargs=pageargs)
        h = context.get('h', UNDEFINED)
        self = context.get('self', UNDEFINED)
        # SOURCE LINE 2
        context.write(u'\n<html>\n  <head>\n    ')
        # SOURCE LINE 5
        context.write(unicode(self.head_tags()))
        context.write(u'\n    ')
        # SOURCE LINE 6
        context.write(unicode(h.javascript_include_tag(builtins=True)))
        context.write(u'\n    <script src="/javascripts/endotools.js" type="text/javascript"></script>\n    ')
        # SOURCE LINE 8
        context.write(unicode(self.javascript_tags()))
        context.write(u'\n')
        # SOURCE LINE 11
        context.write(u'  </head>\n  <body>\n\n\n\n\n\n\n')
        # SOURCE LINE 21
        context.write(u'\n\n')
        # SOURCE LINE 50
        context.write(u'\n\n\n<form id="formulario">\n    <table border=0>\n    <tr><td class="text9" colspan=2></td></tr>\n    <tr>\n    \t<td class="text9">Usuario: </td><td><input id="username" type="text" class="campo"></td>\n    \t<td class="text9">Contrase&ntilde;a </td><td><input id="password" type="password" class="campo"></td>\n    </tr>\n    <tr>\n        <td align="center" colspan="4"><button type="button" onclick="do_signin()" class="boton">Sign In</button>\n        <button type="reset" class="boton">Reset</button></td>\n    </tr>\n\t</table>\n\t<!--\n\t')
        # SOURCE LINE 66
        context.write(unicode(h.text_field("username", "")))
        context.write(u'\n    ')
        # SOURCE LINE 67
        context.write(unicode(h.password_field("password", "")))
        context.write(u'\n\t')
        # SOURCE LINE 68
        context.write(unicode(h.button_to_function("Sign In", "do_signin()")))
        context.write(u'\n\t-->\n\n</form>\n\n\n\n\n  </body>\n</html>\n')
        return ''
    finally:
        context.caller_stack.pop_frame()


def render_javascript_tags(context):
    context.caller_stack.push_frame()
    try:
        # SOURCE LINE 23
        context.write(u'\n    <script type="text/javascript">\n\tdo_signin = function() {\n            var form = $("formulario");\n            var user = $F(form["username"]);\n            var pass = $F(form["password"]);\n            new Ajax.Request(\'FORM_ACTION\', {\n\t\t\tmethod: \'post\',\n\t\t\tparameters: {username: user, password: pass},\n\t\t\tasynchronous: true,\n\t\t\tonSuccess: function(request){ok(request)},\n\t\t\tonFailure: function(request){error(request)}\n\t\t})\n            return false;\n\n\t}\n\n    \tfunction ok(request) {\n//\t\talert(this.url);\n//\t\tnew Ajax.Updater($(\'content\'), \'/web/pacientes\', {method: \'get\', evalScripts: true})\n\t}\n\n    \tfunction error(request) {\n//\t\talert(this.url);\n\t}\n\n    </script>\n')
        return ''
    finally:
        context.caller_stack.pop_frame()


def render_head_tags(context):
    context.caller_stack.push_frame()
    try:
        # SOURCE LINE 19
        context.write(u'\n    <title>Sign in</title>\n')
        return ''
    finally:
        context.caller_stack.pop_frame()


