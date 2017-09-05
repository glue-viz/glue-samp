# Here we describe what we want the behavior to be under different scenarios.
# First we consider the case of another application sending a SAMP message to
# Glue
#
# table.load.votable, table.load.fits, and image.load.fits: load data if not
# already loaded (based on table-id or image-id)
#
# table.select.rowList: update subset or create new subset based on currently
#                       selected subset in glue (as if external application was
#                       just another viewer)
#
# table.highlight.row: should have an option that if enabled will treat this as
#                      a selection (but by default not?)
#
# Next we define what messages we can emit from glue:
#
# table.load.votable, table.load.fits, and image.load.fits: we should be able to
# send this by control-clicking on datasets in the data collection. Doing this
# could assign a table-id or image-id in the Data.meta.
#
# Table.select.rowList: we should be able to send this by control-clicking on
# subset groups or subsets in the data collection. Only subsets for datasets
# that have a table-id or image-id should be sent.
#
# A full list of 'standard' mtypes can be found here:
#
# http://wiki.ivoa.net/twiki/bin/view/IVOA/SampMTypes#table_load


def setup():
    from . import menubar  # noqa
