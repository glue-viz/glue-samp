import os
import time

import pytest
from mock import MagicMock

import numpy as np
from numpy.testing import assert_equal

from astropy.io import fits
from astropy.table import Table

try:
    from astropy.samp import SAMPHubServer, SAMPIntegratedClient
except ImportError:
    from astropy.vo.samp import SAMPHubServer, SAMPIntegratedClient

from glue.core import Data, DataCollection
from glue.core.subset import ElementSubsetState
from glue.core.edit_subset_mode import EditSubsetMode

from ..samp_state import SAMPState
from ..samp_client import SAMPClient


class WaitMixin():

    def wait(self, exit_condition):
        for iter in range(50):
            if exit_condition(self):
                break
            time.sleep(0.1)
        else:
            raise Exception("Timed out while waiting for exit condition")


class TestSAMPClientConnectSend(WaitMixin):

    def setup_method(self, method):
        self.state = SAMPState()
        self.data_collection = DataCollection()
        self.client = SAMPClient(state=self.state,
                                 data_collection=self.data_collection)
        self.client_ext = SAMPIntegratedClient()

    def teardown_method(self, method):
        self.client_ext.disconnect()
        self.client.stop_samp()

    def test_start_builtin_hub(self):
        assert not self.state.connected
        assert self.state.status == 'Not connected to SAMP Hub'
        self.client.start_samp()
        assert self.state.connected
        assert self.state.status == 'Connected to (glue) SAMP Hub'
        self.client.stop_samp()
        assert not self.state.connected
        assert self.state.status == 'Not connected to SAMP Hub'

    def test_start_external_hub(self):
        assert not self.state.connected
        assert self.state.status == 'Not connected to SAMP Hub'
        self.hub = SAMPHubServer()
        self.hub.start()
        self.client.start_samp()
        assert self.state.connected
        assert self.state.status == 'Connected to SAMP Hub'
        self.client.stop_samp()
        assert not self.state.connected
        assert self.state.status == 'Not connected to SAMP Hub'

    def test_metadata(self):
        self.client.start_samp()
        self.client_ext.connect()
        for client in self.client_ext.get_registered_clients():
            if 'hub' not in client:
                metadata = self.client_ext.get_metadata(client)
                break
        else:
            raise Exception("Client not found")
        assert metadata['samp.name'] == 'glueviz'

    def test_send_data(self):

        receiver = MagicMock()

        def receiver_func(private_key, sender_id, msg_id, mtype, params, extra):
            receiver(private_key, sender_id, msg_id, mtype, params, extra)

        self.client.start_samp()

        self.client_ext.connect()
        self.client_ext.bind_receive_call('*', receiver_func)
        self.client_ext.bind_receive_notification('*', receiver_func)

        data1d = Data(x=[1, 2, 3])
        self.client.send_data(layer=data1d, client=self.client_ext.get_public_id())

        self.wait(lambda x: len(receiver.call_args_list) == 3)

        args, kwargs = receiver.call_args_list[-1]
        assert args[3] == 'table.load.votable'
        assert 'url' in args[4]
        assert 'table-id' in args[4]

        t = Table.read(args[4]['url'], format='votable')
        assert_equal(t['x'], [1, 2, 3])

        receiver.reset_mock()

        data2d = Data(a=[[1, 2], [3, 4]])
        self.client.send_data(layer=data2d)

        self.wait(lambda x: len(receiver.call_args_list) == 1)

        args, kwargs = receiver.call_args_list[-1]
        assert args[3] == 'image.load.fits'
        assert 'url' in args[4]
        assert 'image-id' in args[4]

        hdu = fits.open(args[4]['url'], format='votable')[0]
        assert_equal(hdu.data, [[1, 2], [3, 4]])

        receiver.reset_mock()

        subset1d = data1d.new_subset()
        subset1d.subset_state = ElementSubsetState([0, 2])

        self.client.send_data(layer=subset1d)

        self.wait(lambda x: len(receiver.call_args_list) == 1)

        args, kwargs = receiver.call_args_list[-1]
        assert args[3] == 'table.select.rowList'
        assert 'table-id' in args[4]

        assert_equal(args[4]['row-list'], ['0', '2'])


class TestSAMPClientReceive(WaitMixin):

    def setup_method(self, method):

        self.state = SAMPState()

        self.data_collection = DataCollection()

        self.client = SAMPClient(state=self.state,
                                 data_collection=self.data_collection)
        self.client.start_samp()
        self.client.register()

        self.client_ext = SAMPIntegratedClient()
        self.client_ext.connect()

        mode = EditSubsetMode()
        mode.edit_subset = []
        mode.data_collection = self.data_collection

    def teardown_method(self, method):
        self.client_ext.disconnect()
        self.client.unregister()
        self.client.stop_samp()

    @pytest.mark.parametrize('fmt', ['fits', 'votable'])
    def test_receive_table_votable(self, tmpdir, fmt):

        filename = tmpdir.join('test').strpath
        t = Table()
        t['a'] = [1, 2, 3]
        t.write(filename, format=fmt)

        message = {}
        message['samp.mtype'] = 'table.load.' + fmt
        message['samp.params'] = {}
        message['samp.params']['url'] = 'file://' + os.path.abspath(filename)
        message['samp.params']['table-id'] = 'testing'
        message['samp.params']['name'] = 'test_table'

        self.client_ext.call_all('tag', message)

        self.wait(lambda x: len(x.data_collection) == 1)

        assert_equal(self.data_collection[0]['a'], [1, 2, 3])
        assert self.data_collection[0].label == 'test_table'

    def test_receive_image(self, tmpdir):

        filename = tmpdir.join('test').strpath
        image = np.array([[1, 2], [3, 4]])
        fits.writeto(filename, image)

        message = {}
        message['samp.mtype'] = 'image.load.fits'
        message['samp.params'] = {}
        message['samp.params']['url'] = 'file://' + os.path.abspath(filename)
        message['samp.params']['image-id'] = 'testing'
        message['samp.params']['name'] = 'test_image'

        self.client_ext.call_all('tag', message)

        self.wait(lambda x: len(x.data_collection) == 1)

        assert_equal(self.data_collection[0]['PRIMARY'], [[1, 2], [3, 4]])
        assert self.data_collection[0].label == 'test_image'

    def test_receive_highlight(self, tmpdir):

        d = Data(a=[1, 2, 3], label='test')
        d.meta['samp-table-id'] = 'table-123'
        self.data_collection.append(d)

        message = {}
        message['samp.mtype'] = 'table.highlight.row'
        message['samp.params'] = {}
        message['samp.params']['table-id'] = 'table-123'
        message['samp.params']['row'] = 1

        self.client_ext.call_all('tag', message)

        assert len(d.subsets) == 0

        self.state.highlight_is_selection = True

        self.client_ext.call_all('tag', message)

        self.wait(lambda x: len(d.subsets) == 1)

        assert len(d.subsets) == 1
        assert_equal(d.subsets[0].to_mask(), [0, 1, 0])

    def test_receive_row_list(self, tmpdir):

        d = Data(a=[1, 2, 3], label='test')
        d.meta['samp-table-id'] = 'table-123'
        self.data_collection.append(d)

        message = {}
        message['samp.mtype'] = 'table.select.rowList'
        message['samp.params'] = {}
        message['samp.params']['table-id'] = 'table-123'
        message['samp.params']['row-list'] = [0, 2]

        self.client_ext.call_all('tag', message)

        self.wait(lambda x: len(d.subsets) == 1)

        assert len(d.subsets) == 1
        assert_equal(d.subsets[0].to_mask(), [1, 0, 1])

    def test_receive_client_change(self):

        self.wait(lambda x: len(x.state.clients) == 2)

        client = SAMPIntegratedClient()
        client.connect()

        self.wait(lambda x: len(x.state.clients) == 3)

        assert len(self.state.clients) == 3
        client_id = client.get_public_id()
        assert (client_id, client_id) in self.state.clients

        client.disconnect()

        self.wait(lambda x: len(x.state.clients) == 2)

        assert len(self.state.clients) == 2
