import time
import unittest

import test_helpers

import sorter.controller.machine_controller
import sorter.network.tcp_client


class MachineControllerTest(unittest.TestCase, test_helpers.BaseTest):
    def test_tcp_busy_command(self):
        """
        Full loop, incl. network
        """
        self.setup_logging()

        mc = sorter.controller.machine_controller.MachineController(
            enable_device=False, enable_belt=True, disable_server=False, enable_vf=True
        )
        mc.start_control_thread()

        # very high timers to only react on busy event
        mc.state.vf1_active_sec = 100
        mc.state.vf2_active_sec = 100
        mc.state.storage_active_sec = 100

        c1 = sorter.network.tcp_client.TcpClient(
            "127.0.0.1",
            5005,
            name="VisionService",
            type="VisionService",
            retry_connection=False,
            auto_reconnect=False,
        )
        c1.start()
        time.sleep(0.5)

        # e-stop false
        c1.send_msg(b"STP false")
        time.sleep(0.5)

        for cycle_counter in range(0, 25):
            # running beginning
            if cycle_counter == 0:
                self.assertTrue(mc.last_state_output.vf1_active)
                self.assertTrue(mc.last_state_output.vf2_active)
                self.assertTrue(mc.last_state_output.storage_active)

            # stopping because busy
            elif cycle_counter == 2:
                c1.send_msg(b"BST busy 5")
            elif cycle_counter == 4:
                self.assertFalse(mc.last_state_output.vf1_active)
                self.assertFalse(mc.last_state_output.vf2_active)
                self.assertFalse(mc.last_state_output.storage_active)

            # running again
            elif cycle_counter == 6:
                c1.send_msg(b"BST not-busy 10")
            elif cycle_counter == 8:
                self.assertTrue(mc.last_state_output.vf1_active)
                self.assertTrue(mc.last_state_output.vf2_active)
                # not storage because running so shortly

            time.sleep(0.2)

        # stop network
        c1.stop()
        mc.stop_control_thread()

        test_helpers.BaseTest.assert_threads_stopped(self)

    def test_classification_request(self):
        """
        CLF, forward classification request to classification service
        """
        self.setup_logging()

        # server
        mc = sorter.controller.machine_controller.MachineController(
            enable_device=False, enable_belt=False, disable_server=False, enable_vf=True
        )
        mc.start_control_thread()
        time.sleep(0.5)

        # clients
        vision_service = sorter.network.tcp_client.TcpClient(
            "127.0.0.1",
            5005,
            name="VisionService",
            type="VisionService",
            retry_connection=False,
            auto_reconnect=False,
        )
        vision_service.start()
        time.sleep(0.5)
        classification_service = sorter.network.tcp_client.TcpClient(
            "127.0.0.1",
            5005,
            name="ClassificationService",
            type="ClassificationService",
            retry_connection=False,
            auto_reconnect=False,
        )
        classification_service.start()
        time.sleep(0.5)

        # send CLF to server
        vision_service.send_msg(b"CLF 5 test_image.png")
        time.sleep(0.5)

        # assert fwd via server received
        self.assertEqual(b"CLF 5 test_image.png", classification_service.get_last_msg())

        # stop network
        classification_service.stop()
        vision_service.stop()
        mc.stop_control_thread()

        test_helpers.BaseTest.assert_threads_stopped(self)

    def test_notification_request(self):
        """
        CLF, forward classification request to classification service
        """
        self.setup_logging()

        # server
        mc = sorter.controller.machine_controller.MachineController(
            enable_device=False, enable_belt=False, disable_server=False, enable_vf=True
        )
        mc.start_control_thread()
        time.sleep(0.5)

        # clients
        vision_service = sorter.network.tcp_client.TcpClient(
            "127.0.0.1",
            5005,
            name="VisionService",
            type="VisionService",
            retry_connection=False,
            auto_reconnect=False,
        )
        vision_service.start()
        time.sleep(0.5)
        notification_service = sorter.network.tcp_client.TcpClient(
            "127.0.0.1",
            5005,
            name="NotificationService",
            type="NotificationService",
            retry_connection=False,
            auto_reconnect=False,
        )
        notification_service.start()
        time.sleep(0.5)

        # send NTF to server
        vision_service.send_msg(b"NTF object_detected This is a message")
        time.sleep(0.5)

        # assert fwd via server received
        self.assertEqual(
            b"NTF object_detected This is a message",
            notification_service.get_last_msg(),
        )

        # stop network
        notification_service.stop()
        vision_service.stop()
        mc.stop_control_thread()

        test_helpers.BaseTest.assert_threads_stopped(self)
