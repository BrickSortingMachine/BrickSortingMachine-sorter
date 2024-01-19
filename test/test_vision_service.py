# All ObjectDetector Tests are currently deactivated since there is no
# public version of the test data available yet.

# import json
# import logging
# import os
# import pathlib
# import time
# import unittest

# import test_helpers

# import sorter.network.tcp_server
# import sorter.util.catch_all_thread_exception
# import sorter.vision_service.vision_service


# class DummyCommandHandler(sorter.network.tcp_server.RequestHandler):
#     def __init__(self, request, client_address, server) -> None:
#         super().__init__(request, client_address, server)
#         self.belt_busy = None
#         self.belt_busy_frame_index = None

#     def process_custom_command(self, message):
#         command = message[:3]

#         # BST - Belt Status
#         if command == b"BST":
#             # b'BST busy 57'
#             logging.info('Received command BST - belt status: "%s"' % message)
#             part_list = str(message, "utf-8").split(" ")
#             self.belt_busy = part_list[1] == "busy"
#             self.belt_busy_frame_index = int(part_list[2])
#         else:
#             # ignore all other commands
#             pass


# class VisionServiceTest(unittest.TestCase, test_helpers.BaseTest):
#     test_data_folder = os.path.abspath(
#          os.path.join(os.path.dirname(__file__), "data"))

#     def test_general(self):
#         """
#         General
#         """
#         enable_visualization = False
#         self.setup_logging()

#         # yellow technic brick
#         recording = os.path.abspath(
#             os.path.join(
#                 os.path.dirname(__file__), "..", "data", "rec_2022-04-21_12-42-30"
#             )
#         )

#         # dummy server
#         s = sorter.network.tcp_server.TcpServer("0.0.0.0", 5005, DummyCommandHandler)
#         s.start()
#         time.sleep(1)

#         # run vision service client
#         tdc = sorter.vision_service.vision_service.VisionService(
#             recording=recording,
#             object_class="technic_brick",
#             no_write=False,
#             host="127.0.0.1",
#             disable_network=False,
#             enable_visualization_fullscreen=False,
#         )
#         tdc.enable_visualization = enable_visualization
#         tdc.camera_fisheye.set_pre_recorded_loop_count(0)
#         tdc.incoming_data_known_class_train_folder_path = self.test_data_folder
#         tdc.collect()

#         # server received belt busy
#         self.assertTrue(s.get_handler_by_name("VisionService").belt_busy)
#         self.assertEqual(
#             53, s.get_handler_by_name("VisionService").belt_busy_frame_index
#         )

#         # stop network
#         tdc.stop()
#         s.stop()
#         time.sleep(5)

#         test_helpers.BaseTest.assert_threads_stopped(self)

#     def test_network_auto_reconnect(self):
#         """
#         Data collection running, network breaks -> stop collecting data,
#         reconnect, resume
#         """
#         self.setup_logging()

#         # yellow technic brick
#         recording = os.path.abspath(
#             os.path.join(
#                 os.path.dirname(__file__), "..", "data", "rec_2022-04-21_12-42-30"
#             )
#         )

#         # dummy server
#         s = sorter.network.tcp_server.TcpServer("0.0.0.0", 5005, DummyCommandHandler)
#         s.start()
#         time.sleep(1)

#         # collect train data
#         tdc = sorter.vision_service.vision_service.VisionService(
#             recording=recording,
#             object_class="technic_brick",
#             no_write=True,
#             host="127.0.0.1",
#             disable_network=False,
#             enable_visualization_fullscreen=False,
#         )
#         tdc.notification_client.tcp_client = None  # disable notification client
#         tdc.enable_visualization = False
#         tdc.camera_fisheye.set_pre_recorded_loop_count(2)
#         time.sleep(1)

#         # connected
#         self.assertTrue(tdc.tcp_client.get_connected())

#         # stop server
#         s.stop()
#         time.sleep(0.5)
#         self.assertFalse(tdc.tcp_client.get_connected())

#         # restart server
#         s.start()
#         time.sleep(2)
#         self.assertTrue(tdc.tcp_client.get_connected())

#         # stop network
#         tdc.stop()
#         s.stop()
#         time.sleep(0.5)

#         test_helpers.BaseTest.assert_threads_stopped(self)

#     def test_time_since_last_busy(self):
#         """
#         General
#         """
#         enable_visualization = False
#         self.setup_logging()

#         # empty belt
#         recording = os.path.abspath(
#             os.path.join(
#                 os.path.dirname(__file__), "..", "data", "rec_2022-04-21_12-42-15"
#             )
#         )

#         # run vision service client
#         vs = sorter.vision_service.vision_service.VisionService(
#             recording=recording,
#             object_class="",
#             no_write=True,
#             host=None,
#             disable_network=True,
#             enable_visualization_fullscreen=False,
#         )
#         vs.time_since_last_busy_msg_interval_sec = 0
#         vs.max_sec_since_last_busy = 1
#         vs.enable_visualization = enable_visualization
#         vs.camera_fisheye.set_pre_recorded_loop_count(0)
#         vs.collect()

#         test_helpers.BaseTest.assert_threads_stopped(self)

#     def test_receive_classification_result(self):
#         """
#         Classification + Visualization
#         """
#         enable_visualization = False
#         self.setup_logging()

#         # yellow technic brick
#         recording = os.path.abspath(
#             os.path.join(
#                 os.path.dirname(__file__), "..", "data", "rec_2022-04-21_12-42-30"
#             )
#         )

#         # dummy server
#         s = sorter.network.tcp_server.TcpServer("0.0.0.0", 5005, DummyCommandHandler)
#         s.start()
#         time.sleep(1)

#         # vision
#         tdc = sorter.vision_service.vision_service.VisionService(
#             recording=recording,
#             object_class="technic_brick",
#             no_write=False,
#             host="127.0.0.1",
#             disable_network=False,
#             enable_visualization_fullscreen=False,
#         )
#         tdc.enable_visualization = enable_visualization
#         tdc.camera_fisheye.set_pre_recorded_loop_count(0)
#         tdc.soft_estop_enabled = False

#         # mock object detector
#         class DummyObjectDetector:
#             def __init__(self) -> None:
#                 self.trigger = False

#             def set_trigger(self, trigger):
#                 self.trigger = trigger

#             def process_frame(
#                 self,
#                 collect_loop_frame_index,
#                 frame,
#                 enable_visualization,
#                 enable_viz_mask,
#             ):
#                 frame_viz = frame.copy()
#                 component_list = []
#                 belt_busy = False
#                 return self.trigger, frame_viz, component_list, belt_busy

#             def currently_inhibited(self, collect_loop_frame_index):
#                 return False

#             def get_statistics(self):
#                 return {
#                     "count_triggered": 0,
#                     "count_double_object": 0,
#                 }

#         tdc.od = DummyObjectDetector()

#         # collection loop
#         tdc.loop_setup()
#         frame_index = 0
#         while True:
#             # trigger on frame 105
#             tdc.od.set_trigger(frame_index == 105)

#             # send classification result at frame 120
#             if frame_index == 120:
#                 msg = (
#                     "CLR 0 plate1x 1 100 1.218174 "
#               "W3siY2xhc3MiOiAicGxhdGUxeCIsICJwcm9iYWJpbGl0eSI6IDF9LCB7ImNsYXNzIjogImJyaWNrMXgiLCAi"
#               "cHJvYmFiaWxpdHkiOiAwfSwgeyJjbGFzcyI6ICJicmljazJ4Ii"
#               "wgInByb2JhYmlsaXR5IjogMH1d W3siY2x"
#               "hc3MiOiAicGxhdGUxeCIsICJwcm9iYWJpbGl0eSI6IDF9LCB7ImNsYXNzIjogImJyaWNrMXgiLCAicHJvYmF"
#               "iaWxpdHkiOiAwfSwgeyJjbGFzcyI6ICJicmljazJ4IiwgInByb2JhYmlsaXR5IjogMH1d"
#                 )
#                 s.broadcast(bytes(msg, "utf-8"))

#             stop = tdc.loop_step()
#             if stop:
#                 break

#             if frame_index >= 121:
#                 time.sleep(0.5)

#             frame_index += 1

#         tdc.stop()
#         s.stop()

#         test_helpers.BaseTest.assert_threads_stopped(self)

#     def test_malformed_incoming_msg(self):
#         self.setup_logging()

#         # yellow technic brick
#         recording = os.path.abspath(
#             os.path.join(
#                 os.path.dirname(__file__), "..", "data", "rec_2022-04-21_12-42-30"
#             )
#         )

#         # catch exceptions in other threads
#         sorter.third_party.catch_all_thread_exception.install()

#         # dummy server
#         s = sorter.network.tcp_server.TcpServer("0.0.0.0", 5005, DummyCommandHandler)
#         s.start()
#         time.sleep(1)

#         # run vision service client
#         tdc = sorter.vision_service.vision_service.VisionService(
#             recording=recording,
#             object_class="technic_brick",
#             no_write=False,
#             host="127.0.0.1",
#             disable_network=False,
#             enable_visualization_fullscreen=False,
#         )
#         tdc.enable_visualization = False

#         # malformed msg - 2 msgs interlocked
#         s.broadcast(
#             b"HMV 329784.924058CLR 149 plate_modified 0.9071938991546631 "
#             b"10.56008284220217 0.1364444885006166 "
#             b"W3siY2xhc3MiOiAicGxhdGVfbW9kaWZpZWQiLCAicHJvYmFiaWxpdHkiOiAwLjkw"
#             b"NzE5Mzg5OTE1NDY2MzF9LCB7ImNsYXNzI"
#             b"jogImJyaWNrX21vZGlmaWVkIiwgInByb2JhYmlsaXR5IjogMC4wODU5MDc4Mzky"
#             b"Mzg2NDM2NX0sIHsiY2xhc3MiOiAiY2FyIi"
#             b"wgInByb2JhYmlsaXR5IjogMC4wMDM1NDEyMTkyODEwMzI2ODE1fV0= W3siY2xh"
#             b"c3MiOiAicGxhdGVfbW9kaWZpZWQiLCAicHJvYmFiaWxpdHkiOiAwLjk5OTk1Mjc"
#             b"5MzEyMTMzNzl9LCB7ImNsYXNzIjogInNsb3BlMXgiLCAicHJvYmFiaWxpdHkiOi"
#             b"AzLjE4NzEzNzU1NDA1MDQyM2UtMDV9LCB7ImNsYXNzIjogInJvdW5kX3Nsb3BlI"
#             b"iwgInByb2JhYmlsaXR5IjogNS42MjU5NzA1MTYxMjEwMTVlLTA2fV0="
#         )
#         time.sleep(0.5)

#         # stop network
#         tdc.stop()
#         s.stop()
#         time.sleep(2)

#         sorter.third_party.catch_all_thread_exception.collect_thread_exceptions()

#         test_helpers.BaseTest.assert_threads_stopped(self)

#     def test_collection_mode_inconsistent(self):
#         self.setup_logging()

#         # recording not actually needed
#         recording = os.path.abspath(
#             os.path.join(
#                 os.path.dirname(__file__), "..", "data", "rec_2022-04-21_12-42-30"
#             )
#         )

#         tdc = sorter.vision_service.vision_service.VisionService(
#             recording=recording,
#             object_class="technic_brick",
#             no_write=False,
#             host="127.0.0.1",
#             disable_network=True,
#             enable_visualization_fullscreen=False,
#         )
#         tdc.collection_mode = (
#             sorter.vision_service.vision_service.CollectionMode.INCONSISTENT
#         )

#         object_id = 0
#         predicted_class = "plate1x"
#         probability = 1.0
#         uniqueness = 100.0
#         average_process_time_sec = 1.218174
#         pred_low_list = [
#             {"class": "plate1x", "probability": 1},
#             {"class": "brick1x", "probability": 0},
#             {"class": "brick2x", "probability": 0},
#         ]
#         pred_high_list = [
#             {"class": "plate1x", "probability": 1},
#             {"class": "brick1x", "probability": 0},
#             {"class": "brick2x", "probability": 0},
#         ]

#         png_path, json_path = self.create_dummy_files()

#         # png/json exists
#         self.assertTrue(png_path.exists() and png_path.is_file())
#         self.assertTrue(json_path.exists() and json_path.is_file())

#         # fake detected objected
#         item = sorter.vision_service.vision_service.CollectLoopDataItem(object_id)
#         tdc.collect_loop_data_list = [item]
#         item.filepath = str(json_path.parent / json_path.stem)

#         # receive CLR
#         tdc.receive_classification_result(
#             object_id,
#             predicted_class,
#             probability,
#             uniqueness,
#             average_process_time_sec,
#             pred_low_list,
#             pred_high_list,
#         )

#         # png/json removed
#         self.assertFalse(png_path.exists() and png_path.is_file())
#         self.assertFalse(json_path.exists() and json_path.is_file())

#     def test_collection_mode_keep_non_class(self):
#         """
#         Only keep images if not class passed via cmd arg
#         """
#         self.setup_logging()

#         # recording not actually needed
#         recording = os.path.abspath(
#             os.path.join(
#                 os.path.dirname(__file__), "..", "data", "rec_2022-04-21_12-42-30"
#             )
#         )

#         cmd_arg_class = "plate1x"

#         tdc = sorter.vision_service.vision_service.VisionService(
#             recording=recording,
#             object_class=cmd_arg_class,
#             no_write=False,
#             host="127.0.0.1",
#             disable_network=True,
#             enable_visualization_fullscreen=False,
#         )
#         tdc.collection_mode = (
#             sorter.vision_service.vision_service.CollectionMode.KEEP_INCORRECT
#         )

#         png_path, json_path = self.create_dummy_files()

#         # with brick2x image shall be kept
#         # with plate1x shall be deleted
#         for predicted_class in ["brick2x", "plate1x"]:
#             object_id = 0
#             probability = 1.0
#             uniqueness = 100.0
#             average_process_time_sec = 1.218174
#             pred_low_list = [
#                 {"class": predicted_class, "probability": 1},
#                 {"class": "brick1x", "probability": 0},
#                 {"class": "brick2x", "probability": 0},
#             ]
#             pred_high_list = [
#                 {"class": predicted_class, "probability": 1},
#                 {"class": "brick1x", "probability": 0},
#                 {"class": "brick2x", "probability": 0},
#             ]

#             # png/json exists
#             self.assertTrue(png_path.exists() and png_path.is_file())
#             self.assertTrue(json_path.exists() and json_path.is_file())

#             # fake detected objected
#             item = sorter.vision_service.vision_service.CollectLoopDataItem(object_id)
#             tdc.collect_loop_data_list = [item]
#             item.filepath = str(json_path.parent / json_path.stem)

#             # receive CLR
#             tdc.receive_classification_result(
#                 object_id,
#                 predicted_class,
#                 probability,
#                 uniqueness,
#                 average_process_time_sec,
#                 pred_low_list,
#                 pred_high_list,
#             )

#             if predicted_class != cmd_arg_class:
#                 # wrong prediction, img kept
#                 self.assertTrue(png_path.exists() and png_path.is_file())
#                 self.assertTrue(json_path.exists() and json_path.is_file())
#             else:
#                 # correct prediction, img removed
#                 self.assertFalse(png_path.exists() and png_path.is_file())
#                 self.assertFalse(json_path.exists() and json_path.is_file())

#     def create_dummy_files(self):
#         dir_path = pathlib.Path(__file__).parent / "data"
#         json_path = dir_path / "train_yyyy-mm-dd_hh-mm-ss.json"
#         png_path = dir_path / "train_yyyy-mm-dd_hh-mm-ss.png"

#         # json
#         data = {}
#         with open(str(json_path), "w") as f:
#             json.dump(data, f, indent=2)
#         logging.info(f"Json written {json_path}")

#         # png
#         png_path.touch()

#         return png_path, json_path
