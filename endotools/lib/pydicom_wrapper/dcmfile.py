from pydicom import dcmread 
from PIL import Image

class DCMFile:

    def __init__(self, ds=None, dcmpath=None):
        """ 
            - ds: es el dataset que representa un archivo dcm
            - dcmpath: es un dataset contenido en un archivo
        """
        if ds:
            self.dcmfile = ds
        if dcmpath:
            try:
                self.dcmfile = dcmread(dcmpath)
            except Exception, e:
                raise Exception('Error reading DCMFile: %s' % (str(e)))

    def convert(self, destinationpath=None, format=None):
        if not destinationpath:
            raise Exception('Destination path is missing')
        if not format:
            raise Exception('Format is missing')

        if format == 'jpg':
            self.dicom2jpg(destinationpath)
        if format == 'png':
            self.dicom2png(destinationpath)
        else:
            raise Exception("Not Supported")

    def dicom2jpg(self, destinationpath):
        try:
            jpg = Image.fromarray(self.dcmfile.pixel_array)
            jpg.save(destinationpath)
            return destinationpath
        except Exception, e:
            raise Exception("can't convert: "+ str(e))

    def dicom2png(self, destinationpath):
        shape = self.dcmfile.pixel_array.shape

        # Convert to float to avoid overflow or underflow losses.
        image_2d = self.dcmfile.pixel_array.astype(float)

        # Rescaling grey scale between 0-255
        image_2d_scaled = (np.maximum(image_2d,0) / image_2d.max()) * 255.0

        # Convert to uint
        image_2d_scaled = np.uint8(image_2d_scaled)

        # Write the PNG file
        with open(destinationpath, 'wb') as png_file:
            w = png.Writer(shape[1], shape[0], greyscale=True)
            w.write(png_file, image_2d_scaled)