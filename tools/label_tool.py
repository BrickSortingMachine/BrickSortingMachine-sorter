import json
import logging
import os
import pathlib
import sys

import cv2

logging.basicConfig(
    format="%(levelname)s %(asctime)s %(filename)s:%(lineno)d %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.DEBUG,
)

# add robolab folder to python path
p = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(p)

import sorter.label_tool.classification_service_client
import sorter.util.argument_parser
import sorter.vision_service.draw_bg_box
import tools.label_tool_post_process


def read_state():
    state_fp = folder_path / "label_tool.json"
    if state_fp.is_file():
        with open(state_fp) as json_file:
            state = json.load(json_file)
    else:
        state = {"current_file_index": 0}
    return state


def write_state(state):
    state_fp = folder_path / "label_tool.json"
    with open(str(state_fp), "w") as f:
        json.dump(state, f, indent=2)


def draw_cutout(img):
    """
    draw rectangle classifier cutout
    """
    for low in [True, False]:
        if low:
            x = 330
            y = 250
            w = 400
            h = 400
        else:
            x = 380
            y = 10
            w = 300
            h = 300

        cv2.rectangle(img, (x, y), (x + w, y + h), (255, 255, 255), 1)


if __name__ == "__main__":
    # parse command line arguments
    parser = sorter.util.argument_parser.ArgumentParser(
        description="Video capture tool"
    )
    parser.add_argument("folder")
    args = parser.parse_args()

    folder_path = pathlib.Path(args.folder)

    folder_path = folder_path.resolve()

    state = read_state()

    logging.info(f"Path: {folder_path}")
    if not folder_path.exists() or not folder_path.is_dir():
        logging.error(f"Path {folder_path} does not exist or is not a directory")
        sys.exit(1)

    file_list = []
    for f in folder_path.iterdir():
        if f.is_file() and f.suffix == ".png":
            file_list.append(f)

    # clamp file index
    state["current_file_index"] = min(state["current_file_index"], len(file_list) - 1)

    while True:
        f = file_list[state["current_file_index"]]
        print(f)
        json_path = f.with_suffix(".json")
        with open(json_path) as json_file:
            json_data = json.load(json_file)

        current_class = json_data["object_class"]
        manual_check_passed = "Unknown"
        if "manual_check_passed" in json_data:
            if json_data["manual_check_passed"]:
                manual_check_passed = "True"
            else:
                manual_check_passed = "False"
        predicted_class = "Unknown"
        if "predicted_class" in json_data:
            predicted_class = json_data["predicted_class"]

        quit = False
        esc = False
        while True:
            img = cv2.imread(str(f))
            msg_list = []
            msg_list.append(f'File {state["current_file_index"]} of {len(file_list)}')
            msg_list.append("Quit: q")
            msg_list.append("Reset: Esc")
            msg_list.append("Write: Enter")
            msg_list.append("MCFailed & Write: t")
            msg_list.append("")
            msg_list.append("Accept pred: [Space]")
            msg_list.append("None: e")

            msg_list.append("plate1x: p")
            msg_list.append("plate2x: o")
            msg_list.append("plate_modified: i")
            msg_list.append("plate_shaped: u")

            msg_list.append("brick1x:        b")
            msg_list.append("brick2x:        n")
            msg_list.append("brick_modified: m")

            msg_list.append("round_slope:    a")
            msg_list.append("slope1x:        s")
            msg_list.append("slope:          d")
            msg_list.append("car:            c")
            msg_list.append("small:          v")
            msg_list.append("tile:           j")
            msg_list.append("human:          h")
            msg_list.append("round:          r")
            msg_list.append("window:         w")
            msg_list.append("hinge:          x")
            msg_list.append("plane:          f")
            msg_list.append("bar:            g")
            msg_list.append("multiple parts: l")
            msg_list.append("")
            msg_list.append(f"Predicted Class: {predicted_class}")
            msg_list.append(f"Current Class: {current_class}")
            msg_list.append(f"Manual Check Passed: {manual_check_passed}")
            y = 20
            sorter.vision_service.draw_bg_box.draw_bg_box(
                img, 10, 10, 300, img.shape[0] - 20, alpha=0.8
            )
            for msg in msg_list:
                cv2.putText(
                    img,
                    msg,
                    (10, y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    1,
                    2,
                )
                y += 20

            draw_cutout(img)

            cv2.imshow("Label Tool", img)
            ch = cv2.waitKey(-1)

            if ord("b") == ch:
                current_class = "brick1x"
                manual_check_passed = "True"
            elif ord("n") == ch:
                current_class = "brick2x"
                manual_check_passed = "True"
            elif ord("m") == ch:
                current_class = "brick_modified"
                manual_check_passed = "True"
            elif 48 == ch:  # 0 key
                current_class = "plate"
                manual_check_passed = "True"
            elif ord("p") == ch:
                current_class = "plate1x"
                manual_check_passed = "True"
            elif ord("o") == ch:
                current_class = "plate2x"
                manual_check_passed = "True"
            elif ord("i") == ch:
                current_class = "plate_modified"
                manual_check_passed = "True"
            elif ord("u") == ch:
                current_class = "plate_shaped"
                manual_check_passed = "True"
            elif ord("a") == ch:
                current_class = "round_slope"
                manual_check_passed = "True"
            elif ord("s") == ch:
                current_class = "slope1x"
                manual_check_passed = "True"
            elif ord("d") == ch:
                current_class = "slope"
                manual_check_passed = "True"
            elif ord("c") == ch:
                current_class = "car"
                manual_check_passed = "True"
            elif ord("v") == ch:
                current_class = "small"
                manual_check_passed = "True"
            elif ord("j") == ch:
                current_class = "tile"
                manual_check_passed = "True"
            elif ord("h") == ch:
                current_class = "human"
                manual_check_passed = "True"
            elif ord("w") == ch:
                current_class = "window"
                manual_check_passed = "True"
            elif ord("e") == ch:
                current_class = "None"
                manual_check_passed = "False"
            elif ord("r") == ch:
                current_class = "round"
                manual_check_passed = "True"
            elif ord("x") == ch:
                current_class = "hinge"
                manual_check_passed = "True"
            elif ord("f") == ch:
                current_class = "plane"
                manual_check_passed = "True"
            elif ord("g") == ch:
                current_class = "bar"
                manual_check_passed = "True"
            elif ord("l") == ch:
                current_class = "multiple_parts"
                manual_check_passed = "True"
            elif 51 == ch:  # 3 key
                del_input = input("Shall file postprocessing really be started y/[n]? ")
                if del_input == "y":
                    tools.label_tool_post_process.post_process(folder_path)
                quit = True
                break
            if ord("q") == ch:
                quit = True
                break
            if ord("t") == ch:
                manual_check_passed = "False"
            if 32 == ch:  # space
                if current_class == "None":
                    if not json_data["predicted_class"].startswith(
                        "inc_"
                    ) and not json_data["predicted_class"].startswith("skip"):
                        current_class = json_data["predicted_class"]
                        manual_check_passed = "True"
                    else:
                        logging.info('Predicted class is "inc_"/"skip" - cannot accept')
                        ch = 0
                else:
                    logging.info("Current class is not None - will not overwrite")
                    ch = 0
            if 13 == ch or ord("t") == ch or 32 == ch:  # enter
                logging.info(f"Writing class {current_class} ...")
                json_data["object_class"] = current_class
                if manual_check_passed == "True":
                    json_data["manual_check_passed"] = True
                if manual_check_passed == "False":
                    json_data["manual_check_passed"] = False
                with open(str(json_path), "w") as f:
                    json.dump(json_data, f, indent=2)

                state["current_file_index"] += 1
                state["current_file_index"] = min(
                    state["current_file_index"], len(file_list) - 1
                )
                write_state(state)
                break
            elif 27 == ch:  # esc
                logging.info("Resetting class to json file state ...")
                current_class = json_data["object_class"]
            elif 37 == ch or 49 == ch:  # left, 1
                state["current_file_index"] -= 1
                state["current_file_index"] = max(state["current_file_index"], 0)
                write_state(state)
                break
            elif 39 == ch or 50 == ch:  # right, 2
                state["current_file_index"] += 1
                state["current_file_index"] = min(
                    state["current_file_index"], len(file_list) - 1
                )
                write_state(state)
                break
            elif ord(";") == ch:
                classification_service_client = (
                    sorter.label_tool.classification_service_client.ClassificationServiceClient()
                )
                current_class = classification_service_client.run(
                    file_list[state["current_file_index"]]
                )
                manual_check_passed = "True"
            else:
                print(ch)

        if quit:
            break
