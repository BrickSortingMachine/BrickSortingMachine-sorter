import logging
import os
import sys
import time

import sorter.util.argument_parser
import sorter.util.config_handler

logging.basicConfig(
    format="%(levelname)s %(asctime)s %(filename)s:%(lineno)d %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)


def run_controller(args, sub_parser):
    enable_device = not args.disable_machine
    enable_belt = not args.disable_belt
    enable_vf = not args.disable_vf
    if args.disable_machine:
        logging.info("Machine disabled ...")
    if args.disable_belt:
        logging.info("Belt disabled ...")
    if args.disable_vf:
        logging.info("vf1/vf2/storage disabled ...")

    import sorter.controller.machine_controller

    mc = sorter.controller.machine_controller.MachineController(
        enable_device, enable_belt, disable_server=False, enable_vf=enable_vf
    )
    mc.start_control_thread()

    logging.info("Stop controller using Ctrl + C ...")
    try:
        while True:
            time.sleep(100)
    except KeyboardInterrupt:
        logging.info("Stopping ...")
        mc.stop_control_thread()


def run_notification(args, sub_parser):
    import sorter.notification_service.notification_service

    c = sorter.notification_service.notification_service.NotificationService(
        args.host, disable_network=args.disable_network, theme=args.theme
    )

    logging.info("Stop controller using Ctrl + C ...")
    try:
        while True:
            time.sleep(100)
    except KeyboardInterrupt:
        logging.info("Stopping ...")
        c.stop()
    except Exception as e:
        c.stop()
        raise e


def run_serial(args, sub_parser):
    import sorter.serial_service.serial_service as ss

    _ = ss.SerialService(args.host, disable_network=args.disable_network)

    logging.info("Stop serial service using Ctrl + C ...")

    try:
        while True:
            time.sleep(100)
    except KeyboardInterrupt:
        logging.info("Stopping ...")


def run_classification(args, sub_parser):
    import sorter.classification_service.classification_service

    c = sorter.classification_service.classification_service.ClassificationService(
        args.host, model_fp=args.model, enable_cnn=not args.disable_cnn
    )

    time.sleep(0.5)
    logging.info("Stop classification service using Ctrl + C ...")
    try:
        while True:
            time.sleep(100)
    except KeyboardInterrupt:
        logging.info("Stopping ...")
        c.stop()


def run_vision(args, sub_parser):
    recording = None
    if args.disable_camera:
        rec = (
            args.recording if args.recording is not None else "rec_2022-04-21_12-42-30"
        )

        # yellow technic brick
        recording = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "data", rec)
        )

    import sorter.vision_service.vision_service

    c = sorter.vision_service.vision_service.VisionService(
        recording,
        args.collect_class,
        args.disable_write,
        args.host,
        disable_network=False,
        enable_visualization_fullscreen=not args.disable_fullscreen,
    )
    try:
        c.collect()
        c.stop()
    except KeyboardInterrupt:
        logging.info("Stopping ...")
        c.stop()


if __name__ == "__main__":
    # parse command line arguments
    parser = sorter.util.argument_parser.ArgumentParser(description="Sorter")

    # command specific parsers
    subparsers = parser.add_subparsers(help="Command to be run")

    # controller
    controller_parser = subparsers.add_parser("controller")
    controller_parser.set_defaults(command="controller")
    controller_parser.add_argument(
        "--disable_machine", action="store_true", required=False
    )
    controller_parser.add_argument(
        "--disable_belt", action="store_true", required=False
    )
    controller_parser.add_argument("--disable_vf", action="store_true", required=False)

    # vision
    vision_parser = subparsers.add_parser("vision")
    vision_parser.set_defaults(command="vision")
    vision_parser.add_argument(
        "--host", required=True, help="Hostname of machine server"
    )
    vision_parser.add_argument(
        "--collect_class", required=True, help="Assign data to this class"
    )
    vision_parser.add_argument(
        "--disable_camera",
        action="store_true",
        required=False,
        help="No camera, sample data",
    )
    vision_parser.add_argument(
        "--disable_write",
        action="store_true",
        required=False,
        help="Not writing images to disk",
    )
    vision_parser.add_argument(
        "--recording",
        required=False,
        help="Recording, to be used with --disable_camera",
    )
    vision_parser.add_argument(
        "--disable_fullscreen",
        action="store_true",
        help="Display visualization in window instead of in fuillscreen mode",
    )

    # classification
    classification_parser = subparsers.add_parser("classification")
    classification_parser.set_defaults(command="classification")
    classification_parser.add_argument(
        "--host", required=True, help="Hostname of machine server"
    )
    classification_parser.add_argument(
        "--model", required=True, help="CNN model to load"
    )
    classification_parser.add_argument(
        "--disable_cnn",
        required=False,
        help="Disable CNN (dummy results)",
        action="store_true",
    )

    # notification
    notification_parser = subparsers.add_parser("notification")
    notification_parser.set_defaults(command="notification")
    notification_parser.add_argument(
        "--host", required=True, help="Hostname of machine server"
    )
    notification_parser.add_argument(
        "--disable_network",
        required=False,
        action="store_true",
        help="No network connection",
    )
    notification_parser.add_argument("--theme", required=True, help="Sound theme")

    # serial
    serial_parser = subparsers.add_parser("serial")
    serial_parser.set_defaults(command="serial")
    serial_parser.add_argument(
        "--host", required=True, help="Hostname of machine server"
    )
    serial_parser.add_argument(
        "--disable_network",
        required=False,
        action="store_true",
        help="No network connection",
    )

    args = parser.parse_args()

    _ = sorter.util.config_handler.ConfigHandler()

    if "command" not in args:
        parser.error("Please supply " "command" " argument.")
        sys.exit(1)

    if args.command.lower() == "controller":
        run_controller(args, controller_parser)

    elif args.command.lower() == "vision":
        run_vision(args, vision_parser)

    elif args.command.lower() == "classification":
        run_classification(args, classification_parser)

    elif args.command.lower() == "notification":
        run_notification(args, notification_parser)

    elif args.command.lower() == "serial":
        run_serial(args, serial_parser)

    # standard help
    else:
        parser.print_help()
        sys.exit(1)
