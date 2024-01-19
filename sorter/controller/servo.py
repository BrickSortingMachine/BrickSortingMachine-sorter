# import RPi.GPIO as GPIO


class Servo:
    def __init__(self, port_index_bcm, enable_device):
        self.port_index_bcm = port_index_bcm

        # start pigpio deamon
        # ret = os.system('sudo pigpiod')
        # print(ret)

        if enable_device:
            import pigpio as my_pigpio_package  # "as" is needed since otherwise namespace gets messed up

            self.pwm = my_pigpio_package.pi()
            self.pwm.set_mode(self.port_index_bcm, my_pigpio_package.OUTPUT)

            self.pwm.set_PWM_frequency(self.port_index_bcm, 50)
        else:
            self.pwm = None

    def goto(self, value):
        assert 0 <= value <= 1
        encoded = int(500.0 + value * 2000)
        self.pwm.set_servo_pulsewidth(self.port_index_bcm, encoded)

    def stop(self):
        self.pwm.set_PWM_dutycycle(self.port_index_bcm, 0)
        self.pwm.set_PWM_frequency(self.port_index_bcm, 0)
