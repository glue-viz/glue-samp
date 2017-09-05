import os
import time

import pytest
import numpy as np
from numpy.testing import assert_equal

from astropy.io import fits
from astropy.table import Table
from astropy.samp import SAMPIntegratedClient

from glue.core import DataCollection

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
