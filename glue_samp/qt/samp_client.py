from __future__ import print_function, division, absolute_import

import os

from qtpy import QtWidgets
from qtpy.QtCore import Signal

from glue.utils import nonpartial
from glue.utils.qt import load_ui
from glue.external.echo.qt import autoconnect_callbacks_to_qt

from glue_samp.samp_client import SAMPClient


class QtSAMPClient(SAMPClient, QtWidgets.QWidget):

    call_received = Signal(object, object, object, object, object, object)
    notification_received = Signal(object, object, object, object, object, object)

    def __init__(self, state=None, data_collection=None, parent=None):

        SAMPClient.__init__(self, state=state, data_collection=data_collection)
        QtWidgets.QWidget.__init__(self, parent=parent)

        self.ui = load_ui('samp_client.ui', self,
                          directory=os.path.dirname(__file__))

        self.state = state

        autoconnect_callbacks_to_qt(self.state, self.ui)

        self.ui.button_start_samp.clicked.connect(nonpartial(self.start_samp))
        self.ui.button_stop_samp.clicked.connect(nonpartial(self.stop_samp))

        self.state.add_callback('connected', self.on_connected_change)
        self.state.add_callback('status', self.on_status_change)

        self.on_connected_change()
        self.on_status_change()

    def on_connected_change(self, *args):

        self.ui.button_start_samp.setEnabled(not self.state.connected)
        self.ui.button_stop_samp.setEnabled(self.state.connected)

        if self.state.connected:

            self.register()

            self.call_received.connect(self.receive_message)
            self.notification_received.connect(self.receive_message)

        else:

            self.unregister()

            try:
                self.call_received.disconnect(self.receive_message)
                self.notification_received.disconnect(self.receive_message)
            except TypeError:
                pass

    def on_status_change(self, *args):
        color = 'green' if self.state.connected else 'red'
        self.ui.text_status.setStyleSheet('color: {0}'.format(color))

    def receive_call(self, private_key, sender_id, msg_id, mtype, params, extra):
        self.call_received.emit(private_key, sender_id, msg_id, mtype, params, extra)
        self.client.reply(msg_id, {"samp.status": "samp.ok", "samp.result": {}})

    def receive_notification(self, private_key, sender_id, msg_id, mtype, params, extra):
        self.notification_received.emit(private_key, sender_id, msg_id, mtype, params, extra)
