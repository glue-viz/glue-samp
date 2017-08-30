from qtpy.QtCore import QObject, Signal

from glue.config import menubar_plugin
from glue.logger import logger
from glue.core.data_factories.astropy_table import (astropy_tabular_data_votable,
                                                    astropy_tabular_data_fits)
from glue.core.edit_subset_mode import EditSubsetMode
from glue.core.subset import ElementSubsetState

from astropy.samp import SAMPIntegratedClient

# http://wiki.ivoa.net/twiki/bin/view/IVOA/SampMTypes#table_load


class GlueSAMPReceiver(QObject):

    call_received = Signal(object, object, object, object, object, object)
    notification_received = Signal(object, object, object, object, object, object)

    def __init__(self, data_collection):

        super(GlueSAMPReceiver, self).__init__()

        self.data_collection = data_collection

        self.client = SAMPIntegratedClient()
        self.client.connect()

        self.client.bind_receive_call("*", self._receive_call)
        self.client.bind_receive_notification("*", self._receive_notification)

        self.call_received.connect(self.receive_call)
        self.notification_received.connect(self.receive_notification)

    def _receive_call(self, private_key, sender_id, msg_id, mtype, params, extra):
        logger.info('SAMP: received call - sender_id={0} msg_id={1} mtype={2} params={3} extra={4}'.format(sender_id, msg_id, mtype, params, extra))
        self.call_received.emit(private_key, sender_id, msg_id, mtype, params, extra)
        self.client.reply(msg_id, {"samp.status": "samp.ok", "samp.result": {}})

    def receive_call(self, private_key, sender_id, msg_id, mtype, params, extra):
        logger.info('SAMP: received call [main] - sender_id={0} msg_id={1} mtype={2} params={3} extra={4}'.format(sender_id, msg_id, mtype, params, extra))

        if mtype == 'table.load.votable':

            if self.table_id_exists(params['table-id']):
                return

            data = astropy_tabular_data_votable(params['url'])
            data.label = params['name']
            data.meta['samp-table-id'] = params['table-id']

            self.data_collection.append(data)

        elif mtype == 'table.load.fits':

            if self.table_id_exists(params['table-id']):
                return

            data = astropy_tabular_data_fits(params['url'])
            data.label = params['name']
            data.meta['samp-table-id'] = params['table-id']

            self.data_collection.append(data)

    def table_id_exists(self, table_id):
        for data in self.data_collection:
            if data.meta['samp-table-id'] == table_id:
                return True
        else:
            return False

    def data_from_table_id(self, table_id):
        for data in self.data_collection:
            if data.meta['samp-table-id'] == table_id:
                return data
        else:
            raise Exception("Table {0} not found".format(table_id))

    def _receive_notification(self, private_key, sender_id, msg_id, mtype, params, extra):
        logger.info('SAMP: received notification - sender_id={0} msg_id={1} mtype={2} params={3} extra={4}'.format(sender_id, msg_id, mtype, params, extra))
        self.notification_received.emit(private_key, sender_id, msg_id, mtype, params, extra)

    def receive_notification(self, private_key, sender_id, msg_id, mtype, params, extra):
        logger.info('SAMP: received notification [main] - sender_id={0} msg_id={1} mtype={2} params={3} extra={4}'.format(sender_id, msg_id, mtype, params, extra))

        if mtype == 'table.highlight.row':

            data = self.data_from_table_id(params['table-id'])
            len(self.data_collection.subset_groups)

            subset_state = ElementSubsetState(indices=[params['row']], data=data)

            mode = EditSubsetMode()
            mode.update(self.data_collection, subset_state)


receiver = None


@menubar_plugin("Open SAMP plugin")
def samp_plugin(session, data_collection):
    global receiver
    if receiver is None:
        receiver = GlueSAMPReceiver(data_collection)
