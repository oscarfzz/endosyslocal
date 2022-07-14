import subprocess
import os
import time
import shutil
try:
    import Image
except ImportError:
    from PIL import Image

class DCMTKConvert(object):
	
	bin_path = None

	def __init__(self, bin_path):
		""" ruta donde estan los archivos binarios de dcmtk """
		self.bin_path=bin_path

	def convert_dcm2bmp2jpg(self,source_file, destination_file, timeout=5):
		""" Dependiendo del PACS, puede ser que sea necesario 
			convetir a bmp antes de jpg (PACS AGFA)
		"""

		# ruta del archivo bmp temporal, luego se eliminara
		destination_file_bmp_temp = destination_file + ".temp.bmp"

		# configruacion de la llamada al subproceso
		process_parameters = [os.path.join(self.bin_path,'dcmj2pnm.exe')]
		process_parameters.append(source_file)
		process_parameters.append(destination_file_bmp_temp)
		process_parameters.append("+obt")

		#pydcmtk = os.path.join(config['pylons.paths']['root'], 'lib', 'dicom','pydcmtk','bin')
		
		p = subprocess.Popen(process_parameters)
		seconds = 0
		interval = 0.1
		timeout = timeout
		while p.poll() is None and seconds < timeout:
			time.sleep(interval)
			seconds += interval

		returncode = p.poll()
		
		if returncode != 0:
			raise Exception("dcmtk subprocess error: " + str(returncode))
		
		# se convitio correctamente a bmp

		try:
			# convertir bmp a jpg
			img = Image.open(destination_file_bmp_temp)
			img.save( destination_file, 'JPEG', quality=95)
			os.remove(destination_file_bmp_temp)
			return destination_file
		except Exception, e:
			raise Exception("dcmtk error: " + str(e))