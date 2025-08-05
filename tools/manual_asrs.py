import logging
import os
import sys
import time

import readchar

# add robolab folder to python path
p = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(p)

import sorter.asrs_service.asrs_service
import sorter.util.argument_parser

logging.basicConfig(
    format="%(levelname)s %(asctime)s %(filename)s:%(lineno)d %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.DEBUG,
)

parser = sorter.util.argument_parser.ArgumentParser(description="Manual Commands")
args = parser.parse_args()

asrs = sorter.asrs_service.asrs_service.ASRSService(host="", disable_network=True)


# prompt
while True:
    # help
    print(" ")
    print(" ")
    print("Control Slide")
    print(" ")
    print("   [h]   home              [q]  Quit")

    # readkey
    try:
        k = readchar.readkey()
    except KeyboardInterrupt:
        k = "q"

    if k == "h":
        asrs.homing()
    
    elif k == "f":
        pass

    elif k == "q":
        logging.info("Stopping ...")
        asrs.stop()
        break

logging.info("Stopped.")
