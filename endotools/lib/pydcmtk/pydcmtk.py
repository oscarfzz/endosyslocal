''' python wrapper de dcm.dll (funciones de acceso DICOM) '''
import logging
log = logging.getLogger(__name__)

from ctypes import *
from datetime import date, time

logdir = None
class DCMException(Exception):

    def __str__(self):
        if logdir:
            from os import path
            return '%s (Ver detalles en el archivo "%s")' % ( Exception.__str__(self), path.join(logdir, 'dcm.log') )
        else:
            return Exception.__str__(self)

# constantes

kQueryRetrieveLevel = 0						#	0008,0052
kPatientID = 1                              #	0010,0020
kPatientName = 2                            #	0010,0010
kStudyInstanceUID = 3                       #	0020,000d
kSeriesInstanceUID = 4                      #	0020,000e
kSOPInstanceUID = 5                         #	0008,0018
kMediaStorageSOPClassUID = 6                #	0002,0002
kMediaStorageSOPInstanceUID = 7             #	0002,0003
kTransferSyntaxUID = 8                      #	0002,0010
kImplementationClassUID = 9                 #	0002,0012
kSOPClassUID = 10                           #	0008,0016
kPatientName = 11                           #	0010,0010
kStudyDate = 12                             #	0008,0020
kSeriesDate = 13                            #	0008,0021
kStudyTime = 14                             #	0008,0030
kSeriesTime = 15                            #	0008,0031
kConversionType = 16                        #	0008,0064
kSamplesPerPixel = 17                       #	0028,0002
kPhotometricInterpretation = 18             #	0028,0004
kPlanarConfiguration = 19                   #	0028,0006
kRows = 20                                  #	0028,0010
kColumns = 21                               #	0028,0011
kPixelAspectRatio = 22                      #	0028,0034
kBitsAllocated = 23                         #	0028,0100
kBitsStored = 24                            #	0028,0101
kHighBit = 25                               #	0028,0102
kPixelRepresentation = 26                   #	0028,0103
kPixelData = 27                             #	7FE0,0010
kLossyImageCompression = 28                 #	0028,2110
kScheduledProcedureStepSequence = 29        #	0040,0100
kScheduledProcedureStepStartDate = 30       #	0040,0002
kScheduledProcedureStepStartTime = 31       #	0040,0003
kCineRate = 32                              #	0018,0040
kFrameTime = 33                             #	0018,1063
kFrameTimeVector = 34                       #	0018,1065
kModality = 35                              #	0008,0060
kScheduledStationAETitle = 36               #	0040,0001
kScheduledPerformingPhysiciansName = 37     #	0040,0006
kSpecificCharacterSet = 38                  #	0008,0005
kAccessionNumber = 39                       #	0008,0050
kPatientSex = 40                            #	0010,0040
kPatientBirthDate = 41                      #	0010,0030
kReferringPhysiciansName = 42               #	0008,0090
kScheduledProcedureStepDescription = 43     #	0040,0007
kSeriesNumber = 44                          #	0020,0011
kInstanceNumber = 45                        #	0020,0013
kContentDate = 46                           #	0008,0023
kContentTime = 47                           #	0008,0033
kCurrentPatientLocation = 48                #	0038,0300
kReferencedSOPInstanceUID = 49              #	0008,1155
kReferencedSOPClassUID = 50                 #	0008,1150
kRequestingPhysician = 51                   #	0032,1032
kRequestedProcedureDescription = 52         #	0032,1060
kScheduledProcedureStepLocation = 53        #	0040,0011
kScheduledStationName = 54                  #	0040,0010
kScheduledProcedureStepID = 55              #	0040,0009
kScheduledProcedureStepStatus = 56          #	0040,0020
kRequestedProcedureID = 57                  #	0040,1001
kRequestedProcedurePriority = 58            #	0040,1003
kRequestingService = 59                 	#	0032,1033
kPlacerOrderNumberImagingServiceRequest = 60 #	0040,2016
kAdmissionID = 61 							#	0038,0010

imWorklist = 'WORKLIST'
imPatient = 'PATIENT'
imStudy = 'STUDY'
imPSOnly = 'PSONLY'

utNone = 'NONE'
utStudy = 'STUDY'
utSeries = 'SERIES'
utInstance = 'INSTANCE'

tsUncompr = 'UNCOMPR'
tsLittle = 'LITTLE'
tsBig = 'BIG'
tsImplicit = 'IMPLICIT'
tsLossless = 'LOSSLESS'
tsJPEG8 = 'JPEG8'
tsJPEG12 = 'JPEG12'

MedConn_Root_UID =                      '1.2.826.0.1.3680043.8.272' # creo que se generó desde http://www.medicalconnections.co.uk/Free_UID
Secondary_Capture_Image_Storage =       '1.2.840.10008.5.1.4.1.1.7'
VL_Endoscopic_Image_Storage =           '1.2.840.10008.5.1.4.1.1.77.1.1'
Video_Endoscopic_Image_Storage =        '1.2.840.10008.5.1.4.1.1.77.1.1.1'
ExplVR_Little_Endian =                  '1.2.840.10008.1.2.1'
JPEG_Baseline_TS =                      '1.2.840.10008.1.2.4.50'
MPEG2_TS =                              '1.2.840.10008.1.2.4.100'
##ERROR_MSG =                             'ERROR:';
##WARNING_MSG =                           'WARNING:';


# estructuras

class dcmKeyValue(Structure):
    _fields_ = [("key", c_int),
                ("value", c_char_p)]


# funcion de ayuda para crear parametros de tipo array

def _crear_array(tipo, lista):
    return (tipo*len(lista))(*lista)


########## WRAPPER ###############

# XXX no se aun muy bien porqué, cuando se utiliza Oracle falla la carga
# de dcm.dll sin indicar la ruta... es posible que las librerias de oracle
# canbien algo de los path, etc... asi que se ha hecho que siempre se indique
# la ruta de dcm.dll
##dcmdll = windll.dcm
##dcmdll = windll.LoadLibrary('dcm.dll')
import os
from pylons import config
dcmdll = windll.LoadLibrary( os.path.join(config['pylons.paths'].get('root_parent', ''), 'dcm.dll') )

# dcmConfig

class _dcmConfig(object):

    def __setattr__(self, name, value):
        dcmdll.dcmConfig_set(name, value)

    def __getattr__(self, name):
        dcmdll.dcmConfig_get.restype = c_int
        size = dcmdll.dcmConfig_get(name, 0)
        b = create_string_buffer('', size)
        dcmdll.dcmConfig_get(name, byref(b))
        return b.value

dcmConfig = _dcmConfig()

_callback_func = None

##def set_dcmExecOutput(callback):
##    global _callback_func
##    CALLBACKFUNC = WINFUNCTYPE(c_int, c_char_p)
####    CALLBACKFUNC = WINFUNCTYPE(c_int, c_int)
##    _callback_func = CALLBACKFUNC(callback)
##
##    return dcmdll.set_dcmExecOutput(byref(_callback_func))


# DcmDataSet

class _DataSetValues(dict):

    def __init__(self, ref):
        self._dcmDataSet = ref

    def __setitem__(self, key, value):
        if not dcmdll.dcmDataSet_setdsValue(self._dcmDataSet, key, value):
            raise DCMException('Error llamando a _DataSetValues.__setitem__(%s, %s)' % (key, value))

    def __getitem__(self, key):
        dcmdll.dcmDataSet_getdsValue.restype = c_int
        size = dcmdll.dcmDataSet_getdsValue(self._dcmDataSet, key, 0)
        b = create_string_buffer('', size)
        if not dcmdll.dcmDataSet_getdsValue(self._dcmDataSet, key, byref(b)):
            raise DCMException('Error llamando a _DataSetValues.__getitem__(%s)' % key)
        return b.value


class _MetaHeaderValues(dict):

    def __init__(self, ref):
        self._dcmDataSet = ref

    def __setitem__(self, key, value):
        if not dcmdll.dcmDataSet_setmhValue(self._dcmDataSet, key, value):
            raise DCMException('Error llamando a _MetaHeaderValues.__setitem__(%s, %s)' % (key, value))

    def __getitem__(self, key):
        dcmdll.dcmDataSet_getmhValue.restype = c_int
        size = dcmdll.dcmDataSet_getmhValue(self._dcmDataSet, key, 0)
        b = create_string_buffer('', size)
        if not dcmdll.dcmDataSet_getmhValue(self._dcmDataSet, key, byref(b)):
            raise DCMException('Error llamando a _MetaHeaderValues.__getitem__(%s)' % key)
        return b.value


class DcmDataSet(object):

    def __init__(self, ref=None):
        if ref:
            self._dcmDataSet = ref
            self.self_created = False
        else:
            self._dcmDataSet = dcmdll.dcmDataSet_Create()
            self.self_created = True
        self._datasetValues = _DataSetValues(self._dcmDataSet)
        self._metaheaderValues = _MetaHeaderValues(self._dcmDataSet)

    def __del__(self):
        if self.self_created:
            self.free()

    def free(self):
        # if self_created: return 0
        if self._dcmDataSet:
            if not dcmdll.dcmDataSet_Free(self._dcmDataSet):
                raise DCMException('Error llamando a DcmDataSet.free()')
            self._dcmDataSet = None

    def loadFromFile(self, filename):
        if not dcmdll.dcmDataSet_LoadFromFile(self._dcmDataSet, filename):
            raise DCMException('Error llamando a DcmDataSet.loadFromFile(%s)' % filename)

    def setDatasetEncoding(self, encodingUID):
        if not dcmdll.dcmDataSet_setDatasetEncoding(self._dcmDataSet, encodingUID):
            raise DCMException('Error llamando a DcmDataSet.setDatasetEncoding(%s)' % encodingUID)

    def getSequenceItem(self, key):
        # devuelve directamente un puntero a un IXMLNode de Delphi... (o nil XXX)
        dcmdll.dcmDataSet_getSequenceItem.restype = c_void_p
        return dcmdll.dcmDataSet_getSequenceItem(self._dcmDataSet, key)

    def saveToFileDCM(self, filename):
        if not dcmdll.dcmDataSet_SaveToFileDCM(self._dcmDataSet, filename):
            raise DCMException('Error llamando a DcmDataSet.saveToFileDCM(%s)' % filename)

    @property
    def datasetValues(self):
        return self._datasetValues

    @property
    def metaheaderValues(self):
        return self._metaheaderValues

##
##    dcmdll.SetValueToNode,


# DcmDataSetList

class DcmDataSetList(object):

    def __init__(self, ref):
        self._dcmDataSetList = ref

    def __del__(self):
        self.free()

    def free(self):
        if self._dcmDataSetList:
            if not dcmdll.dcmDataSetList_Free(self._dcmDataSetList):
                raise DCMException('Error llamando a DcmDataSetList.free()')
            self._dcmDataSetList = None

##    def loadFromFile(self, filename):
##        return dcmdll.dcmDataSet_LoadFromFile(self._dcmDataSet, filename)

    @property
    def dataSetCount(self):
        dcmdll.dcmDataSetList_dataSetCount.restype = c_int
        return dcmdll.dcmDataSetList_dataSetCount(self._dcmDataSetList)

    def getDataSet(self, index):
        dcmdll.dcmDataSetList_getdataSet.restype = c_void_p
        ref = dcmdll.dcmDataSetList_getdataSet(self._dcmDataSetList, index)
        if not ref:
            raise DCMException('Error llamando a DcmDataSetList.getDataSet(%s)' % str(index))
        return DcmDataSet(ref)


# set/get node values

def SetValueToNode(node, key, value):
    # node es un puntero a un IXMLNode de Delphi
    if not dcmdll.SetValueToNode(node, key, value):
        raise DCMException('Error llamando a SetValueToNode(%s, %s, %s)' % (node, key, value))

def SetValueToNode_firstchild(node, key, value):
    # node es un puntero a un IXMLNode de Delphi
    log.debug("ejecutar SetValueToNode_firstchild")
    log.debug("parametros:")
    log.debug("node: " + str(node))
    log.debug("key: " + str(key))
    log.debug("value: " + str(value))
    if not dcmdll.SetValueToNode_firstchild(node, key, value):
        raise DCMException('Error llamando a SetValueToNode_firstchild(%s, %s, %s)' % (node, key, value))

def SetNodeValue_child(node, child_num, value):
    # node es un puntero a un IXMLNode de Delphi
    if not dcmdll.SetNodeValue_child(node, child_num, value):
        raise DCMException('Error llamando a SetNodeValue_child(%s, %s, %s)' % (node, child_num, value))

def GetValueFromNode(node, key):
    # node es un puntero a un IXMLNode de Delphi
    dcmdll.GetValueFromNode.restype = c_int
    size = dcmdll.GetValueFromNode(node, key, 0)
    b = create_string_buffer('', size)
    if not dcmdll.GetValueFromNode(node, key, byref(b)):
        raise DCMException('Error llamando a GetValueFromNode(%s, %s)' % (node, key))
    return b.value

def GetValueFromNode_firstchild(node, key):
    # node es un puntero a un IXMLNode de Delphi
    dcmdll.GetValueFromNode_firstchild.restype = c_int
    size = dcmdll.GetValueFromNode_firstchild(node, key, 0)
    b = create_string_buffer('', size)
    if not dcmdll.GetValueFromNode_firstchild(node, key, byref(b)):
        raise DCMException('Error llamando a GetValueFromNode_firstchild(%s, %s)' % (node, key))
    return b.value


# dcmQuery

def dcmQuery(infModel, queryRetrieveLevel, params, dcmFile):
    v = _crear_array(dcmKeyValue, params)
    dcmdll.dcmQuery.restype = c_void_p
    dcmdll.dcmQuery.argtypes = [c_char_p, c_char_p, c_void_p, c_int, c_char_p]
    ref = dcmdll.dcmQuery(infModel, queryRetrieveLevel, byref(v), len(v), dcmFile)
    if not ref:
        raise DCMException('Error llamando a dcmQuery(%s, %s, %s, %s)' % (infModel, queryRetrieveLevel, params, dcmFile))
    return DcmDataSetList(ref)


# dcmRetrieve

def dcmRetrieve(studyUID, seriesUID, instanceUID, transferSyntax, outputFile):
    dcmdll.dcmRetrieve.restype = c_int
##    dcmdll.dcmQuery.argtypes = [c_char_p, c_char_p, c_char_p, c_char_p, c_char_p]
    if not dcmdll.dcmRetrieve(studyUID, seriesUID, instanceUID, transferSyntax, outputFile):
        raise DCMException('Error llamando a dcmRetrieve(%s, %s, %s, %s, %s)' % (studyUID, seriesUID, instanceUID, transferSyntax, outputFile))


# dcmStore

def dcmStore(transferSyntax, fileName):
    dcmdll.dcmStore.restype = c_int
    if not dcmdll.dcmStore(transferSyntax, fileName):
        raise DCMException('Error llamando a dcmStore(%s, %s)' % (transferSyntax, fileName))


# dcmConvertDCMtoBMP

def dcmConvertDCMtoBMP(dcmFile, destinationFile):
    dcmdll.dcmConvertDCMtoBMP.restype = c_int
    if not dcmdll.dcmConvertDCMtoBMP(dcmFile, destinationFile):
        raise DCMException('Error llamando a dcmConvertDCMtoBMP(%s, %s)' % (dcmFile, destinationFile))


# dcmConvertDCMtoJPG

def dcmConvertDCMtoJPG(dcmFile, destinationFile):
    dcmdll.dcmConvertDCMtoJPG.restype = c_int
    if not dcmdll.dcmConvertDCMtoJPG(dcmFile, destinationFile):
        raise DCMException('Error llamando a dcmConvertDCMtoJPG(%s, %s)' % (dcmFile, destinationFile))


# dcmGenUID

def dcmGenUID(UIDType, root):
    dcmdll.dcmGenUID.restype = c_int
    size = dcmdll.dcmGenUID(UIDType, root, 0)
    b = create_string_buffer('', size)
    if not dcmdll.dcmGenUID(UIDType, root, byref(b)):
        raise DCMException('Error llamando a dcmGenUID(%s, %s)' % (UIDType, root))
    return b.value
##    import threading
##    data = threading.local()
##    data._windll = LibraryLoader(WinDLL)
##    data._dcmdll.dcmGenUID.restype = c_int
##    size = data._dcmdll.dcmGenUID(UIDType, root, 0)
##    b = create_string_buffer('', size)
##    _dcmdll.dcmGenUID(UIDType, root, byref(b))
##    del data._windll
##    del data
##    return b.value


def fileToPixelData(filename):
    dcmdll.fileToPixelData.restype = c_int
    size = dcmdll.fileToPixelData(filename, 0)
    b = create_string_buffer('', size)
    if not dcmdll.fileToPixelData(filename, byref(b)):
        raise DCMException('Error llamando a fileToPixelData(%s)' % filename)
    return b.value


def _pixels_generator(img, pixels):
    for y in range(img.size[1]):
        for x in range(img.size[0]):
            yield pixels[x, y][0]
            yield pixels[x, y][1]
            yield pixels[x, y][2]

def pixelsToPixelData(img, pixels):
    # "img" es un objeto Image de PIL
    # "pixels" es un objeto PixelAccess de PIL, devuelto al llamat al metodo load() de la imagen
    return '\\'.join( ( hex(n).split('x')[1] ) for n in _pixels_generator(img, pixels))


def DICOMDate(fecha):
    # fecha    ha de ser un date
    if isinstance(fecha, date):
        if fecha.year < 1900:
            return str(fecha.year) + fecha.replace(year=1900).strftime("%m%d")
        else:
            return fecha.strftime("%Y%m%d")
    else:
        return ''


def DICOMTime(hora):
    # hora     ha de ser un time
    if isinstance(hora, time):
        return hora.strftime("%H%M%S")
    else:
        return ''

def SetLogDir(directory):
    dcmdll.SetLogDir.restype = c_int
    if not dcmdll.SetLogDir(directory):
        raise DCMException('Error llamando a SetLogDir(%s)' % directory)
    global logdir
    logdir = directory
