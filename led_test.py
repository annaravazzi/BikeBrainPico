'''
General pin tests using LEDs and buttons in MicroPython
'''

from machine import Pin
from time import sleep

#led = Pin('LED', Pin.OUT)
button = Pin(5, Pin.IN, Pin.PULL_UP)
led = Pin(3, Pin.OUT, value=0)
print('Button test')

while True:
    if button.value() == 0:
        print('Button pressed')
        led.value(1)
    else:
        led.value(0)