import logging
import os
import sys
import time

import readchar

# add robolab folder to python path
p = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(p)

import sorter.classification_service.classification_service
import sorter.network.tcp_client
import sorter.notification_service.notification_client
import sorter.util.argument_parser

logging.basicConfig(
    format="%(levelname)s %(asctime)s %(filename)s:%(lineno)d %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.DEBUG,
)

parser = sorter.util.argument_parser.ArgumentParser(description="Manual Commands")
parser.add_argument("--host", required=True, help="Hostname of machine server")
args = parser.parse_args()

c = sorter.network.tcp_client.TcpClient(
    args.host,
    5005,
    name="ClassificationService",
    type="ClassificationService",
    retry_connection=False,
    auto_reconnect=False,
)
c.start()
nc = sorter.notification_service.notification_client.NotificationClient(c)

# connected ?
time.sleep(0.5)
if not c.get_connected():
    logging.error("Unable to connect to host")
    sys.exit(1)


def send_classification_result(object_class: str):
    logging.info(f"Sending class: {object_class}")
    low_list = [
        {"class": object_class, "probability": 1},
        {"class": "other1", "probability": 0},
        {"class": "other2", "probability": 0},
    ]
    high_list = low_list

    msg = sorter.classification_service.classification_service.ClassificationService.compose_classification_result_message(
        object_id=0,
        predicted_class=object_class,
        probability=1,
        uniqueness=1000,
        average_process_time_sec=0.1,
        low_list=low_list,
        high_list=high_list,
    )
    logging.info(f"Sending msg {msg} ...")
    c.send_msg(msg)
    logging.info("sent.")

    nc.notify_classification_result(object_class)


# prompt
while True:
    # help
    print("Send Classification Result Messages")
    print(" ")
    print("   [0]   skip              [7]  tile")
    print("   [1]   brick1x           [8]  car")
    print("   [2]   brick2x           [9]  small")
    print("   [3]   brick_modified    [s]  slope1x")
    print("   [4]   plate1x           [r]  round")
    print("   [5]   plate2x")
    print("   [6]   plate_modified")
    print(" ")
    print("   [e]   Exit")
    print(" ")

    # readkey
    k = readchar.readkey()
    if k == "0":
        send_classification_result("skip")
    if k == "1":
        send_classification_result("brick1x")
    if k == "2":
        send_classification_result("brick2x")
    if k == "3":
        send_classification_result("brick_modified")
    if k == "4":
        send_classification_result("plate1x")
    if k == "5":
        send_classification_result("plate2x")
    if k == "6":
        send_classification_result("plate_modified")
    if k == "7":
        send_classification_result("tile")
    if k == "8":
        send_classification_result("car")
    if k == "9":
        send_classification_result("small")
    if k == "s":
        send_classification_result("slope1x")
    if k == "r":
        send_classification_result("round")
    if k == readchar.key.DOWN:
        # do stuff
        print("down")
    if k == "e":
        logging.info("Disconnecting ...")
        break

c.stop()
