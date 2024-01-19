import json
import pathlib
import shutil
import unittest

import test_helpers

import tools.label_tool_post_process


class LabelToolTest(unittest.TestCase, test_helpers.BaseTest):
    def prepare_data_folder(self):
        dir_path = pathlib.Path(__file__).parent / "data" / "dir_with_labelled_images"
        if dir_path.is_dir():
            shutil.rmtree(dir_path)
            dir_path.mkdir()
        else:
            dir_path.mkdir()

        def create_img_json_pair(name, json_data):
            fp_failed_img = dir_path / (name + ".png")
            fp_failed_img.touch()
            fp_failed_json = fp_failed_img.with_suffix(".json")
            with open(str(fp_failed_json), "w") as f:
                json.dump(json_data, f, indent=2)

        # manual check failed
        create_img_json_pair(
            "manual_check_failed",
            {
                "manual_check_passed": False,
            },
        )

        # manual check undefined
        create_img_json_pair("manual_check_undefined", {})

        # manual check passed, prediction correct
        create_img_json_pair(
            "manual_check_passed_pred_correct",
            {
                "manual_check_passed": True,
                "object_class": "brick2x",
                "predicted_class": "brick2x",
            },
        )

        # manual check passed, prediction incorrect
        create_img_json_pair(
            "manual_check_passed_pred_incorrect",
            {
                "manual_check_passed": True,
                "object_class": "brick2x",
                "predicted_class": "tile",
            },
        )

        # manual check passed, prediction missing
        create_img_json_pair(
            "manual_check_passed_pred_missing",
            {
                "manual_check_passed": True,
            },
        )

        return dir_path

    def test_general(self):
        self.setup_logging()

        # prepare test folder
        dir_path = self.prepare_data_folder()

        tools.label_tool_post_process.post_process(dir_path)

        test_helpers.BaseTest.assert_threads_stopped(self)
