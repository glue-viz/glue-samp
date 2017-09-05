import os
import time

from numpy.testing import assert_equal

from astropy.table import Table
from astropy.samp import SAMPIntegratedClient

from glue.core import DataCollection

from ..samp_state import SAMPState
from ..samp_receiver import SAMPReceiver


class TestSAMPReceiver():

    def setup_method(self, method):
        self.state = SAMPState()
        self.data_collection = DataCollection()
        self.receiver = SAMPReceiver(state=self.state,
                                     data_collection=self.data_collection)
        self.state.start_samp()
        self.client = SAMPIntegratedClient()
        self.client.connect()

    def test_receive_table(self, tmpdir):
        filename = tmpdir.join('test.votable').strpath
        t = Table()
        t['a'] = [1, 2, 3]
        t.write(filename, format='votable')
        message = {}
        message['samp.mtype'] = 'table.load.votable'
        message['samp.params'] = {}
        message['samp.params']['url'] = 'file://' + os.path.abspath(filename)
        message['samp.params']['table-id'] = 'testing'
        self.client.call_all('tag', message)
        print(len(self.data_collection))
        while len(self.data_collection) == 0:
            time.sleep(0.1)
        assert_equal(self.data_collection[0]['a'], [1, 2, 3])

        # ABOVE FAILS AS NOT REGISTERED
