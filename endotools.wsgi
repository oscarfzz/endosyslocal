from paste.deploy import loadapp
import os


base_dir = os.path.dirname(__file__)
# Cambiar por el ini_file que corresponda:
ini_file = "dev.ini"
application = loadapp('config:' + ini_file,
		       relative_to=base_dir)
