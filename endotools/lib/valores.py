from endotools.model import ValorTexto, \
							ValorSelec, \
							ValorMulti, \
							ValorBool

import logging
log = logging.getLogger(__name__)

def get_valor_class_by_tipo(tipo):
	""" dado un tipo de campo se devuelve la clase de valor correspondiente
		1: texto / 2: selec / 3: multi / 4: bool / 5: memo
	"""
	tipo = int(tipo)

	if tipo==1 or tipo==5:
		return ValorTexto
	if tipo==2:
		return ValorSelec
	if tipo==3:
		return ValorMulti
	if tipo==4:
		return ValorBool

	# retorna none si no corresponde con ninguno
	return None