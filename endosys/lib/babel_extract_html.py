from HTMLParser import HTMLParser

class BabelExtractHTMLParser(HTMLParser):

	def __init__(self, keywords):
		HTMLParser.__init__(self)
		self.keywords = keywords
		self.extracted_messages = []
		self.pendiente = None

	def _procesar_mensaje(self, msg):
		"""
		quita las opciones del principio [prepend], [append] y [html]
		"""
		if msg.startswith("[prepend]"): return msg[len("[prepend]"):]
		elif msg.startswith("[append]"): return msg[len("[append]"):]
		elif msg.startswith("[html]"): return msg[len("[html]"):]
		else: return msg

	def handle_starttag(self, tag, attrs):

		self.pendiente = None # resetear pendiente...

		for k, v in attrs:
			if k in self.keywords:
				# si el atrinuto no tiene valor, lo buscará en el text del elemento
				if not v:
					# XXX   se podría usar HTMLParser.get_starttag_text() ...
					self.pendiente = k # guarda el nombre del atributo (p.e. data-i18n)
				else:
					self.extracted_messages.append( (self.getpos()[0], k, self._procesar_mensaje(v), "") )

	def handle_data(self, data):
		if self.pendiente:
			self.extracted_messages.append( (self.getpos()[0], self.pendiente, data, "") )
		self.pendiente = None


def extract_html(fileobj, keywords, comment_tags, options):
	"""
	Usado para extraer de los atributos  "data-i18n", usados por la
	libreria javascript i18next.

	También permite la opción de que, si el atributo está vacío,
	coja la cadena del contenido del elemento.

	Además quita las opciones del principio [prepend], [append] y [html]
	"""
	parser = BabelExtractHTMLParser(keywords)
	parser.feed(fileobj.read())
	return parser.extracted_messages
