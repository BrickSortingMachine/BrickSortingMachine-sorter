import asyncio
import logging
import threading

from amqtt.broker import Broker

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
        self.config = {
            "listeners": {
                "default": {"type": "tcp", "bind": f"{self.host}:{self.port}"}
            },
            "sys_interval": 10,  # Publish $SYS topics every 10 seconds
            "topic-check": {"enabled": False},  # Allow any topic
            "plugins": [
                "amqtt.plugins.authentication.AnonymousAuthPlugin",
            ],
            "auth": {"allow-anonymous": True},
        }
        self.broker = None
        self.loop = None
        self.started_event = threading.Event()
        self.stop_event = None  # Will be an asyncio.Event

    def run(self):
        """The main entry point for the thread."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        self.stop_event = asyncio.Event()

        try:
            self.loop.run_until_complete(self.main())
        finally:
            try:
                tasks = asyncio.all_tasks(loop=self.loop)
                for task in tasks:
                    task.cancel()
                self.loop.run_until_complete(
                    asyncio.gather(*tasks, return_exceptions=True)
                )
            finally:
                self.loop.close()

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
        if self.loop and self.stop_event:
            self.loop.call_soon_threadsafe(self.stop_event.set)
