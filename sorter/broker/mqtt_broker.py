import asyncio
import logging
import os
import tempfile
import threading
from pathlib import Path

from amqtt.broker import Broker
from passlib.hash import sha512_crypt

# Optional: Set the logging level for amqtt to avoid excessive output.
# logging.getLogger("amqtt").setLevel(logging.WARNING)


class MqttBrokerThread(threading.Thread):
    """
    A thread that runs an aMQTT Broker instance.
    """

    def __init__(self, host="0.0.0.0", port=1883):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self._password_file = None

        session_secret = os.environ.get("SESSION_SECRET")
        if not session_secret:
            logging.error("SESSION_SECRET environment variable not set.")
            raise ValueError("SESSION_SECRET environment variable not set.")

        self._password_file = tempfile.NamedTemporaryFile(mode="w+", delete=False)
        hashed_password = sha512_crypt.hash(session_secret)
        self._password_file.write(f"sorter:{hashed_password}\n")
        self._password_file.flush()

        self.config = {
            "listeners": {
                "default": {"type": "tcp", "bind": f"{self.host}:{self.port}"}
            },
            "sys_interval": 10,
            "topic-check": {"enabled": False},
            "plugins": {
                "amqtt.plugins.authentication.FileAuthPlugin": {
                    "password_file": self._password_file.name
                }
            },
            "auth": {
                "allow-anonymous": False,
            },
        }

        self.broker = None
        self.loop = None
        self.started_event = threading.Event()
        self.stop_event = None

    def run(self):
        """The main entry point for the thread."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.stop_event = asyncio.Event()

        try:
            self.loop.run_until_complete(self.main())
        finally:
            self.cleanup()

    async def main(self):
        """The core async logic for starting and stopping the broker."""
        self.broker = Broker(config=self.config)
        await self.broker.start()
        logging.info(f"aMQTT broker started on {self.host}:{self.port}")
        self.started_event.set()

        try:
            await self.stop_event.wait()
        except asyncio.CancelledError:
            pass
        finally:
            logging.info("Shutting down broker...")
            await self.broker.shutdown()

    def stop(self):
        """Signals the thread to stop the broker and exit."""
        if self.loop and self.stop_event and not self.stop_event.is_set():
            self.loop.call_soon_threadsafe(self.stop_event.set)

    def cleanup(self):
        """Cleans up resources like the temporary password file."""
        if self._password_file:
            try:
                self._password_file.close()
                os.remove(self._password_file.name)
                logging.info(f"Removed temporary password file: {self._password_file.name}")
            except Exception as e:
                logging.error(f"Error cleaning up password file: {e}")
        try:
            tasks = asyncio.all_tasks(loop=self.loop)
            for task in tasks:
                task.cancel()
            self.loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        finally:
            self.loop.close()
