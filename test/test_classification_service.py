# All ClassificationService Tests are currently deactivated since there is no
# public version of the test data available yet.

# import logging
# import sys
# import time
# import unittest

# import test_helpers

# import sorter.classification_service.classification_service
# import sorter.network.tcp_server


# class DummyCommandHandler(sorter.network.tcp_server.RequestHandler):
#     def __init__(self, request, client_address, server) -> None:
#         self.belt_busy = None
#         self.belt_busy_frame_index = None
#         self.last_classification_result = None
#         super().__init__(request, client_address, server)

#     def process_custom_command(self, message):
#         command = message[:3]

#         # CLR - Classification Result
#         if command == b"CLR":
#             # b'BST busy 57'
#             part_list = str(message, "utf-8").split(" ")
#             object_id = int(part_list[1])
#             predicted_class = part_list[2]
#             logging.info(
#                 f"Received command CLR - id: {object_id} prediction: {predicted_class}"
#             )
#             self.last_classification_result = predicted_class

#         elif command == b"NTF":
#             logging.info(f"Received notification command: {message}")

#         else:
#             raise Exception("Received unsupported command: " "%s" "" % command)


# class ClassificationServiceTest(unittest.TestCase, test_helpers.BaseTest):
#     def test_general(self):
#         """
#         General
#         """
#         self.setup_logging()

#         # dummy server
#         s = sorter.network.tcp_server.TcpServer("0.0.0.0", 5005, DummyCommandHandler)
#         s.start()
#         time.sleep(1)

#         cs = sorter.classification_service.classification_service.ClassificationService(
#             host="127.0.0.1",
#             enable_cnn=False,
#             model_fp="models/moved_crop_centrally.h5",
#         )
#         time.sleep(1)

#         if sys.platform == "win32":
#             path = b"rec_2022-04-21_12-42-30\\frame_000103_4744b5a14e0f17cb8cf12cb63afd1f70ef0c38ba.png"
#         elif sys.platform == "linux":
#             path = b"rec_2022-04-21_12-42-30/frame_000103_4744b5a14e0f17cb8cf12cb63afd1f70ef0c38ba.png"
#         else:
#             assert False

#         for i in range(1):
#             s.broadcast(b"CLF 5 " + path)
#             time.sleep(
#                 1.5
#             )  # classification waits 1s artificially before sending result
#             self.assertEqual(
#                 "plate1x", s.get_handler_list()[0].last_classification_result
#             )

#         # stop network
#         cs.stop()
#         s.stop()
#         time.sleep(0.5)

#         test_helpers.BaseTest.assert_threads_stopped(self)
