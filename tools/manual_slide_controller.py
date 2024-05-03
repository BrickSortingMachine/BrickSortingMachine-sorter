import logging
import os
import sys
import time

import readchar

# add robolab folder to python path
p = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(p)

import sorter.argument_parser
import sorter.serial_connection.manager
import sorter.serial_service.slide_serial_connection_handler

logging.basicConfig(
    format="%(levelname)s %(asctime)s %(filename)s:%(lineno)d %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.DEBUG,
)

parser = sorter.argument_parser.ArgumentParser(description="Manual Commands")
args = parser.parse_args()

manager = sorter.serial_connection.manager.SerialConnectionManager()
slide = (
    sorter.serial_service.slide_serial_connection_handler.SlideSerialConnectionHandler()
)
manager.register_handler("slide-controller", slide)

motion_completed = True
current_position = 90
current_elevation = 90


def callback_motion_completed():
    global motion_completed
    logging.info("Motion completed")
    motion_completed = True


slide.set_callback_motion_completed(callback_motion_completed)


def move(cmd: str):
    global current_position
    global current_elevation
    global motion_completed
    if cmd.startswith("normal"):
        inc = 10
    elif cmd.startswith("fast"):
        inc = 40
    elif cmd.startswith("slow"):
        inc = 1

    if cmd.endswith("right"):
        current_position += inc
    elif cmd.endswith("left"):
        current_position -= inc
    elif cmd.endswith("up"):
        if cmd.startswith("slow"):
            inc = 200
        current_elevation -= inc
    elif cmd.endswith("down"):
        if cmd.startswith("slow"):
            inc = 200
        current_elevation += inc
    elif cmd == "home":
        current_position = 90
        current_elevation = 90

    current_position = min(180, max(0, current_position))
    current_elevation = min(170, max(90, current_elevation))

    motion_completed = False
    slide.move_slide(current_position, current_elevation)
    while not motion_completed:
        time.sleep(0.5)
    logging.info("done")


# wait for serial connection
logging.info("Connecting ...")
while not slide.is_connected():
    time.sleep(0.5)
logging.info("Connected.")

# prompt
while True:
    # help
    print(" ")
    print(f"Current slide position: {current_position}deg {current_elevation}deg")
    print(" ")
    print("Control Slide")
    print(" ")
    print("   [h]   home              [q]  Quit")
    print(" ")
    print("   [e]   right slow        [d]  left slow")
    print("   [r]   right             [f]  left")
    print("   [t]   right fast        [g]  left fast")
    print(" ")
    print("   [o]   up slow        [l]  down slow")
    print("   [u]   up             [j]  down")
    print("   [i]   up fast        [k]  down fast")
    print(" ")

    # readkey
    try:
        k = readchar.readkey()
    except KeyboardInterrupt:
        k = "q"

    if k == "r":
        move("normal-right")
    elif k == "f":
        move("normal-left")

    elif k == "t":
        move("fast-right")
    elif k == "g":
        move("fast-left")

    elif k == "e":
        move("slow-right")
    elif k == "d":
        move("slow-left")

    elif k == "u":
        move("normal-up")
    elif k == "j":
        move("normal-down")

    elif k == "i":
        move("fast-up")
    elif k == "k":
        move("fast-down")

    elif k == "o":
        move("slow-up")
    elif k == "l":
        move("slow-down")

    elif k == "h":
        move("home")
    elif k == "q":
        logging.info("Stopping ...")
        move("home")
        break

logging.info("Stopped.")
