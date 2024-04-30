import logging
import os
import sys
import time

logging.basicConfig(
    format="%(levelname)s %(asctime)s %(filename)s:%(lineno)d %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.DEBUG,
)

# add robolab folder to python path
p = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(p)

import sorter.network.tcp_client
import sorter.util.argument_parser

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

# check connected
time.sleep(0.5)
if not c.get_connected():
    logging.error("Unable to connect to host")
    sys.exit(1)

print("Example Prompts:")
print("  STP false        Disable Soft E-Stop")
print("  ")
print("  BST not-busy 0   Belt non-busy")
print("  BST busy 0   Belt busy")
print("  ")
print("  Empty prompt for quit")
print("  ")

# prompt
while True:
    s = input(">>> ")
    if s == "":
        break
    c.send_msg(bytes(s, "utf-8"))

c.stop()
