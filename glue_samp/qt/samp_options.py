from __future__ import print_function, division, absolute_import

import os

from qtpy import QtWidgets
from qtpy.QtCore import Signal

from glue.utils.qt import load_ui
from glue.external.echo.qt import autoconnect_callbacks_to_qt

from astropy.samp import SAMPClientError


class SAMPOptions(QtWidgets.QWidget):

    call_received = Signal(object, object, object, object, object, object)
    notification_received = Signal(object, object, object, object, object, object)

    def __init__(self, state=None, receiver=None, parent=None):

        super(SAMPOptions, self).__init__(parent=parent)

        self.ui = load_ui('samp_options.ui', self,
                          directory=os.path.dirname(__file__))

        self.state = state
        self.receiver = receiver

        autoconnect_callbacks_to_qt(self.state, self.ui)

        self.state.add_callback('connected', self.on_connected_change)
        self.state.add_callback('status', self.on_status_change)

        self.on_connected_change()
        self.on_status_change()

    def on_connected_change(self, *args):

        self.ui.button_start_samp.setEnabled(not self.state.connected)
        self.ui.button_stop_samp.setEnabled(self.state.connected)

        if self.state.connected:

            self.state.client.bind_receive_call("*", self._receive_call)
            self.state.client.bind_receive_notification("*", self._receive_notification)

            self.call_received.connect(self.receiver.receive_message)
            self.notification_received.connect(self.receiver.receive_message)

        else:

            try:
                self.state.client.unbind_receive_call("*")
                self.state.client.unbind_receive_notification("*")
            except (AttributeError, SAMPClientError):
                pass

            try:
                self.call_received.disconnect(self.receiver.receive_message)
                self.notification_received.disconnect(self.receiver.receive_message)
            except TypeError:
                pass

    def on_status_change(self, *args):
        color = 'green' if self.state.connected else 'red'
        self.ui.text_status.setStyleSheet('color: {0}'.format(color))

    def _receive_call(self, private_key, sender_id, msg_id, mtype, params, extra):
        self.call_received.emit(private_key, sender_id, msg_id, mtype, params, extra)
        self.state.client.reply(msg_id, {"samp.status": "samp.ok", "samp.result": {}})

    def _receive_notification(self, private_key, sender_id, msg_id, mtype, params, extra):
        self.notification_received.emit(private_key, sender_id, msg_id, mtype, params, extra)
