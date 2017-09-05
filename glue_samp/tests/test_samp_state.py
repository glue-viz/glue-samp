import time
from mock import MagicMock

from numpy.testing import assert_equal

from astropy.io import fits
from astropy.table import Table
from astropy.samp import SAMPHubServer, SAMPIntegratedClient

from glue.core.subset import ElementSubsetState
from glue.core import Data

from ..samp_state import SAMPState


class TestSAMPState():

    def setup_method(self, method):
        self.state = SAMPState()
        self.client = SAMPIntegratedClient()

    def test_start_builtin_hub(self):
        assert not self.state.connected
        assert self.state.status == 'Not connected to SAMP Hub'
        self.state.start_samp()
        assert self.state.connected
        assert self.state.status == 'Connected to (glue) SAMP Hub'
        self.state.stop_samp()
        assert not self.state.connected
        assert self.state.status == 'Not connected to SAMP Hub'

    def test_start_external_hub(self):
        assert not self.state.connected
        assert self.state.status == 'Not connected to SAMP Hub'
        self.hub = SAMPHubServer()
        self.hub.start()
        self.state.start_samp()
        assert self.state.connected
        assert self.state.status == 'Connected to SAMP Hub'
        self.state.stop_samp()
        assert not self.state.connected
        assert self.state.status == 'Not connected to SAMP Hub'

    def test_metadata(self):
        self.state.start_samp()
        self.client.connect()
        for client in self.client.get_registered_clients():
            if 'hub' not in client:
                metadata = self.client.get_metadata(client)
                break
        else:
            raise Exception("Client not found")
        assert metadata['samp.name'] == 'glueviz'

    def test_send_data(self):

        receiver = MagicMock()

        def receiver_func(private_key, sender_id, msg_id, mtype, params, extra):
            receiver(private_key, sender_id, msg_id, mtype, params, extra)

        self.state.start_samp()

        self.client.connect()
        self.client.bind_receive_call('*', receiver_func)
        self.client.bind_receive_notification('*', receiver_func)

        data1d = Data(x=[1, 2, 3])
        self.state.send_data(layer=data1d, client=self.client.get_public_id())

        while len(receiver.call_args_list) == 2:
            time.sleep(0.1)

        args, kwargs = receiver.call_args_list[-1]
        assert args[3] == 'table.load.votable'
        assert 'url' in args[4]
        assert 'table-id' in args[4]

        t = Table.read(args[4]['url'], format='votable')
        assert_equal(t['x'], [1, 2, 3])

        receiver.reset_mock()

        data2d = Data(a=[[1, 2], [3, 4]])
        self.state.send_data(layer=data2d)

        while len(receiver.call_args_list) == 0:
            time.sleep(0.1)

        args, kwargs = receiver.call_args_list[-1]
        assert args[3] == 'image.load.fits'
        assert 'url' in args[4]
        assert 'image-id' in args[4]

        hdu = fits.open(args[4]['url'], format='votable')[0]
        assert_equal(hdu.data, [[1, 2], [3, 4]])

        receiver.reset_mock()

        subset1d = data1d.new_subset()
        subset1d.subset_state = ElementSubsetState([0, 2])

        self.state.send_data(layer=subset1d)

        while len(receiver.call_args_list) == 0:
            time.sleep(0.1)

        args, kwargs = receiver.call_args_list[-1]
        assert args[3] == 'table.select.rowList'
        assert 'table-id' in args[4]

        assert_equal(args[4]['row-list'], ['0', '2'])
