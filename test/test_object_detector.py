# All ObjectDetector Tests are currently deactivated since there is no
# public version of the test data available yet.

# import logging
# import os
# import unittest

# import cv2
# import test_helpers

# import sorter.vision_service.camera_capture
# import sorter.vision_service.object_detector


# class ObjectDetectorTest(unittest.TestCase, test_helpers.BaseTest):
#     def deactivated_test_positive_dectection(self):
#         """
#         True positive trigger on obj
#         """
#         enable_visualization = False
#         self.setup_logging()

#         recording = os.path.abspath(
#             os.path.join(
#                 os.path.dirname(__file__), "..", "data", "rec_2022-04-21_12-42-30"
#             )
#         )
#         cc = sorter.vision_service.camera_capture.CameraCapture("fisheye", recording)
#         cc.set_pre_recorded_loop_count(3)

#         od = sorter.vision_service.object_detector.ObjectDetector(
#             notification_client=None
#         )

#         trigger_frame_index = None
#         for frame_index in range(1000):
#             frame = cc.capture()
#             if frame is None:
#                 break

#             trigger, frame_viz, component_list, belt_busy = od.process_frame(
#                 frame_index, frame, enable_visualization
#             )
#             if trigger:
#                 logging.info(" Frame %03d: Object in trigger area" % frame_index)
#                 trigger_frame_index = frame_index

#             # viz
#             if enable_visualization:
#                 cv2.imshow("Video Capture", frame_viz)
#                 cv2.waitKey(10)

#         self.assertIsNotNone(trigger_frame_index)

#         test_helpers.BaseTest.assert_threads_stopped(self)

#     def test_second_object_in_roi_while_trigger(self):
#         """
#         2nd object in roi -> no trigger
#         """
#         enable_visualization = False
#         self.setup_logging()

#         recording = os.path.abspath(
#             os.path.join(
#                 os.path.dirname(__file__), "..", "data", "rec_2022-04-21_12-53-11"
#             )
#         )
#         cc = sorter.vision_service.camera_capture.CameraCapture("fisheye", recording)
#         cc.set_pre_recorded_loop_count(0)

#         od = sorter.vision_service.object_detector.ObjectDetector(
#             notification_client=None
#         )

#         trigger_frame_index = None
#         for frame_index in range(1000):
#             frame = cc.capture()
#             if frame is None:
#                 break

#             trigger, frame_viz, component_list, belt_busy = od.process_frame(
#                 frame_index, frame, enable_visualization
#             )
#             if trigger:
#                 trigger_frame_index = frame_index

#             # viz
#             if enable_visualization:
#                 cv2.imshow("Video Capture", frame_viz)
#                 cv2.waitKey(100)

#         self.assertIsNone(trigger_frame_index)

#         test_helpers.BaseTest.assert_threads_stopped(self)

#     def test_no_trigger_on_conveyor_gap(self):
#         """
#         Not trigger on conveyor gap
#         """
#         enable_visualization = False
#         self.setup_logging()

#         recording = os.path.abspath(
#             os.path.join(
#                 os.path.dirname(__file__), "..", "data", "rec_2022-04-21_12-42-15"
#             )
#         )
#         cc = sorter.vision_service.camera_capture.CameraCapture("fisheye", recording)
#         cc.set_pre_recorded_loop_count(0)

#         od = sorter.vision_service.object_detector.ObjectDetector(
#             notification_client=None
#         )

#         trigger_frame_index = None
#         for frame_index in range(1000):
#             frame = cc.capture()
#             if frame is None:
#                 break

#             trigger, frame_viz, component_list, belt_busy = od.process_frame(
#                 frame_index, frame, enable_visualization
#             )
#             if trigger:
#                 trigger_frame_index = frame_index

#             # viz
#             if enable_visualization:
#                 cv2.imshow("Video Capture", frame_viz)
#                 cv2.waitKey(100)

#         self.assertIsNone(trigger_frame_index)

#         test_helpers.BaseTest.assert_threads_stopped(self)

#     def test_trigger_front_in_area(self):
#         """
#         Front (left) corners need to be in x trigger area
#         """
#         self.setup_logging()

#         # left edge in trigger x
#         od = sorter.vision_service.object_detector.ObjectDetector(
#             notification_client=None
#         )
#         od.last_trigger_frame = -100
#         component_list = [
#             {
#                 "x": (od.trigger_area_min_x + od.trigger_area_max_x) / 2.0,
#                 "y": od.trigger_area_min_y,
#                 "w": 100,
#                 "h": 100,
#             }
#         ]
#         trigger = od.eval_trigger(frame_index=0, component_list=component_list)
#         self.assertTrue(trigger)

#         # left edge left of trigger x
#         od = sorter.vision_service.object_detector.ObjectDetector(
#             notification_client=None
#         )
#         od.last_trigger_frame = -100
#         component_list = [
#             {
#                 "x": od.trigger_area_min_x - 10,
#                 "y": od.trigger_area_min_y,
#                 "w": 100,
#                 "h": 100,
#             }
#         ]
#         trigger = od.eval_trigger(frame_index=0, component_list=component_list)
#         self.assertFalse(trigger)

#         test_helpers.BaseTest.assert_threads_stopped(self)

#     def test_belt_busy(self):
#         """
#         True positive belt busy
#         """
#         enable_visualization = False
#         self.setup_logging()

#         recording = os.path.abspath(
#             os.path.join(
#                 os.path.dirname(__file__), "..", "data", "rec_2022-04-21_12-42-30"
#             )
#         )
#         cc = sorter.vision_service.camera_capture.CameraCapture("fisheye", recording)
#         cc.set_pre_recorded_loop_count(0)

#         od = sorter.vision_service.object_detector.ObjectDetector(
#             notification_client=None
#         )

#         busy_frame_index = None
#         last_frame_belt_busy = False
#         for frame_index in range(1000):
#             frame = cc.capture()
#             if frame is None:
#                 break

#             trigger, frame_viz, component_list, belt_busy = od.process_frame(
#                 frame_index, frame, enable_visualization
#             )
#             if belt_busy and not last_frame_belt_busy:
#                 logging.info("Belt became busy: %d" % frame_index)
#                 busy_frame_index = frame_index
#             last_frame_belt_busy = belt_busy

#             # viz
#             if enable_visualization:
#                 cv2.imshow("Video Capture", frame_viz)
#                 cv2.waitKey(100)

#         self.assertEqual(53, busy_frame_index)

#         test_helpers.BaseTest.assert_threads_stopped(self)

#     def test_windows_adjustment(self):
#         """
#         Not trigger on conveyor gap, trigger on black part
#         """
#         enable_visualization = False
#         self.setup_logging()

#         recording = os.path.abspath(
#             os.path.join(
#                 os.path.dirname(__file__), "..", "data", "rec_2023-08-09_21-38-43"
#             )
#         )
#         cc = sorter.vision_service.camera_capture.CameraCapture("fisheye", recording)
#         cc.set_pre_recorded_loop_count(0)

#         od = sorter.vision_service.object_detector.ObjectDetector(
#             notification_client=None
#         )

#         trigger_frame_index = None
#         for frame_index in range(1000):
#             frame = cc.capture()
#             if frame is None:
#                 break

#             trigger, frame_viz, component_list, belt_busy = od.process_frame(
#                 frame_index, frame, enable_visualization, enable_viz_mask=True
#             )
#             if trigger:
#                 trigger_frame_index = frame_index

#             # viz
#             if enable_visualization:
#                 cv2.putText(
#                     frame_viz,
#                     f"{frame_index}",
#                     (10, 20),
#                     cv2.FONT_HERSHEY_SIMPLEX,
#                     0.5,
#                     (255, 255, 255),
#                     1,
#                     2,
#                 )
#                 cv2.imshow("Video Capture", frame_viz)
#                 if frame_index < 420:
#                     # in case false positive belt busy
#                     if belt_busy:
#                         cv2.waitKey(-1)
#                     else:
#                         cv2.waitKey(10)
#                 else:
#                     cv2.waitKey(100)

#             # must not be busy before 440 (belt seam must not trigger busy)
#             if frame_index < 420:
#                 self.assertFalse(belt_busy)

#         # must detect part
#         self.assertIsNotNone(trigger_frame_index)

#         test_helpers.BaseTest.assert_threads_stopped(self)
