import asyncio
import logging
import threading

from amqtt.broker import Broker

# reduce amqtt debug logging
logging.getLogger("amqtt").setLevel(logging.WARNING)
logging.getLogger("amqtt.broker").setLevel(logging.WARNING)
logging.getLogger("transitions.core").setLevel(logging.WARNING)
logging.getLogger("passlib.utils.compat").setLevel(logging.WARNING)


class AmqttBrokerThread(threading.Thread):
    """
    A thread that runs an amqtt Broker instance on a fixed port.
    """

    def __init__(self, host="localhost", port=1884):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.config = {
            "listeners": {"default": {"type": "tcp", "bind": f"{host}:{port}"}},
            "sys_interval": 0,  # Disable $SYS topics for testing
            "topic-check": {"enabled": False},  # Allow any topic
            "plugins": [
                # enable anonymous login
                {
                    "amqtt.plugins.authentication.AnonymousAuthPlugin": {
                        "allow_anonymous": True
                    }
                }
            ],
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
            # Final cleanup
            try:
                tasks = asyncio.all_tasks(loop=self.loop)
                for task in tasks:
                    task.cancel()

                # Gather and wait for all tasks to finish cancelling
                self.loop.run_until_complete(
                    asyncio.gather(*tasks, return_exceptions=True)
                )
            finally:
                self.loop.close()

    async def main(self):
        """The core async logic for starting and stopping the broker."""
        # --- Create the broker instance NOW, inside the async method ---
        self.broker = Broker(config=self.config)
        await self.broker.start()

        logging.info(f"(Broker Thread) AMQTT broker started on {self.host}:{self.port}")
        self.started_event.set()

        try:
            await self.stop_event.wait()
        except asyncio.CancelledError:
            # This can happen during cleanup, and it's okay.
            pass
        finally:
            logging.info("(Broker Thread) AMQTT broker shutting down.")
            await self.broker.shutdown()

    def stop(self):
        """Signals the thread to stop the broker and exit."""
        if self.loop and self.stop_event:
            self.loop.call_soon_threadsafe(self.stop_event.set)
