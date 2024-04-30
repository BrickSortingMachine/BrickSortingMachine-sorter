import time

import serial

import sorter.serial_service.serial_connection_handler
import sorter.serial_service.serial_connection_manager


def get_manager_mock():
    class MySerial:
        def __init__(self, path) -> None:
            self.path = path
            self.next_response = None
            self.read_count = 0

        def write(self, byte_str):
            if byte_str == b"HLO\n":
                if self.path.endswith("USB0"):
                    self.next_response = b"HLO slide-controller"
                elif self.path.endswith("USB1"):
                    self.next_response = b"HLO connection-ubs0"

        def readline(self):
            if self.next_response is not None:
                # request sent previously
                resp = self.next_response
                self.next_response = None
                return resp
            else:
                # simulate cyclic input from serial
                if self.read_count < 5:
                    time.sleep(1)
                    self.read_count += 1
                    return b"POS 5.273"
                else:
                    # simulate device disconnected
                    raise serial.SerialException()

    class MySerialConnectionHandler(
        sorter.serial_service.serial_connection_handler.SerialConnectionHandlerBase
    ):
        def __init__(self) -> None:
            super().__init__()

        def event_connected(self, connection):
            pass

        def event_disconnected(self, connection):
            pass

        def event_data_received(self, connection, data: bytes):
            pass

    def get_device_list(_):
        return ["/dev/ttyUSB0"]

    def connect_serial(_, path):
        return MySerial(path)

    # replace get_device_list method
    SerialConnectionManager = (
        sorter.serial_service.serial_connection_manager.SerialConnectionManager
    )
    SerialConnectionManagerAdapted = type(
        SerialConnectionManager.__name__,
        SerialConnectionManager.__bases__,
        dict(SerialConnectionManager.__dict__),
    )
    SerialConnectionManagerAdapted.get_device_list = get_device_list
    SerialConnectionManagerAdapted.connect_serial = connect_serial

    return SerialConnectionManagerAdapted, MySerialConnectionHandler
