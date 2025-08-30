import asyncio
import logging
import os
import tempfile
import threading

from amqtt.broker import Broker
from passlib.hash import sha512_crypt

# reduce amqtt debug logging
logging.getLogger("amqtt").setLevel(logging.WARNING)
logging.getLogger("amqtt.broker").setLevel(logging.WARNING)
logging.getLogger("transitions.core").setLevel(logging.WARNING)
logging.getLogger("passlib.utils.compat").setLevel(logging.WARNING)


class AmqttBrokerThread(threading.Thread):
    """
    A thread that runs an amqtt Broker instance on a fixed port.
    """

    def __init__(self, host="localhost", port=1884, session_secret=None):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self._password_file = None

        if not session_secret:
            raise ValueError("session_secret is required")

        self._password_file = tempfile.NamedTemporaryFile(mode="w+", delete=False)
        hashed_password = sha512_crypt.hash(session_secret)
        self._password_file.write(f"sorter:{hashed_password}\n")
        self._password_file.flush()

        self.config = {
            "listeners": {"default": {"type": "tcp", "bind": f"{host}:{port}"}},
            "sys_interval": 0,  # Disable $SYS topics for testing
            "topic-check": {"enabled": False},  # Allow any topic
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
        self.stop_event = None  # Will be an asyncio.Event

    def run(self):
        """The main entry point for the thread."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        # This event is tied to this specific loop
        self.stop_event = asyncio.Event()

        try:
            # Run the main async task
            self.loop.run_until_complete(self.main())
        finally:
            self.cleanup()

    async def main(self):
        """The core async logic for starting and stopping the broker."""
        # --- Create the broker instance NOW, inside the async method ---
        self.broker = Broker(config=self.config)
        await self.broker.start()

        self.started_event.set()

        try:
            await self.stop_event.wait()
        except asyncio.CancelledError:
            # This can happen during cleanup, and it's okay.
            pass
        finally:
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
            except Exception as e:
                logging.error(f"Error cleaning up password file: {e}")
        try:
            tasks = asyncio.all_tasks(loop=self.loop)
            for task in tasks:
                task.cancel()
            self.loop.run_until_complete(
                asyncio.gather(*tasks, return_exceptions=True)
            )
        finally:
            self.loop.close()
