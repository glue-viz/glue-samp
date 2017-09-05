import os
import time

import pytest
import numpy as np
from numpy.testing import assert_equal

from astropy.io import fits
from astropy.table import Table
from astropy.samp import SAMPIntegratedClient

from glue.core import Data, DataCollection
from glue.core.edit_subset_mode import EditSubsetMode

from ..samp_state import SAMPState
from ..samp_client import SAMPClient


class TestSAMPClient():

    def setup_method(self, method):

        self.state = SAMPState()

        self.data_collection = DataCollection()

        self.client = SAMPClient(state=self.state,
                                 data_collection=self.data_collection)
        self.state.start_samp()
        self.client.register()

        self.client2 = SAMPIntegratedClient()
        self.client2.connect()

        mode = EditSubsetMode()
        mode.edit_subset = []
        mode.data_collection = self.data_collection

    def teardown_method(self, method):
        self.client2.disconnect()
        self.client.unregister()
        self.state.stop_samp()

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

        self.client2.call_all('tag', message)

        while len(self.data_collection) == 0:
            time.sleep(0.1)

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

        self.client2.call_all('tag', message)

        while len(self.data_collection) == 0:
            time.sleep(0.1)

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

        self.client2.call_all('tag', message)

        assert len(d.subsets) == 0

        self.state.highlight_is_selection = True

        self.client2.call_all('tag', message)

        while len(d.subsets) == 0:
            time.sleep(0.1)

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

        self.client2.call_all('tag', message)

        while len(d.subsets) == 0:
            time.sleep(0.1)

        assert len(d.subsets) == 1
        assert_equal(d.subsets[0].to_mask(), [1, 0, 1])

    def test_receive_client_change(self):

        assert len(self.state.clients) == 1

        self.state.on_client_change()

        assert len(self.state.clients) == 2

        client = SAMPIntegratedClient()
        client.connect()

        while len(self.state.clients) == 2:
            time.sleep(0.1)

        assert len(self.state.clients) == 3
        client_id = client.get_public_id()
        assert (client_id, client_id) in self.state.clients

        client.disconnect()

        assert len(self.state.clients) == 2
