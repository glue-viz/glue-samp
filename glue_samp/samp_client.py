from __future__ import print_function, division, absolute_import

import os
import uuid
import tempfile
from fnmatch import fnmatch

import numpy as np

try:
    from astropy.samp import SAMPClientError, SAMPHubServer, SAMPIntegratedClient, SAMPHubError
except ImportError:
    from astropy.vo.samp import SAMPClientError, SAMPHubServer, SAMPIntegratedClient, SAMPHubError

from glue import __version__ as glue_version
from glue.core import Data
from glue.logger import logger
from glue.core.data_factories.astropy_table import (astropy_tabular_data_votable,
                                                    astropy_tabular_data_fits)
from glue.core.data_factories.fits import fits_reader
from glue.core.data_exporters.gridded_fits import fits_writer
from glue.core.data_exporters.astropy_table import data_to_astropy_table
from glue.core.edit_subset_mode import EditSubsetMode
from glue.core.subset import ElementSubsetState
from glue.external.echo import delay_callback


__all__ = ['SAMPClient']

ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'glue_samp_icon.png')

MTYPES = ['table.load.votable',
          'table.load.fits',
          'table.highlight.row',
          'table.select.rowList',
          'image.load.fits',
          'samp.hub.event.register',
          'samp.hub.event.unregister']


class SAMPClient(object):

    def __init__(self, state=None, data_collection=None):
        self.state = state
        self.data_collection = data_collection
        self.hub = SAMPHubServer()
        self.client = SAMPIntegratedClient()
        self.state.add_callback('connected', self.on_connected)

    def start_samp(self):
        if not self.client.is_connected:
            try:
                self.client.connect()
            except SAMPHubError:
                try:
                    self.hub.start()
                    self.client.connect()
                except Exception:
                    with delay_callback(self.state, 'connected', 'status'):
                        self.state.connected = False
                        self.state.status = 'Could not connect to Hub'
                else:
                    with delay_callback(self.state, 'connected', 'status'):
                        self.state.connected = True
                        self.state.status = 'Connected to (glue) SAMP Hub'
            except:
                with delay_callback(self.state, 'connected', 'status'):
                    self.state.connected = False
                    self.state.status = 'Could not connect to Hub'
            else:
                with delay_callback(self.state, 'connected', 'status'):
                    self.state.connected = True
                    self.state.status = 'Connected to SAMP Hub'
            self.update_clients()

    def stop_samp(self):
        if self.client.is_connected:
            self.client.disconnect()
        if self.hub.is_running:
            self.hub.stop()
        self.state.connected = False
        self.state.status = 'Not connected to SAMP Hub'
        self.state.clients = []

    def register(self):
        for mtype in MTYPES:
            self.client.bind_receive_call(mtype, self.receive_call)
            self.client.bind_receive_notification(mtype, self.receive_notification)

    def unregister(self):
        try:
            for mtype in MTYPES:
                self.client.unbind_receive_call(mtype)
                self.client.unbind_receive_notification(mtype)
        except (AttributeError, SAMPClientError):
            pass

    def on_connected(self, *args):
        if self.state.connected:
            metadata = {'author.email': 'thomas.robitaille@gmail.com',
                        'author.name': 'Thomas Robitaille',
                        'home.page': 'http://www.glueviz.org',
                        'samp.description.text': 'Multi-dimensional linked data exploration',
                        'samp.documentation.url': 'http://www.glueviz.org',
                        'samp.icon.url': 'file://' + ICON_PATH,
                        'samp.name': 'glueviz',
                        'glue.version': glue_version}
            self.client.declare_metadata(metadata)
            self.update_clients()

    def update_clients(self):
        clients = []
        for client in self.client.get_registered_clients():
            metadata = self.client.get_metadata(client)
            clients.append((client, metadata.get('samp.name', client)))
        self.state.clients = clients

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

    def receive_call(self, private_key, sender_id, msg_id, mtype, params, extra):
        self.receive_message(private_key, sender_id, msg_id, mtype, params, extra)
        self.client.reply(msg_id, {"samp.status": "samp.ok", "samp.result": {}})

    def receive_notification(self, private_key, sender_id, msg_id, mtype, params, extra):
        self.receive_message(private_key, sender_id, msg_id, mtype, params, extra)

    def receive_message(self, private_key, sender_id, msg_id, mtype, params, extra):

        logger.info('SAMP: received message - sender_id={0} msg_id={1} mtype={2} '
                    'params={3} extra={4}'.format(sender_id, msg_id, mtype,
                                                  params, extra))

        if mtype.startswith('table.load'):

            if self.table_id_exists(params['table-id']):
                logger.info('SAMP: table with table-id={0} has already '
                            'been read in'.format(params['table-id']))
                return

            logger.info('SAMP: loading table with table-id={0}'.format(params['table-id']))

            if mtype == 'table.load.votable':
                data = astropy_tabular_data_votable(params['url'])
            elif mtype == 'table.load.fits':
                data = astropy_tabular_data_fits(params['url'])
            else:
                logger.info('SAMP: unknown format {0}'.format(mtype.split('.')[-1]))
                return

            if 'name' in params:
                data.label = params['name']

            if 'table-id' in params:
                data.meta['samp-table-id'] = params['table-id']

            self.data_collection.append(data)

        elif mtype.startswith('image.load'):

            if self.image_id_exists(params['image-id']):
                logger.info('SAMP: image with image-id={0} has already '
                            'been read in'.format(params['image-id']))
                return

            logger.info('SAMP: loading image with image-id={0}'.format(params['image-id']))

            if mtype == 'image.load.fits':
                data = fits_reader(params['url'])[0]
            else:
                logger.info('SAMP: unknown format {0}'.format(mtype.split('.')[-1]))
                return

            if 'name' in params:
                data.label = params['name']

            if 'image-id' in params:
                data.meta['samp-image-id'] = params['image-id']

            self.data_collection.append(data)

        elif self.state.highlight_is_selection and mtype == 'table.highlight.row':

            if not self.table_id_exists(params['table-id']):
                return

            data = self.data_from_table_id(params['table-id'])

            subset_state = ElementSubsetState(indices=[params['row']], data=data)

            mode = EditSubsetMode()
            mode.update(self.data_collection, subset_state)

        elif mtype == 'table.select.rowList':

            if not self.table_id_exists(params['table-id']):
                return

            data = self.data_from_table_id(params['table-id'])

            rows = np.asarray(params['row-list'], dtype=int)

            subset_state = ElementSubsetState(indices=rows, data=data)

            mode = EditSubsetMode()
            mode.update(self.data_collection, subset_state)

        elif mtype == 'samp.hub.event.register' or mtype == 'samp.hub.event.unregister':

            self.update_clients()

    def table_id_exists(self, table_id):
        for data in self.data_collection:
            if data.meta.get('samp-table-id', None) == table_id:
                return True
        else:
            return False

    def data_from_table_id(self, table_id):
        for data in self.data_collection:
            if data.meta.get('samp-table-id', None) == table_id:
                return data
        else:
            raise Exception("Table {0} not found".format(table_id))

    def image_id_exists(self, image_id):
        for data in self.data_collection:
            if data.meta.get('samp-image-id', None) == image_id:
                return True
        else:
            return False

    def data_from_image_id(self, image_id):
        for data in self.data_collection:
            if data.meta.get('samp-image-id', None) == image_id:
                return data
        else:
            raise Exception("image {0} not found".format(image_id))
