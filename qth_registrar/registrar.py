from collections import defaultdict

import asyncio
import logging

import qth

from qth_registrar.tree import client_registrations_to_directory_tree


class QthRegistrar(object):
    """A registration server for Qth."""

    def __init__(self, load_time=3.0, loop=None, host="localhost", port=1883,
                 keepalive=10):
        """Constructor

        Params
        ------
        load_time : float
            The time to allow the MQTT server to send all retained messages in
            response to a subscription.
        """
        self._load_time = load_time
        self._loop = loop or asyncio.get_event_loop()
        self._client = qth.Client("qth_registrar",
                                  "Implements the Qth Registration service.",
                                  loop=loop, host=host, port=port,
                                  keepalive=keepalive)

        # When the server first starts up we allow some time to receive the
        # complete set of retained messages indicating client states and the
        # existing directory tree before making any changes. This helps prevent
        # the tree thrashing on startup.
        self._enable_listings_updates = False

        # The authoratative dictionary mapping from topic to a list of
        # endpoint objects registered to that topic. (Not including
        # directories.)
        self._topics = defaultdict(list)

        # Mapping from client_id to the latest report from that client
        self._client_registrations = {}

        # For every directory, the most recently published listing.
        self._cur_tree = {}

        # A lock which is held while the tree is reconciled.
        self._reconciliation_lock = asyncio.Lock()

        logging.info("Qth registrar starting...")
        self._loop.create_task(self._startup())

    async def close(self):
        logging.info("Qth registrar shutting down...")
        self._enable_listings_updates = False
        await self._client.close()
        logging.info("Qth registrar shut down.")

    async def _startup(self):
        # Register just the root 'ls' endpoint as a hint for browsers. We can't
        # provide a full directory listing as this would produce an infinitely
        # recurring tree!
        await self._client.register(
            "meta/ls/",
            qth.PROPERTY_ONE_TO_MANY,
            "The root of the Qth directory listing. The properties which form "
            "the lower levels of this hierarchy do not appear in the listing.")

        await self._client.ensure_connected()

        # Fetch the current published tree and client registrations
        logging.info("Waiting for all client registrations to arrive.")
        await asyncio.wait([
            self._client.subscribe("meta/clients/+", self._on_client_changed),
            self._read_back_tree(),
        ], loop=self._loop)

        # Reconcile any differences
        logging.info("Publishing initial tree.")
        self._enable_listings_updates = True
        await self._reconcile()
        logging.info("Server started!")

    async def _read_back_tree(self):
        """Internal use only. Read the directory tree back from the MQTT server
        and store it in self._cur_tree. For use on startup to allow the server
        to cleanly take over from a previous registration server.
        """
        self._cur_tree = {}

        def on_dir_listing_received(topic, payload):
            self._cur_tree[topic] = payload
        await self._client.subscribe("meta/ls/#", on_dir_listing_received)

        # Give the tree time to be received
        await asyncio.sleep(self._load_time, loop=self._loop)

        await self._client.unsubscribe("meta/ls/#", on_dir_listing_received)

    async def _on_client_changed(self, topic, payload):
        """Internal. Callback when a client changes its registration
        details.
        """
        # Update the client record
        client_id = topic.split("/")[-1]
        if payload is not qth.Empty:
            # Child connected or changed
            if client_id not in self._client_registrations:
                logging.info("Client '%s' connected.", client_id)
            else:
                logging.info("Client '%s' changed.", client_id)
            self._client_registrations[client_id] = payload
        else:
            # Child disconnected, perform requested cleanup actions
            logging.info("Client '%s' disconnected.", client_id)
            child_registration = self._client_registrations.pop(client_id, {})
            for topic, registration in child_registration["topics"].items():
                if registration.get("delete_on_unregister", False):
                    print(topic, "deleted")
                    self._loop.create_task(self._client.delete_property(topic))
                elif "on_unregister" in registration:
                    if registration["behaviour"] in (qth.EVENT_ONE_TO_MANY,
                                                     qth.EVENT_MANY_TO_ONE):
                        print(topic, "send")
                        self._loop.create_task(self._client.send_event(
                            topic, registration["on_unregister"]))
                    elif registration["behaviour"] in (
                            qth.PROPERTY_ONE_TO_MANY,
                            qth.PROPERTY_MANY_TO_ONE):
                        print(topic, "set")
                        self._loop.create_task(self._client.set_property(
                            topic, registration["on_unregister"]))

        # Propagate the changes to the listing tree
        if self._enable_listings_updates:
            self._loop.create_task(self._reconcile())

    async def _reconcile(self):
        """Internal. Make the listed tree consistent with the current set of
        client registrations.
        """
        with await self._reconciliation_lock:
            logging.info("Reconciling tree...")
            # Compute the complete desired directory tree
            new_tree = client_registrations_to_directory_tree(
                self._client_registrations)

            # Find the set of topics which need re-publishing
            to_change = set()
            for topic in set(new_tree) | set(self._cur_tree):
                if new_tree.get(topic) != self._cur_tree.get(topic):
                    to_change.add(topic)

            # Generate publications.
            message_coros = []
            for topic in to_change:
                new_value = new_tree.get(topic, qth.Empty)
                retain = new_value is not None
                message_coros.append(self._client.publish(topic, new_value,
                                     retain=retain))

            # Wait for publications to take effect
            if message_coros:
                logging.info("Updating tree for paths: %s",
                             ", ".join(map(repr, to_change)))
                try:
                    done, pending = await asyncio.wait(
                        message_coros, loop=self._loop)
                    assert len(pending) == 0
                    self._cur_tree = new_tree
                except Exception as e:
                    # If publication fails we'll be left in an unknown state;
                    # republish everything from scratch.
                    logging.error("Tree update failed, "
                                  "will recreate tree from scratch...")
                    self._cur_tree = {}
                    if self._enable_listings_updates:
                        self._loop.create_task(self._reconcile())
                    logging.exception(e)
            else:
                logging.info("No changes to tree required!")
