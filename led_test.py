'''
General pin tests using LEDs and buttons in MicroPython
'''

from machine import Pin, PWM
from time import sleep
from lib.ble_simple_peripheral import BLESimplePeripheral
import bluetooth

ble = bluetooth.BLE()
sp = BLESimplePeripheral(ble)

print(ble.config('mtu'))

def send_data_BLE (sp, data):
    data_bytes = bytes(data, 'utf-8')
    if sp.is_connected():
        sp.send(data_bytes)
        return True
    return False

data = ""
for i in range(206):
    data += str(i)

print(len(data.encode('utf-8')))

while True:
    if sp.is_connected():
        input()
        if send_data_BLE(sp, data):
            sleep(1)
            ble.gap_disconnect(64)

# led = Pin('LED', Pin.OUT)
# led.value(0)
# button = Pin(5, Pin.IN, Pin.PULL_UP)
# led = Pin(3, Pin.OUT, value=0)
# print('Button test')

# while True:
#     led.value(not led.value())
#     sleep(1)


# buzzer = PWM(Pin(22))
# buzzer.freq(200)

# while True:
#     buzzer.duty_u16(1001)
#     sleep(0.5)
#     buzzer.duty_u16(0)
#     sleep(0.2)