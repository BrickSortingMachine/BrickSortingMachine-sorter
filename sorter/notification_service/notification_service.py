import http.client
import json
import logging
import pathlib
import sys
import urllib.parse

import sorter.network.tcp_client

if sys.platform == "win32":
    import winsound
if sys.platform == "linux":
    import playsound


class NSTcpClient(sorter.network.tcp_client.TcpClient):
    def __init__(
        self,
        host,
        port,
        name,
        type,
        retry_connection,
        auto_reconnect,
        notificaiton_service,
    ):
        super().__init__(host, port, name, type, retry_connection, auto_reconnect)
        self.notificaiton_service: NotificationService = notificaiton_service

    def event_msg_received(self, msg):
        part_list = str(msg, "utf-8").split(" ")

        try:
            # notification request
            if part_list[0] == "NTF":
                logging.info(f"Received notificaiton request - msg: {msg}")
                notification_type = part_list[1]
                notification_msg = " ".join(part_list[2:])
                self.notificaiton_service.notify(notification_type, notification_msg)
        except Exception:
            logging.error(
                "Decoding network message error - could be malformed/entangled messages"
            )


class NotificationService:
    def __init__(
        self, host: str, disable_network, theme, disable_pushover=False
    ) -> None:
        # network thread
        if not disable_network:
            self.tcp_client = NSTcpClient(
                host,
                5005,
                "NotificationService",
                "NotificationService",
                retry_connection=True,
                auto_reconnect=True,
                notificaiton_service=self,
            )
            self.tcp_client.start()
        else:
            self.tcp_client = None

        # theme
        self.theme = theme

        # pushover credentials
        credentials_fp = pathlib.Path(__file__).parents[2] / "pushover_credentials.json"
        if not credentials_fp.is_file() and not disable_pushover:
            raise Exception(
                'Pushover credetials missing. Copy "pushover_credetials.json.example" to "pushover_credentials.json" and adapt its contents'
            )
        if credentials_fp.is_file():
            with open(credentials_fp) as json_file:
                self.pushover_credentials = json.load(json_file)
        else:
            self.pushover_credentials = None

    def stop(self):
        if self.tcp_client is not None:
            self.tcp_client.stop()

    def notify(self, notification_type, notification_msg):
        if notification_type == "part_scanned":
            if sys.platform == "win32":
                winsound.Beep(800, 50)
                winsound.Beep(1000, 50)
            elif sys.platform == "linux":
                print("\a")

        elif notification_type == "scanner_inhibition_ended":
            if sys.platform == "win32":
                winsound.Beep(800, 50)
                winsound.Beep(800, 50)
            elif sys.platform == "linux":
                print("\a")

        elif (
            notification_type == "classification_result"
            or notification_type == "double_part_scanned"
        ):
            if notification_msg.startswith("inc_"):
                notification_msg = "skip"

            if notification_type == "double_part_scanned":
                notification_msg = "double"

            fp = pathlib.Path("sounds") / self.theme / (notification_msg + ".wav")
            if fp.is_file():
                if sys.platform == "win32":
                    winsound.PlaySound(str(fp), winsound.SND_FILENAME)
                elif sys.platform == "linux":
                    playsound.playsound(str(fp))
            else:
                logging.warn(f'No sound for part name "{notification_msg}"')

        elif notification_type == "timeout_max_non_busy":
            # winsound.Beep(1000, 300)
            # winsound.Beep(800, 300)
            # winsound.Beep(1000, 300)
            # winsound.Beep(800, 300)
            msg = f"Ran out of parts ({notification_msg}s)"
            self.pushover(msg)

        elif notification_type == "soft_estop":
            pass
            # stopped
            if notification_msg == "True":
                msg = "Soft E-Stop triggered"
                self.pushover(msg)
            #     winsound.Beep(1000, 300)
            #     winsound.Beep(800, 300)
            #     winsound.Beep(1000, 300)
            #     winsound.Beep(800, 300)
            #     self.pushover('Soft E-Stop triggered')

            # # resumed
            # else:
            #     winsound.Beep(1000, 100)
            #     winsound.Beep(1000, 100)
            #     winsound.Beep(1000, 100)

        else:
            raise Exception(f"Unsupported notification type '{notification_type}'")

    def pushover(self, msg):
        if self.pushover_credentials is None:
            logging.warning("Pushover disabled - no credentials")
            return

        conn = http.client.HTTPSConnection("api.pushover.net:443")
        conn.request(
            "POST",
            "/1/messages.json",
            urllib.parse.urlencode(
                {
                    "token": self.pushover_credentials["api_token"],
                    "user": self.pushover_credentials["user_key"],
                    "message": msg,
                }
            ),
            {"Content-type": "application/x-www-form-urlencoded"},
        )
