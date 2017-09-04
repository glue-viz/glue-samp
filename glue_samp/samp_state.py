from __future__ import print_function, division, absolute_import

import os
import uuid
import tempfile
from fnmatch import fnmatch

import numpy as np

from glue import __version__ as glue_version
from glue.core import Data
from glue.external.echo import CallbackProperty
from glue.core.state_objects import State

from glue.core.data_exporters.gridded_fits import fits_writer
from glue.core.data_exporters.astropy_table import data_to_astropy_table
from astropy.samp import SAMPHubServer, SAMPIntegratedClient, SAMPHubError

ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'glue_samp_icon.png')


class SAMPState(State):

    status = CallbackProperty('Not connected to SAMP Hub')
    connected = CallbackProperty(False)
    clients = CallbackProperty([])
    highlight_is_selection = CallbackProperty(False)

    def __init__(self):
        super(SAMPState, self).__init__()
        self.hub = SAMPHubServer()
        self.client = SAMPIntegratedClient()
        self.add_callback('connected', self.on_connected)

    def start_samp(self):
        if not self.client.is_connected:
            try:
                self.client.connect()
            except SAMPHubError:
                try:
                    self.hub.start()
                    self.client.connect()
                except Exception:
                    self.connected = False
                    self.status = 'Could not connect to Hub'
                else:
                    self.connected = True
                    self.status = 'Connected to (glue) SAMP Hub'
            except:
                self.connected = False
                self.status = 'Could not connect to Hub'
            else:
                self.connected = True
                self.status = 'Connected to SAMP Hub'

    def stop_samp(self):
        if self.client.is_connected:
            self.client.disconnect()
        if self.hub.is_running:
            self.hub.stop()
        self.connected = False
        self.status = 'Not connected to SAMP Hub'

    def on_connected(self, *args):
        if self.connected:
            metadata = {'author.email': 'thomas.robitaille@gmail.com',
                        'author.name': 'Thomas Robitaille',
                        'home.page': 'http://www.glueviz.org',
                        'samp.description.text': 'Multi-dimensional linked data exploration',
                        'samp.documentation.url': 'http://www.glueviz.org',
                        'samp.icon.url': 'file://' + ICON_PATH,
                        'samp.name': 'glueviz',
                        'glue.version': glue_version}
            self.client.declare_metadata(metadata)
            self.on_client_change()

    def on_client_change(self):
        clients = []
        for client in self.client.get_registered_clients():
            metadata = self.client.get_metadata(client)
            clients.append((client, metadata.get('samp.name', client)))
        self.clients = clients

    def send_data(self, layer=None, client=None):

        filename = tempfile.mktemp()

        message = {}
        message["samp.params"] = {}

        if isinstance(layer, Data):

            if layer.ndim == 1:
                table = data_to_astropy_table(layer)
                table.write(filename, format='votable')
                message["samp.mtype"] = "table.load.votable"
                if 'samp-table-id' not in layer.meta:
                    layer.meta['samp-table-id'] = str(uuid.uuid4())
                message["samp.params"]['table-id'] = layer.meta['samp-table-id']
            elif layer.ndim == 2:
                fits_writer(filename, layer)
                message["samp.mtype"] = "image.load.fits"
                if 'samp-image-id' not in layer.meta:
                    layer.meta['samp-image-id'] = str(uuid.uuid4())
                message["samp.params"]['image-id'] = layer.meta['samp-image-id']
            else:
                return

            message["samp.params"]['name'] = layer.label
            message["samp.params"]['url'] = 'file://' + os.path.abspath(filename)

        else:

            message['samp.mtype'] = 'table.select.rowList'

            if layer.ndim == 1:
                message["samp.params"]['table-id'] = layer.data.meta['samp-table-id']
                message["samp.params"]['row-list'] = np.nonzero(layer.to_mask())[0].astype(str).tolist()
            else:
                return

        if client is None:
            self.client.notify_all(message)
        else:
            # Make sure client is subscribed otherwise an exception is raised
            subscriptions = self.client.get_subscriptions(client)
            for mtype in subscriptions:
                if fnmatch(message['samp.mtype'], mtype):
                    self.client.notify(client, message)
                    return
            else:
                return
