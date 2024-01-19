import logging
import os
import sys
import time

import keyboard

# add robolab folder to python path
p = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(p)

import sorter.network.tcp_client
import sorter.util.argument_parser
import sorter.util.scan_codes

logging.basicConfig(
    format="%(levelname)s %(asctime)s %(filename)s:%(lineno)d %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)


parser = sorter.util.argument_parser.ArgumentParser(description="Manual Commands")
parser.add_argument("--host", required=True, help="Hostname of machine server")
args = parser.parse_args()

c = sorter.network.tcp_client.TcpClient(
    args.host,
    5005,
    name="VisionService",
    type="VisionService",
    retry_connection=False,
    auto_reconnect=False,
)
c.start()

# connected ?
time.sleep(0.5)
if not c.get_connected():
    logging.error("Unable to connect to host")
    sys.exit(1)
else:
    logging.info("Connection succesful.")

state_stopped = False
state_belt_busy = False


def draw_status():
    print("Usage")
    print("=====\n")
    print("  ESC     Exit")

    print(f"  Stopped    {state_stopped!s:5}    S / X")
    print(f"  Belt-Busy  {state_belt_busy!s:5}    D / C")
    print(" ")


draw_status()

try:
    while True:
        if keyboard.is_pressed(sorter.util.scan_codes.key_esc):
            break
        elif keyboard.is_pressed(sorter.util.scan_codes.key_s):
            c.send_msg(b"STP true")
            logging.info("STP true")
            state_stopped = True
            draw_status()
        elif keyboard.is_pressed(sorter.util.scan_codes.key_x):
            c.send_msg(b"STP false")
            logging.info("STP false")
            state_stopped = False
            draw_status()
        elif keyboard.is_pressed(sorter.util.scan_codes.key_d):
            c.send_msg(b"BST busy 123")
            logging.info("BST busy 123")
            state_belt_busy = True
            draw_status()
        elif keyboard.is_pressed(sorter.util.scan_codes.key_c):
            c.send_msg(b"BST non-busy 123")
            logging.info("STP non-busy 123")
            state_belt_busy = False
            draw_status()

        time.sleep(0.1)

except KeyboardInterrupt:
    logging.info("Stopping client ...")
    c.stop()
except Exception as e:
    c.stop()
    raise e

c.stop()
