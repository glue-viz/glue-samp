from __future__ import print_function, division, absolute_import

import os

from glue import __version__ as glue_version
from glue.external.echo import CallbackProperty
from glue.core.state_objects import State

from astropy.samp import SAMPHubServer, SAMPIntegratedClient, SAMPHubError

ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'glue_samp_icon.png')


class SAMPState(State):

    status = CallbackProperty('Not connected to SAMP Hub')
    connected = CallbackProperty(False)

    def __init__(self):
        super(SAMPState, self).__init__()
        self.hub = SAMPHubServer()
        self.client = SAMPIntegratedClient()
        self.add_callback('connected', self.declare_metadata)

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

    def declare_metadata(self, *args):
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
