import logging


class SerialConnectionHandlerBase:
    """
    Abstract base class for handling serial connections
    """

    def __init__(self) -> None:
        self.connection = None

    def base_event_connected(self, connection):
        logging.info("SerConHandler: Event connected")

        if self.connection is not None:
            raise Exception("Already have connection")
        self.connection = connection

        self.event_connected(connection)

    def base_event_disconnected(self, connection):
        logging.info("SerConHandler: Event disconnected")

        if self.connection is None:
            raise Exception("Already disconnected")
        self.connection = None

        self.event_disconnected(connection)

    def base_event_data_received(self, connection, data: bytes):
        assert isinstance(data, bytes)
        assert self.connection is not None
        logging.info(f'SerConHandler: Event data received "{data}"')
        self.event_data_received(connection, data)

    def event_connected(self, connection):
        raise NotImplementedError

    def event_disconnected(self, connection):
        raise NotImplementedError

    def event_data_received(self, connection, data: bytes):
        raise NotImplementedError

    def get_connection(self):
        return self.connection

    def is_connected(self):
        return self.connection is not None
