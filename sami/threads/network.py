import time
import queue

from ._base import BaseThread
from ..network.requests import Request
from ..contacts import Contact, OwnContact
from ..nodes.own import is_private_key_loaded
from ..utils.network import get_network_interfaces
from ..network import Network, Networks, RequestsHandler

import logging as _logging
logger = _logging.getLogger('threads')


class NetworkThread(BaseThread):
    """
    Thread handling network interactions.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.networks: Networks = Networks()
        # Populate the networks
        for nic in get_network_interfaces():
            self.networks.register_network(
                Network(
                    parent=self.networks,
                    own_contact=OwnContact.from_interface(nic),
                )
            )


class RequestHandlingThread(NetworkThread):

    def run(self):
        # Wait until the private key is loaded in
        while not is_private_key_loaded() \
                and not self.global_app_stop_event.is_set() \
                and not self._stop_event.is_set():
            time.sleep(2)

        if self.global_app_stop_event.is_set() or self._stop_event.is_set():
            return

        logger.info('Beginning requests handling')
        # Main loop, we'll handle the raw requests in the queue
        handler: RequestsHandler = RequestsHandler()
        while not self.global_app_stop_event.is_set() \
                and not self._stop_event.is_set():
            try:
                raw_req, from_address = self.networks.handle_queue.get(block=False)
            except queue.Empty:
                time.sleep(2)
            else:
                handler(raw_req, from_address)


class SenderThread(NetworkThread):

    def run(self):
        # Main loop, we'll send the requests in the queue
        while not self.global_app_stop_event.is_set() \
                and not self._stop_event.is_set():
            try:
                network, request, contact = self.networks.send_queue.get(block=False)
                network: Network
                request: Request
                contact: Contact
            except queue.Empty:
                time.sleep(2)
            else:
                network._send_request(request, contact)
