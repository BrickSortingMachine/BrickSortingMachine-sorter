import json
import pathlib

import sorter.util.singleton


class ConfigHandler(metaclass=sorter.util.singleton.Singleton):
    def __init__(self):
        self.json_file_path = pathlib.Path(__file__).parents[2] / "config.json"

        # help msg
        if not self.json_file_path.is_file():
            raise Exception(
                "File 'config.json' file does not exist. Please adapt template 'config.json.examle' and rename to 'config.json'"
            )

        # read json
        with open(self.json_file_path) as json_file:
            self.data = json.load(json_file)

    def get_param(self, key):
        return self.data[key]
