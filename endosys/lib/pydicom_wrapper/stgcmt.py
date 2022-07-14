from base import BasePyDICOM
from pydicom.dataset import Dataset

class StgcmtRequest(BasePyDICOM):
    pass

"""
Ejemplo del n_action 
def test_unknown_msg(self):
        self.ae = ae = AE()
        ae.add_supported_context(ModalityPerformedProcedureStepSOPClass)
        ae.add_requested_context(ModalityPerformedProcedureStepSOPClass)
        scp = ae.start_server(('', 11112), block=False)

        ae.acse_timeout = 5
        ae.dimse_timeout = 5
        assoc = ae.associate('localhost', 11112)
        assert assoc.is_established
        status, ds = assoc.send_n_action(
            self.ds,
            1,
            ModalityPerformedProcedureStepSOPClass,
            '1.2.3.4'
        )
        assert assoc.is_aborted
"""