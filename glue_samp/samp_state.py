from __future__ import print_function, division, absolute_import

from glue.external.echo import CallbackProperty
from glue.core.state_objects import State


class SAMPState(State):

    status = CallbackProperty('Not connected to SAMP Hub')
    connected = CallbackProperty(False)
    clients = CallbackProperty([])
    highlight_is_selection = CallbackProperty(False)
