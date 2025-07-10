import test_mqtt_base


class AMQTTTest(test_mqtt_base.MqttTestCase):
    def test_general(self):
        self.setup_logging()
