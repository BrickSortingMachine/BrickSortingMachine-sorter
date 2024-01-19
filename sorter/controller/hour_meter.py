import datetime
import enum
import json
import os
import pathlib

import sorter.util.singleton


# Enum for state of hour meter
class HourMeterState(enum.Enum):
    STOPPED = 0
    RUNNING = 1


class HourMeter(metaclass=sorter.util.singleton.Singleton):
    def __init__(self) -> None:
        # NOTICE: Singleton not re-called between different tests -> use reset
        self.reset()

    def reset(self):
        self.dt_start = None
        self.state = HourMeterState.STOPPED
        self.data_fp = pathlib.Path(__file__).parents[2] / "data"

        # last value stored in json
        d = self.read_json()
        self.last_stored_value = d["s"]

    def start(self):
        if self.state != HourMeterState.STOPPED:
            raise Exception("HourMeter started called while not in STOPPED state")

        self.state = HourMeterState.RUNNING
        self.dt_start = datetime.datetime.now()

    def stop(self):
        if self.state != HourMeterState.RUNNING:
            raise Exception("HourMeter stopped called while not in RUNNING state")

        runtime_sec = (datetime.datetime.now() - self.dt_start).total_seconds()

        data = self.read_json()

        data["s"] += runtime_sec

        self.write_json(data)

        self.state = HourMeterState.STOPPED
        self.dt_start = None
        self.last_stored_value = data["s"]

    def read_json(self):
        # default data
        data = {
            "s": 0,
        }

        # read file if exists
        json_fp = self.data_fp / "hour_meter.json"
        if json_fp.is_file():
            with open(str(json_fp)) as json_file:
                data = json.load(json_file)

        return data

    def write_json(self, data):
        """
        - Write json to tmp file
        - Move old file to backup file
        - Move tmp file to main file
        """

        json_fp = self.data_fp / "hour_meter.json"
        tmp_fp = self.data_fp / "hour_meter.tmp"
        backup_fp = self.data_fp / (
            "hour_meter_backup_"
            + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
            + ".json"
        )

        # write tmp file
        with open(str(tmp_fp), "w+") as f:
            json.dump(data, f, indent=2)

        # move main -> bak
        if json_fp.is_file():
            os.rename(str(json_fp), str(backup_fp))

        # move tmp -> main
        os.rename(str(tmp_fp), str(json_fp))

        self.delete_old_tmp_files()

    def delete_old_tmp_files(self):
        """
        Delete, except most recent 3
        """
        backup_file_list = list(self.data_fp.glob("hour_meter_backup_*"))

        # sort by date
        backup_file_list.sort()

        # delete all except last 3
        files_to_delte = backup_file_list[0:-5]

        # delete the old ones
        for f in files_to_delte:
            os.remove(str(f))

    def get_value(self):
        if self.state == HourMeterState.STOPPED:
            return self.last_stored_value
        else:
            runtime_sec = (datetime.datetime.now() - self.dt_start).total_seconds()
            return self.last_stored_value + runtime_sec
