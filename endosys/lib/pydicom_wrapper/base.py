from pylons.i18n import _
from pydicom.dataset import Dataset
from pynetdicom import AE

class BasePyDICOM(object):
    #TODO: Esta tiene que ser la clase Base para todas
    #      las utilidades de dicom
    assoc = None
    called_ae = None
    calling_ae = None
    server = None
    port = None
    conf = None
    requested_contexts = None
    ae = None
    ext_neg=None
    evt_handlers=None

    def __init__(self, conf=None):
        """ inicializa y crea la asociacion
        """
        if not conf:
            raise Exception(_(u'No se envió la configuración'))
        self.conf = conf

        if not 'connection_data' in conf:
            raise Exception(_(u'No se enviaron los datos de conexión'))
        connection_data = conf['connection_data']

        if not 'calling_ae' in connection_data or \
            not 'called_ae' in connection_data or \
            not 'server' in connection_data or \
            not 'port' in connection_data:
            raise Exception(_(u'Los parametros del conexion a MWL no son correctos'))

        self.ae = AE()
        self.assoc = self._create_assoc(connection_data)

    def set_requested_context(self):
        # Para implementar
        pass

    def hook_pre_associate(self):
        # Para implementar
        pass

    def _create_assoc(self, connection_data):
        """ Crea una conexión con el Servidor DICOM
        """

        # asignar datos de conexion a varibles locales
        self.called_ae = str(connection_data['called_ae'])
        self.calling_ae = str(connection_data['calling_ae'])
        self.server = str(connection_data['server'])
        self.port = int(connection_data['port'])

        # Inicializar el Application Entity
        self.ae.ae_title = self.calling_ae
        
        # Agregar un requested presentation context
        self.set_requested_context()

        # para agregar funcionalidad especifica
        self.hook_pre_associate()
        
        assoc = self.ae.associate(self.server, self.port, ae_title=self.called_ae, ext_neg=self.ext_neg, evt_handlers=self.evt_handlers)
        if not assoc.is_established:
            raise Exception(_(u"Error al conectárse al servidor DICOM Worklist"))

        return assoc