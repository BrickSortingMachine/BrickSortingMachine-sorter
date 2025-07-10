import asyncio
import threading
import logging
from amqtt.broker import Broker

# Optional: Silence the noisy amqtt logs during tests
logging.basicConfig(level=logging.WARNING)
logging.getLogger("amqtt").setLevel(logging.WARNING)


class AmqttBrokerThread(threading.Thread):
    """
    A thread that runs an amqtt Broker instance on a fixed port.
    """
    def __init__(self, host="localhost", port=1884):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.config = {
            "listeners": {
                "default": {"type": "tcp", "bind": f"{host}:{port}"}
            },
            "sys_interval": 0,  # Disable $SYS topics for testing
            "topic-check": {"enabled": False},  # Allow any topic
        }
        self.broker = None
        self.loop = None
        self.started_event = threading.Event()
        self.stop_event = threading.Event()

    def run(self):
        """The main entry point for the thread."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        # Run the main async task
        self.loop.run_until_complete(self.main())
        self.loop.close()

    async def main(self):
        """The core async logic for starting and stopping the broker."""
        # --- Create the broker instance NOW, inside the async method ---
        self.broker = Broker(config=self.config)
        await self.broker.start()
        
        print(f"\n(Broker Thread) AMQTT broker started on {self.host}:{self.port}")
        self.started_event.set()

        await self.loop.run_in_executor(None, self.stop_event.wait)

        print("\n(Broker Thread) AMQTT broker shutting down.")
        await self.broker.shutdown()

    def stop(self):
        """Signals the thread to stop the broker and exit."""
        if self.is_alive():
            self.stop_event.set()
            self.join()
