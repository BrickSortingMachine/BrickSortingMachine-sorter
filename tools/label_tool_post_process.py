import json
import logging
import shutil


def post_process(dir_path):
    """
    - Create sub folders
        __extended
            if 'manual_check_passed' in data and data['manual_check_passed']:
                if data['object_class'] == data['predicted_class']:
        __checked
            manual check passed, prediction incorrect / missing
        __rejected
            manual check failed
        parent folder, leave everything else
    """
    assert dir_path.is_dir()

    # create dirs
    checked_fp = dir_path / (dir_path.name + "__checked")
    checked_fp.mkdir()
    extended_fp = dir_path / (dir_path.name + "__extended")
    extended_fp.mkdir()
    rejected_fp = dir_path / (dir_path.name + "__rejected")
    rejected_fp.mkdir()

    # sort files
    extended_file_list = []
    checked_file_list = []
    rejected_file_list = []
    for json_fp in dir_path.iterdir():
        if (
            json_fp.is_file()
            and json_fp.suffix == ".json"
            and json_fp.name != "label_tool.json"
        ):
            img_fp = json_fp.with_suffix(".png")
            if not img_fp.is_file():
                raise Exception(f"No .png for json file {json_fp}")

            with open(json_fp) as json_file:
                json_data = json.load(json_file)

            file_tuple = (img_fp, json_fp)

            if "manual_check_passed" in json_data:
                if not json_data["manual_check_passed"]:
                    # manual check failed
                    rejected_file_list.append(file_tuple)

                else:
                    # manual check passed

                    if (
                        "predicted_class" not in json_data
                        or json_data["predicted_class"] != json_data["object_class"]
                    ):
                        # prediction incorrect / missing
                        checked_file_list.append(file_tuple)

                    else:
                        # prediction correct
                        extended_file_list.append(file_tuple)

    # output
    logging.info("Rejected Images:")
    for t in rejected_file_list:
        logging.info(f"  {t[0].name}")
    logging.info("Extended Images:")
    for t in extended_file_list:
        logging.info(f"  {t[0].name}")
    logging.info("Checked Images:")
    for t in checked_file_list:
        logging.info(f"  {t[0].name}")

    # move files
    def mv(fp, target_dir_path):
        src_fp = fp
        dst_fp = target_dir_path / fp.name
        logging.info(f"{src_fp} -> {dst_fp}")
        shutil.move(src_fp, dst_fp)

    for t in rejected_file_list:
        mv(t[0], rejected_fp)
        mv(t[1], rejected_fp)
    for t in extended_file_list:
        mv(t[0], extended_fp)
        mv(t[1], extended_fp)
    for t in checked_file_list:
        mv(t[0], checked_fp)
        mv(t[1], checked_fp)
