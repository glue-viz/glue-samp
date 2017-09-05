from functools import partial

from qtpy import QtWidgets

from glue.app.qt.layer_tree_widget import LayerAction

__all__ = ['add_samp_layer_actions']


class SAMPAction(LayerAction):

    _title = 'SAMP'

    def __init__(self, client, *args, **kwargs):
        super(SAMPAction, self).__init__(*args, **kwargs)
        self.client = client
        menu = SAMPMenu(self)
        self.setMenu(menu)
        self.update_enabled()

    def _can_trigger(self):
        if self.single_selection_data():
            layer = self.selected_layers()[0]
            return layer.ndim == 1 or layer.ndim == 2
        elif self.single_selection_subset():
            layer = self.selected_layers()[0]
            return layer.ndim == 1
        else:
            return False

    def _do_action(self):
        pass

    def _send_to_samp(self, client=None):
        self.client.send_data(layer=self.selected_layers()[0], client=client)


class SAMPMenu(QtWidgets.QMenu):

    def __init__(self, action, *args, **kwargs):
        super(SAMPMenu, self).__init__(*args, **kwargs)
        self.action = action
        self.update_clients([])

    def update_clients(self, clients):
        self.clear()
        if clients:
            self.addAction('Broadcast to all clients', self.action._send_to_samp)
            for client, name in clients:
                self.addAction('Send to {0}'.format(name),
                               partial(self.action._send_to_samp, client=client))
        else:
            action = self.addAction('No connected clients')
            action.setEnabled(False)


def add_samp_layer_actions(session, client):
    layer_tree_widget = session.application._layer_widget
    action = SAMPAction(client, layer_tree_widget)
    menu = action.menu()
    layer_tree_widget.ui.layerTree.addAction(action)
    client.state.add_callback('clients', menu.update_clients)
