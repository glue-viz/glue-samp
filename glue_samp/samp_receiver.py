from __future__ import print_function, division, absolute_import

from glue.logger import logger

from glue.core.data_factories.astropy_table import (astropy_tabular_data_votable,
                                                    astropy_tabular_data_fits)
from glue.core.data_factories.fits import fits_reader

from glue.core.edit_subset_mode import EditSubsetMode
from glue.core.subset import ElementSubsetState

__all__ = ['SAMPReceiver']


class SAMPReceiver(object):

    def __init__(self, data_collection):
        self.data_collection = data_collection

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

            data.label = params['name']
            data.meta['samp-table-id'] = params['table-id']

            self.data_collection.append(data)

        elif mtype == 'image.load':

            if self.image_id_exists(params['image-id']):
                logger.info('SAMP: image with image-id={0} has already '
                            'been read in'.format(params['image-id']))
                return

            logger.info('SAMP: loading image with image-id={0}'.format(params['image-id']))

            if mtype == 'image.load.fits':
                data = fits_reader(params['url'])
            else:
                logger.info('SAMP: unknown format {0}'.format(mtype.split('.')[-1]))
                return

            data.label = params['name']
            data.meta['samp-image-id'] = params['image-id']

            self.data_collection.append(data)

        elif mtype == 'table.highlight.row':

            data = self.data_from_table_id(params['table-id'])
            len(self.data_collection.subset_groups)

            subset_state = ElementSubsetState(indices=[params['row']], data=data)

            mode = EditSubsetMode()
            mode.update(self.data_collection, subset_state)

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

    def image_id_exists(self, image_id):
        for data in self.data_collection:
            if data.meta['samp-image-id'] == image_id:
                return True
        else:
            return False

    def data_from_image_id(self, image_id):
        for data in self.data_collection:
            if data.meta['samp-image-id'] == image_id:
                return data
        else:
            raise Exception("image {0} not found".format(image_id))
