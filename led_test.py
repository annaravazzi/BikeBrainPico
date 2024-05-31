'''
General pin tests using LEDs and buttons in MicroPython
'''

from machine import Pin
from time import sleep

#led = Pin('LED', Pin.OUT)
# button = Pin(5, Pin.IN, Pin.PULL_UP)
# led = Pin(3, Pin.OUT, value=0)
# print('Button test')

buzzer = Pin(22, Pin.OUT, Pin.PULL_DOWN)
buzzer.value(0)

while True:
    buzzer.value(1)
    sleep(0.5)
    buzzer.value(0)
    sleep(0.5)