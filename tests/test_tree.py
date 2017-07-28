from qth_registrar.tree import Tree, client_registrations_to_directory_tree

class TestTree(object):
    
    def test_direct_child(self):
        t = Tree()
        assert t.children == {}
        
        t.add_topic("foo", {"bar": "baz"})
        assert t.children == {
            "foo": [{"bar": "baz"}],
        }

        t.add_topic("foo", {"qux": "quo"})
        assert t.children == {
            "foo": [{"bar": "baz"}, {"qux": "quo"}],
        }
        
        t.add_topic("jam", {"qb": "than"})
        assert t.children == {
            "foo": [{"bar": "baz"}, {"qux": "quo"}],
            "jam": [{"qb": "than"}],
        }
    
    def test_nested_child(self):
        t = Tree()
        assert t.children == {}
        
        t.add_topic("foo/bar", {"baz": "qux"})
        assert set(t.children.keys()) == {"foo"}
        assert isinstance(t.children["foo"], list)
        assert len(t.children["foo"]) == 1
        assert isinstance(t.children["foo"][0], Tree)
        assert t.children["foo"][0].children == {
            "bar": [{"baz": "qux"}],
        }
        
        # Add something else to the same directory
        t.add_topic("foo/jam", {"qb": "than"})
        assert set(t.children.keys()) == {"foo"}
        assert isinstance(t.children["foo"], list)
        assert len(t.children["foo"]) == 1
        assert isinstance(t.children["foo"][0], Tree)
        assert t.children["foo"][0].children == {
            "bar": [{"baz": "qux"}],
            "jam": [{"qb": "than"}],
        }
    
    def test_get_listing(self):
        t = Tree()
        
        # Empty
        assert t.get_listing() == {}
        
        # Just local children
        t.add_topic("foo", {"bar": "baz"})
        t.add_topic("foo", {"qux": "quo"})
        t.add_topic("jam", {"qb": "than"})
        assert t.get_listing() == {
            "foo": [{"bar": "baz"}, {"qux": "quo"}],
            "jam": [{"qb": "than"}],
        }
        
        # A directory is expanded correctly
        t.add_topic("jam/lub", {"very": "lots"})
        assert t.get_listing() == {
            "foo": [{"bar": "baz"}, {"qux": "quo"}],
            "jam": [{"qb": "than"}, {"behaviour": "DIRECTORY",
                                     "description": "A subdirectory.",
                                     "client_id": None}],
        }
    
    def test_iter_listings(self):
        t = Tree()
        
        # Empty
        assert list(t.iter_listings()) == [("meta/ls/", {})]
        
        # Just local children
        t.add_topic("foo", {"bar": "baz"})
        t.add_topic("foo", {"qux": "quo"})
        t.add_topic("jam", {"qb": "than"})
        assert sorted(t.iter_listings()) == [("meta/ls/", {
            "foo": [{"bar": "baz"}, {"qux": "quo"}],
            "jam": [{"qb": "than"}],
        })]
        
        # Directories are iterated into correctly
        t.add_topic("do/la/re", {"me": "so"})
        t.add_topic("jam/lub", {"very": "lots"})
        assert sorted(t.iter_listings()) == [
            ("meta/ls/", {
                "do": [{"behaviour": "DIRECTORY",
                        "description": "A subdirectory.",
                        "client_id": None}],
                "foo": [{"bar": "baz"}, {"qux": "quo"}],
                "jam": [{"qb": "than"}, {"behaviour": "DIRECTORY",
                                         "description": "A subdirectory.",
                                         "client_id": None}],
             }),
            ("meta/ls/do/", {"la": [{"behaviour": "DIRECTORY",
                                     "description": "A subdirectory.",
                                     "client_id": None}]}),
            ("meta/ls/do/la/", {"re": [{"me": "so"}]}),
            ("meta/ls/jam/", {"lub": [{"very": "lots"}]}),
        ]


def test_client_registrations_to_directory_tree():
    client_registrations = {
        "c1": {
            "description": "Client number one.",
            "topics": {
                "example/foo": {"behaviour": "EVENT-1:N",
                                "description": "Example foo event."},
                "example/bar": {"behaviour": "EVENT-N:1",
                                "description": "Example bar event."},
            }
        },
        "c2": {
            "description": "Client number two.",
            "topics": {
                "example/baz": {"behaviour": "PROPERTY-1:N",
                                "description": "Example baz property."},
                "qux": {"behaviour": "PROPERTY-N:1",
                        "description": "Example qux property."},
            }
        },
    }
    
    assert client_registrations_to_directory_tree(client_registrations) == {
        "meta/ls/": {
            "qux": [{"behaviour": "PROPERTY-N:1",
                     "description": "Example qux property.",
                     "client_id": "c2"}],
            "example": [{"behaviour": "DIRECTORY",
                        "description": "A subdirectory.",
                        "client_id": None}],
            "meta": [{"behaviour": "DIRECTORY",
                      "description": "A subdirectory.",
                      "client_id": None}],
        },
        "meta/ls/example/": {
            "foo": [{"behaviour": "EVENT-1:N",
                     "description": "Example foo event.",
                     "client_id": "c1"}],
            "bar": [{"behaviour": "EVENT-N:1",
                     "description": "Example bar event.",
                     "client_id": "c1"}],
            "baz": [{"behaviour": "PROPERTY-1:N",
                     "description": "Example baz property.",
                     "client_id": "c2"}],
        },
        "meta/ls/meta/": {
            "clients": [{"behaviour": "DIRECTORY",
                        "description": "A subdirectory.",
                        "client_id": None}],
        },
        "meta/ls/meta/clients/": {
            "c1": [{"behaviour": "PROPERTY-1:N",
                    "description": "Client Qth registration details.",
                    "client_id": "c1"}],
            "c2": [{"behaviour": "PROPERTY-1:N",
                    "description": "Client Qth registration details.",
                    "client_id": "c2"}],
        },
    }
