import logging
import sys


class GPIOController:
    def __init__(self, on_device) -> None:
        self.on_device = on_device
        self.stopped = False

        # pin mapping
        pin_vf1 = 11
        pin_vf2 = 9
        pin_storage = 10
        pin_belt = 12

        # real device
        if self.on_device:
            try:
                import RPi.GPIO as GPIO
            except ModuleNotFoundError:
                logging.error(
                    "Module RPi.GPIO not found. Either install via 'pip install RPi.GPIO' or add --nomachine argument"
                )
                sys.exit(1)
            GPIO.setmode(GPIO.BCM)

            GPIO.setup(pin_vf1, GPIO.OUT)
            self.pwm_vf1 = GPIO.PWM(pin_vf1, 100)
            self.pwm_vf1.start(0)
            self.pwm_vf1.ChangeDutyCycle(0)

            GPIO.setup(pin_vf2, GPIO.OUT)
            self.pwm_vf2 = GPIO.PWM(pin_vf2, 100)
            self.pwm_vf2.start(0)
            self.pwm_vf2.ChangeDutyCycle(0)

            GPIO.setup(pin_storage, GPIO.OUT)
            self.pwm_storage = GPIO.PWM(pin_storage, 100)
            self.pwm_storage.start(0)
            self.pwm_storage.ChangeDutyCycle(0)

            GPIO.setup(pin_belt, GPIO.OUT)
            self.pwm_belt = GPIO.PWM(pin_belt, 100)
            self.pwm_belt.start(0)
            self.pwm_belt.ChangeDutyCycle(0)

    def set_stopped(self, stopped):
        self.stopped = stopped
        self.set_speed_vibration_feeder(0)
        self.set_speed_storage(0)

    def set_speed_vf1(self, percentage: int):
        if self.stopped:
            percentage = 0

        assert 0 <= percentage <= 100
        if self.on_device:
            self.pwm_vf1.ChangeDutyCycle(percentage)
        # logging.info('Vibration feeder 1 duty cycle: %d' % percentage)

    def set_speed_vf2(self, percentage: int):
        if self.stopped:
            percentage = 0

        assert 0 <= percentage <= 100
        if self.on_device:
            self.pwm_vf2.ChangeDutyCycle(percentage)
        # logging.info('Vibration feeder 2 duty cycle: %d' % percentage)

    def set_speed_storage(self, percentage: int):
        if self.stopped:
            percentage = 0

        assert 0 <= percentage <= 100
        if self.on_device:
            self.pwm_storage.ChangeDutyCycle(percentage)
        # logging.info('Storage duty cycle: %d' % percentage)

    def set_speed_belt(self, percentage: int):
        if self.stopped:
            percentage = 0

        assert 0 <= percentage <= 100
        if self.on_device:
            self.pwm_belt.ChangeDutyCycle(percentage)
        # logging.info('Belt duty cycle: %d' % percentage)
