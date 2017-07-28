"""
Internal data-structures/algorithms to construct the directory tree structure
published by the registrar.
"""

import logging

from collections import defaultdict

import qth


class Tree(object):
    """A recursive tree structure in a directory tree."""
    
    def __init__(self):
        self.children = defaultdict(list)
    
    def add_topic(self, topic, description):
        """Add a new path to the tree.
        
        Params
        ------
        topic : str
            The topic to add ("/" separated as usual). If a topic is added
            several times, the descriptions will be accumulated.
        description : dict
            The dictionary describing that topic.
        """
        if "/" in topic:
            dirname, _, sub_topic = topic.partition("/")
            
            tree = None
            for child in self.children[dirname]:
                if isinstance(child, Tree):
                    tree = child
                    break
            if tree is None:
                tree = Tree()
                self.children[dirname].append(tree)
            
            tree.add_topic(sub_topic, description)
        else:
            self.children[topic].append(description)
    
    def get_listing(self):
        """Get a JSON-serialisable Qth-registry formatted listing of the
        contents of this level of the directory tree, including entries
        describing available subdirectories.
        """
        return {
            topic: [description if not isinstance(description, Tree) else
                    {"behaviour": qth.DIRECTORY,
                     "description": "A subdirectory.",
                     "client_id": None}
                    for description in descriptions]
            for topic, descriptions in self.children.items()
        }
    
    def iter_listings(self, topic="meta/ls/"):
        """An iterator over the Qth-style directory listings for the entire
        directory structure.
        
        Params
        ------
        topic : str
            The path prefix of the directory listing topics (defaults to
            'meta/ls' so you're unlikely to need to change this).
        """
        # This directory
        yield (topic, self.get_listing())
        
        # Child directories
        for child_subtopic, children in self.children.items():
            child_topic = "{}{}/".format(topic, child_subtopic)
            for child in children:
                if isinstance(child, Tree):
                    yield from child.iter_listings(child_topic)


def client_registrations_to_directory_tree(client_registrations):
    """Given a dictionary mapping client IDs to registration dicts, returns a
    dict mapping from directory listing path to directory listing entry.
    """
    tree = Tree()
    
    for client_id, client_registration in client_registrations.items():
        try:
            # Add topics registered by the client
            for topic, description in client_registration["topics"].items():
                description = description.copy()
                description["client_id"] = client_id
                tree.add_topic(topic, description)
            
            # Add the client registration property itself
            tree.add_topic("meta/clients/{}".format(client_id),
                           {"behaviour": qth.PROPERTY_ONE_TO_MANY,
                            "description": "Client Qth registration details.",
                            "client_id": client_id})
        except e:
            logging.error("Malformed registration for client '%s': %s",
                          client_id, registration)
            logging.exception(e)
    
    return dict(tree.iter_listings())
