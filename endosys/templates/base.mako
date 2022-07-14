# -*- coding: utf-8 -*-
<html>
  <head>
    ${self.head_tags()}
    ${h.javascript_include_tag(builtins=True)}
    <script src="/javascripts/endosys.js" type="text/javascript"></script>
    ${self.javascript_tags()}
    ##${h.stylesheet_link_tag('/css/endosys.css')}
    ##${h.stylesheet_link_tag('/css/layout.css')}
  </head>
  <body>
    ${next.body()}
  </body>
</html>

<%def name="head_tags()">
    <title>Override Me!</title>
</%def>

<%def name="javascript_tags()">
</%def>
