import datetime
import unittest

import test_helpers

import sorter.controller.hour_meter
import sorter.controller.machine_state


class MachineStateTest(unittest.TestCase, test_helpers.BaseTest):
    def test_vf1_pulse(self):
        self.setup_logging()
        sorter.controller.hour_meter.HourMeter().reset()

        sc = sorter.controller.machine_state.MachineState()

        dt_now = datetime.datetime(year=2021, month=1, day=1)
        s = datetime.timedelta(seconds=1)
        d = datetime.timedelta(seconds=0.1)

        # init in stop state
        output = sc.cycle(dt_now)
        self.assertFalse(output.vf1_active)

        # 0s, vision service connected
        sc.input_event_vision_service_connected(dt_now)
        output = sc.cycle(dt_now)
        self.assertFalse(output.vf1_active)

        # e-stop off
        sc.input_event_soft_estop(False, dt_now)
        output = sc.cycle(dt_now)
        self.assertTrue(output.vf1_active)

        # vf1_active_sec, vf1 pauses
        dt_now += sc.vf1_active_sec * s + d
        output = sc.cycle(dt_now)
        self.assertFalse(output.vf1_active)

        # vf1_pause_sec, vf1 resumes
        dt_now += sc.vf1_pause_sec * s + d
        output = sc.cycle(dt_now)
        self.assertTrue(output.vf1_active)

        test_helpers.BaseTest.assert_threads_stopped(self)

    def test_belt_becomes_busy_in_between(self):
        """
        Busy -> VF stops, belt continues
        """
        self.setup_logging()
        sorter.controller.hour_meter.HourMeter().reset()

        sc = sorter.controller.machine_state.MachineState()

        dt_now = datetime.datetime(year=2021, month=1, day=1)
        s = datetime.timedelta(seconds=1)
        d = datetime.timedelta(seconds=0.1)

        # init in stop state
        output = sc.cycle(dt_now)
        self.assertFalse(output.vf1_active)
        self.assertFalse(output.vf2_active)
        self.assertFalse(output.storage_active)
        self.assertFalse(output.belt_active)

        # 0s, vision service connected
        sc.input_event_vision_service_connected(dt_now)
        output = sc.cycle(dt_now)
        self.assertFalse(output.vf1_active)
        self.assertFalse(output.vf2_active)
        self.assertFalse(output.storage_active)
        self.assertFalse(output.belt_active)

        # e-stop off
        sc.input_event_soft_estop(False, dt_now)
        output = sc.cycle(dt_now)
        self.assertTrue(output.vf1_active)
        self.assertTrue(output.vf2_active)
        self.assertTrue(output.storage_active)
        self.assertTrue(output.belt_active)

        # half way belt becomes active
        dt_now += 0.5 * sc.vf1_active_sec * s
        sc.input_event_belt_busy(dt_now)
        output = sc.cycle(dt_now)
        self.assertFalse(output.vf1_active)
        self.assertFalse(output.vf2_active)
        self.assertFalse(output.storage_active)
        self.assertTrue(output.belt_active)  # belt stays active!

        # normally VF would have become paused agian
        # but not because belt busy time does not count
        dt_now += 0.5 * sc.vf1_active_sec * s + d
        sc.input_event_belt_nonBusy(dt_now)
        output = sc.cycle(dt_now)
        self.assertTrue(output.vf1_active)

        # wait another time for it to become paused again
        # catch edge active True -> False
        dt_now += 0.5 * sc.vf1_active_sec * s - d
        output = sc.cycle(dt_now)
        self.assertTrue(output.vf1_active)
        dt_now += 2 * d
        output = sc.cycle(dt_now)
        self.assertFalse(output.vf1_active)

        test_helpers.BaseTest.assert_threads_stopped(self)

    def test_stop(self):
        self.setup_logging()
        sorter.controller.hour_meter.HourMeter().reset()

        sc = sorter.controller.machine_state.MachineState()

        dt_now = datetime.datetime(year=2021, month=1, day=1)
        s = datetime.timedelta(seconds=1)

        # init in stop state
        output = sc.cycle(dt_now)
        self.assertFalse(output.vf1_active)
        self.assertFalse(output.vf2_active)
        self.assertFalse(output.storage_active)
        self.assertFalse(output.belt_active)

        # 0s, vision service connected
        sc.input_event_vision_service_connected(dt_now)
        output = sc.cycle(dt_now)
        self.assertFalse(output.vf1_active)
        self.assertFalse(output.vf2_active)
        self.assertFalse(output.storage_active)
        self.assertFalse(output.belt_active)

        # e-stop off
        sc.input_event_soft_estop(False, dt_now)
        output = sc.cycle(dt_now)
        self.assertTrue(output.vf1_active)
        self.assertTrue(output.vf2_active)
        self.assertTrue(output.storage_active)
        self.assertTrue(output.belt_active)

        # half way, vs stop
        dt_now += 0.5 * sc.vf1_active_sec * s
        sc.input_event_soft_estop(stopped=True, dt_now=dt_now)
        output = sc.cycle(dt_now)
        self.assertFalse(output.vf1_active)
        self.assertFalse(output.vf2_active)
        self.assertFalse(output.storage_active)
        self.assertFalse(output.belt_active)

        test_helpers.BaseTest.assert_threads_stopped(self)

    def test_vs_disconnect(self):
        self.setup_logging()
        sorter.controller.hour_meter.HourMeter().reset()

        sc = sorter.controller.machine_state.MachineState()

        dt_now = datetime.datetime(year=2021, month=1, day=1)
        s = datetime.timedelta(seconds=1)

        # init in stop state
        output = sc.cycle(dt_now)
        self.assertFalse(output.vf1_active)
        self.assertFalse(output.vf2_active)
        self.assertFalse(output.storage_active)
        self.assertFalse(output.belt_active)

        # 0s, vision service connected
        sc.input_event_vision_service_connected(dt_now)
        output = sc.cycle(dt_now)
        self.assertFalse(output.vf1_active)
        self.assertFalse(output.vf2_active)
        self.assertFalse(output.storage_active)
        self.assertFalse(output.belt_active)

        # e-stop off
        sc.input_event_soft_estop(False, dt_now)
        output = sc.cycle(dt_now)
        self.assertTrue(output.vf1_active)
        self.assertTrue(output.vf2_active)
        self.assertTrue(output.storage_active)
        self.assertTrue(output.belt_active)

        # half way, vs disconnected
        dt_now += 0.5 * sc.vf1_active_sec * s
        sc.input_event_vision_service_disconnected(dt_now)
        output = sc.cycle(dt_now)
        self.assertFalse(output.vf1_active)
        self.assertFalse(output.vf2_active)
        self.assertFalse(output.storage_active)
        self.assertFalse(output.belt_active)

        test_helpers.BaseTest.assert_threads_stopped(self)
