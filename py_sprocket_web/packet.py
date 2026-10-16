import json


class Packet:
    """
    Container to hold arbitrary JSON-serializable data (strings, ints, lists, etc.) to send over network.
    No longer uses pickle because we don't like arbitrary code execution from internet strangers.
    Top-level structure is always a dictionary, stored in this class's __dict__ for easy access.
    """

    INTERNAL_DATA_PREFIX = "_pywebsprocket_"  # Top-level packet keys with this prefix are reserved for framework use
    CLIENT_ID_KEY = INTERNAL_DATA_PREFIX + "client_id"

    def __init__(self, **kwargs):
        self.__dict__ = kwargs

    def __str__(self):
        title = [f"Packet at {id(self)}:"]
        lines = [f"  {item}: {self.__dict__[item]}" for item in self.__dict__]
        return "\n".join(title + lines)

    def add_key(self, key, value):
        """ Adds a single key and value to the Packet's dictionary by string name. """
        self.add(**{key: value})

    def add(self, **kwargs):
        """ Add an arbitrary number of keyword arguments to the Packet's dictionary. """
        self.__dict__.update(kwargs)

    def has(self, index):
        """ Returns true if the specified index exists in the packet dictionary. """
        return index in self.__dict__

    def get(self, index, default=None):
        """ Return an item from the Packet's dictionary via index (probably a string). If it doesn't
            exist, instead return the default value.
        """
        if not self.has(index):
            return default
        return self.__dict__[index]

    def to_json(self):
        """ Convert the packet to bytes via JSON. """
        return json.dumps(self.__dict__)

    @staticmethod
    def ping():
        """ Test packet used just for sending heartbeats. """
        return Packet(ping=True)

    def is_ping(self):
        return self.get("ping")

    @staticmethod
    def pong():
        """ Test packet used just for responding to heartbeats. """
        return Packet(pong=True)

    def is_pong(self):
        return self.get("pong")

    @staticmethod
    def from_json(data):
        """ Construct and return a new packet from a JSON string. """
        return Packet(**json.loads(data))
