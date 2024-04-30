import datetime
import enum

import sorter.controller.hour_meter
import sorter.controller.state_timer


class BeltState(enum.Enum):
    NON_BUSY = 0
    BUSY = 1


class ItemState(enum.Enum):
    RUNNING = 0
    PAUSED = 1


class StateOutput:
    def __init__(
        self,
        vf1_active: bool,
        vf2_active: bool,
        storage_active: bool,
        belt_active: bool,
    ):
        self.vf1_active = vf1_active
        self.vf2_active = vf2_active
        self.storage_active = storage_active
        self.belt_active = belt_active


class MachineState:
    """
    No stopped state - if belt busy this gives the indication and not item state
    """

    def __init__(self) -> None:
        # vibration feeder 1 (fast)
        self.vf1_active_sec = 0.2
        self.vf1_pause_sec = 0.5

        # vibration feeder 2 (slow)
        self.vf2_active_sec = 0.2
        self.vf2_pause_sec = (
            self.vf1_pause_sec + self.vf1_active_sec + self.vf1_pause_sec
        )

        # storage belt
        self.storage_active_sec = 0.4
        self.storage_pause_sec = 12

        # start in non-busy state as vs does
        self.belt_state = BeltState.NON_BUSY

        # timers for either start / stop time frame depending on state
        self.vf1_timer = sorter.controller.state_timer.StateTimer()
        self.vf2_timer = sorter.controller.state_timer.StateTimer()
        self.storage_timer = sorter.controller.state_timer.StateTimer()

        # states
        self.vf1_state = ItemState.RUNNING
        self.vf2_state = ItemState.RUNNING
        self.storage_state = ItemState.RUNNING
        self.vision_client_connected = False
        self.machine_stopped = True

        # state in last loop
        self.last_output = None

        # hour meter
        self.hm = sorter.controller.hour_meter.HourMeter()

    def input_event_belt_busy(self, dt_now):
        """
        Called by machine controller on receiving belt busy from vision
        """
        self.belt_state = BeltState.BUSY
        self.pause_timers(dt_now)

    def input_event_belt_nonBusy(self, dt_now):
        self.belt_state = BeltState.NON_BUSY
        self.resume_timers(dt_now)

    def input_event_vision_service_connected(self, dt_now):
        """
        Called by machine controller when vision connected
        """
        self.vision_client_connected = True
        # do not resume timers since still soft estopped

    def input_event_vision_service_disconnected(self, dt_now):
        self.vision_client_connected = False
        self.input_event_soft_estop(True, dt_now)

    def input_event_soft_estop(self, stopped, dt_now):
        self.machine_stopped = stopped
        if stopped:
            self.pause_timers(dt_now)
        else:
            self.resume_timers(dt_now)

    def pause_timers(self, dt_now):
        # not change states, since belt busy says everything
        # pause timers, do not count this time in
        self.vf1_timer.pause(dt_now)
        self.vf2_timer.pause(dt_now)
        self.storage_timer.pause(dt_now)

    def resume_timers(self, dt_now):
        # not change states, since belt busy says everything
        # pause timers, do not count this time in
        self.vf1_timer.resume(dt_now)
        self.vf2_timer.resume(dt_now)
        self.storage_timer.resume(dt_now)

    def cycle(self, dt_now):
        output = None
        # no vision || stopped
        if not self.vision_client_connected or self.machine_stopped:
            output = StateOutput(
                vf1_active=False,
                vf2_active=False,
                storage_active=False,
                belt_active=False,
            )

        # busy
        elif self.belt_state == BeltState.BUSY:
            output = StateOutput(
                vf1_active=False,
                vf2_active=False,
                storage_active=False,
                belt_active=True,
            )

        # non-busy
        elif self.belt_state == BeltState.NON_BUSY:
            self.vf1_state = self.cycle_item_non_busy(
                dt_now,
                self.vf1_state,
                self.vf1_timer,
                self.vf1_active_sec,
                self.vf1_pause_sec,
            )
            self.vf2_state = self.cycle_item_non_busy(
                dt_now,
                self.vf2_state,
                self.vf2_timer,
                self.vf2_active_sec,
                self.vf2_pause_sec,
            )
            self.storage_state = self.cycle_item_non_busy(
                dt_now,
                self.storage_state,
                self.storage_timer,
                self.storage_active_sec,
                self.storage_pause_sec,
            )
            output = StateOutput(
                vf1_active=self.vf1_state == ItemState.RUNNING,
                vf2_active=self.vf2_state == ItemState.RUNNING,
                storage_active=self.storage_state == ItemState.RUNNING,
                belt_active=True,
            )

        # change events
        if (
            self.last_output is not None
            and output.belt_active != self.last_output.belt_active
        ):
            self.output_event_belt_active_changed(output)

        self.last_output = output

        return output

    def cycle_item_non_busy(
        self,
        dt_now: datetime.datetime,
        item_state: ItemState,
        item_timer: sorter.controller.state_timer.StateTimer,
        item_active_sec: float,
        item_pause_sec: float,
    ) -> ItemState:
        new_item_state = item_state

        if item_state == ItemState.RUNNING:
            if item_timer.get_seconds(dt_now) > item_active_sec:
                new_item_state = ItemState.PAUSED
                item_timer.reset()
                item_timer.resume(dt_now)

        elif item_state == ItemState.PAUSED:
            if item_timer.get_seconds(dt_now) > item_pause_sec:
                new_item_state = ItemState.RUNNING
                item_timer.reset()
                item_timer.resume(dt_now)

        else:
            assert False

        return new_item_state

    def output_event_belt_active_changed(self, output):
        """
        Called when belt changes running state (e.g. out of e-stop)
        """
        if output.belt_active:
            self.hm.start()
        else:
            self.hm.stop()

    def get_hour_meter_value(self):
        return self.hm.get_value()
