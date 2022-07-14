import os
from pylons.i18n import _
from base import BasePyDICOM
from pydicom.dataset import Dataset
from pynetdicom import AE, PYNETDICOM_IMPLEMENTATION_UID, PYNETDICOM_IMPLEMENTATION_VERSION, evt, StoragePresentationContexts
from pynetdicom.events import EVT_C_STORE
from pynetdicom.sop_class import PatientRootQueryRetrieveInformationModelGet, SecondaryCaptureImageStorage, PatientRootQueryRetrieveInformationModelMove
from pynetdicom.presentation import build_role
import threading
qr_lock = threading.Lock()

class QRRequest(BasePyDICOM):
    
    requested_context = None
    path_destination = None
    handlers = None
    qr_mode = None
    scp = None
    # Stored es un flag que se pone a true cuando la imagen ya esta grabada en disco
    stored = False
    # Finished es un flag que indica cunado ha terminado el handle
    finished = False
    ds_query=None
    scp_cstore_ae = None
    scp_cstore_port = None

    def __init__(self, conf=None, qrmode=None):
        
        self.qr_mode = qrmode
        super(QRRequest, self).__init__(conf)

    def set_requested_context(self):
        if self.qr_mode == 'c-move':
            self.ae.add_requested_context(PatientRootQueryRetrieveInformationModelMove)
        if self.qr_mode == 'c-get':
            self.ae.add_requested_context(PatientRootQueryRetrieveInformationModelGet)
            self.ae.add_requested_context(SecondaryCaptureImageStorage)

    def handle_store(self, event):
        """ Administra el almacenaje del dcm 
            Este metodo por alguna razon no se llama con la instancia, 
            por lo que si se hace self.ATRIBUTO, se usaran los atributos del
            primera instancia.
        """   
        try:
            
            ds = event.dataset
            context = event.context
            # Add the DICOM File Meta Information
            meta = Dataset()
            meta.MediaStorageSOPClassUID = ds.SOPClassUID
            meta.MediaStorageSOPInstanceUID = ds.SOPInstanceUID
            meta.ImplementationClassUID = PYNETDICOM_IMPLEMENTATION_UID
            meta.ImplementationVersionName = PYNETDICOM_IMPLEMENTATION_VERSION
            meta.TransferSyntaxUID = context.transfer_syntax
            file_to_save = os.path.join(self.path_destination,ds.SOPInstanceUID+'.dcm')

            # Add the file meta to the dataset
            ds.file_meta = meta

            # Set the transfer syntax attributes of the dataset
            ds.is_little_endian = context.transfer_syntax.is_little_endian
            ds.is_implicit_VR = context.transfer_syntax.is_implicit_VR
            # Save the dataset using the SOP Instance UID as the filename
            ds.save_as(file_to_save, write_like_original=False)
            
        except Exception,e:
            print str(e)
            #return 0x0000
                
        print "saved:" + file_to_save
        # Return a 'Success' status
        return 0x0000

    def is_stored(self):
        return self.stored
        
    def is_finished(self):
        return self.finished
        
    def create_dataset_query(self, patient, study, series, sop):
        # Create out identifier (query) dataset
        ds = Dataset()
        ds.QueryRetrieveLevel = 'IMAGE'
        # Unique key for PATIENT level
        ds.PatientID = patient
        # Unique key for STUDY level
        ds.StudyInstanceUID = study
        # Unique key for SERIES level
        ds.SeriesInstanceUID = series
        # Unique Key for SOP Level
        ds.SOPInstanceUID = sop
        return ds

    def hook_pre_associate(self):
    
        global qr_lock
        qr_lock.acquire()
        self.handlers = [(evt.EVT_C_STORE, self.handle_store)]

        if self.qr_mode == 'c-move':
            
            self.scp_cstore_ae = self.conf['connection_data']['calling_ae']
            self.scp_cstore_port = self.conf['connection_data']['calling_ae_port']
        
            # Add the Storage SCP's supported presentation contexts
            self.ae.supported_contexts = StoragePresentationContexts
            # Start our Storage SCP in non-blocking mode, listening on port 11120
            self.ae.ae_title = self.scp_cstore_ae
            self.scp = self.ae.start_server(('', self.scp_cstore_port), block=False, evt_handlers=self.handlers)
            print "start:" 
        if self.qr_mode == 'c-get':
            # Create an SCP/SCU Role Selection Negotiation item for CT Image Storage
            role = build_role(SecondaryCaptureImageStorage, scp_role=True)
            self.ext_neg = [role]
            self.evt_handlers = self.handlers

        

    def get_image(self, patient, study, series, sop, destination):
        self.path_destination = destination
        self.ds_query = self.create_dataset_query(patient,study,series,sop)

        if self.qr_mode == 'c-move':
            self.get_image_move(patient, study, series, sop)
        if self.qr_mode == 'c-get':
            self.get_image_get(patient, study, series, sop)

    def get_image_move(self, patient, study, series, sop):
        try:
            if self.assoc.is_established:
                # Use the C-MOVE service to send the identifier
                # A query_model value of 'P' means use the 'Patient Root Query
                #   Retrieve Information Model - Move' presentation context
                responses = self.assoc.send_c_move(self.ds_query, self.scp_cstore_ae, query_model='P')

                for (status, identifier) in responses:
                    if status:
                        print('C-MOVE query status: 0x{0:04x}'.format(status.Status))
                        
                        # If the status is 'Pending' then `identifier` is the C-MOVE response
                        if status.Status in (0xFF00, 0xFF01):
                            print(identifier)
                        
                    else:
                        print('Connection timed out, was aborted or received invalid response')

                # Release the association
                self.assoc.release()
            else:
                print('Association rejected, aborted or never connected')

            # Stop our Storage SCP
            file_to_save = os.path.join(self.path_destination,sop+'.dcm')
            if os.path.exists(file_to_save):
                self.stored=True
                
            self.finished=True
            self.scp.shutdown()
        finally:
            global qr_lock
            qr_lock.release()

    def get_image_get(self, patient, study, series, sop):

        if self.assoc.is_established:
            # Use the C-GET service to send the identifier
            # A query_model value of 'P' means use the 'Patient Root Query Retrieve
            #     Information Model - Get' presentation context
            responses = self.assoc.send_c_get(self.ds_query, query_model='P')

            for (status, identifier) in responses: 
                if status:
                    print('C-GET query status: 0x{0:04x}'.format(status.Status))

                    # If the status is 'Pending' then `identifier` is the C-GET response
                    if status.Status in (0xFF00, 0xFF01):
                        print(identifier)
                else:
                    print('Connection timed out, was aborted or received invalid response')

            # Release the association
            self.assoc.release()
        else:
            print('Association rejected, aborted or never connected')