import lib.lcd12864 as lcd12864
import lib.mfrc522 as mfrc522
import lib.micropyGPS as micropyGPS
import lib.sdcard as sdcard
import lib.sim800l as sim800l
from lib.ble_simple_peripheral import BLESimplePeripheral
import bluetooth
from machine import Pin, SPI, UART
import time
import uos

CARD_ID = 3186880355
NUMBER = "+5541992130234"

# Pins
LCD_SCK = 14
LCD_CS = 13
LCD_MOSI = 15
RFID_SCK = 2
RFID_MISO = 0
RFID_MOSI = 3
RFID_CS = 1
RFID_RST = 10
GPS_TX = 8
GPS_RX = 9
SD_SCK = 6
SD_MISO = 4
SD_MOSI = 7
SD_CS = 5
SIM_RX = 17
SIM_TX = 16
BUTTON_PIN = 28

# States: idle, running, paused, saving
state = 'idle'

# Initialize the LCD
def init_LCD ():
    spi = SPI(1, baudrate=1_000_000, sck=Pin(LCD_SCK, Pin.OUT), mosi=Pin(LCD_MOSI, Pin.OUT))
    cs = Pin(LCD_CS, Pin.OUT, value=0)
    fbuf = lcd12864.LCD12864(spi, cs)
    return fbuf

# Initialize the RFID
def init_RFID ():
    rfid = mfrc522.MFRC522(spi_id = 0, sck = RFID_SCK, miso = RFID_MISO, mosi = RFID_MOSI, cs = RFID_CS, rst = RFID_RST)
    return rfid

# Initialize the GPS
def init_GPS ():
    gps_module = UART(1, baudrate = 9600, tx = Pin(GPS_TX), rx = Pin(GPS_RX))
    time_zone = -3
    gps = micropyGPS.MicropyGPS(time_zone)
    return gps_module, gps

# Initialize the SD Card
def init_SD ():
    cs = Pin(SD_CS, Pin.OUT)

    spi = SPI(0,
                    baudrate=1000000,
                    polarity=0,
                    phase=0,
                    bits=8,
                    firstbit=SPI.MSB,
                    sck=Pin(SD_SCK),
                    mosi=Pin(SD_MOSI),
                    miso=Pin(SD_MISO))
    
    sd = sdcard.SDCard(spi, cs)

    return sd

# Initialize the BLE
def init_BLE (): 
    ble = bluetooth.BLE()
    sp = BLESimplePeripheral(ble)
    return sp

def init_SIM800L ():
    sim_card = sim800l.SIM800(0, uart_rx=Pin(SIM_RX), uart_tx=Pin(SIM_TX), baud=115200)
    return sim_card

def rfid_read (rfid, CARD_ID):
    rfid.init()
    (stat, tag_type) = rfid.request(rfid.REQIDL)
    if stat == rfid.OK:
        (stat, uid) = rfid.SelectTagSN()
        if stat == rfid.OK:
            card = int.from_bytes(bytes(uid), "little")
            if card == CARD_ID:
                return True
    return False

# TODO: refine screen layout
def update_lcd (lcd, lat, lon, speed, chronometer):
    lcd.fill(0)
    lcd.text(chronometer_str(chronometer), 0, 0, 1)
    lcd.text(str(lat), 0, 10, 1)
    lcd.text(str(lon), 0, 20, 1)
    lcd.text(str(speed), 0, 30, 1)
    lcd.show()

# Increment the chronometer counter
def incr_sec_counter (counter, start_time):
    if time.time() - start_time >= 1:
        counter += 1
        start_time = time.time()
    return counter, start_time

# Convert total of seconds in hours, minutes and seconds
def calculate_time (sec_counter):
    hours = int(sec_counter / 3600)
    minutes = int((sec_counter % 3600) / 60)
    seconds = int(sec_counter % 60)
    return hours, minutes, seconds

def chronometer_str (chronometer):
    hours = str(chronometer[0])
    minutes = str(chronometer[1])
    seconds = str(chronometer[2])
    if len(hours) == 1:
        hours = "0" + hours
    if len(minutes) == 1:
        minutes = "0" + minutes
    if len(seconds) == 1:
        seconds = "0" + seconds
    return hours + ":" + minutes + ":" + seconds

def write_data_SD (vfs, data, n):
    uos.mount(vfs, "/sd")
    if data:
        with open("/sd/data_" + str(n) + ".txt", "w") as f:
            for line in data:
                f.write(line + "\r\n")
            data = []
    uos.umount("/sd")
    return data

def read_data_SD (vfs, n):
    data = ""
    uos.mount(vfs, "/sd")
    with open("/sd/data_" + str(n) + ".txt", "r") as f:
        data = f.read()
    uos.umount("/sd")
    return data

# TODO: send bigger data via packets
def send_data_BLE (sp, data):
    if sp.is_connected():
        sp.send(bytes(data, 'utf-8'))
        return True
    return False

def send_sms (sim800l, message, number):
    # set sms format (text)
    sim800l.send_command(f'AT+CMGF={"1"}')
    # send sms
    sim800l.send_command("AT+CMGS=\"" + number + "\"")
    sim800l.uart.write(message + chr(26))
    

# Main

# Initialize peripherals
lcd = init_LCD()

rfid = init_RFID()

gps_module, gps = init_GPS()

sd = init_SD()
vfs = uos.VfsFat(sd)

sp = init_BLE()

sim_card = init_SIM800L()

led = Pin('LED', Pin.OUT, value=0)
button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)

# GPS data
lat = lon = speed = 0
gps_data = []

# Manage debouncing and periodic data updates
t_rfid = t_gps = t_button = 0
t_current = 0

# Manage pausable chronometer
start_time = 0
sec_counter = 0
chronometer = (0, 0, 0)

# Number of records
n = 0

while True:

    # Check if button was pressed to start running
    if button.value() == 0:
        
        send_sms(sim_card, "Program started running", NUMBER)

        t_button = time.ticks_ms()  # Debouncing

        # Initialize chronometer
        start_time = time.time()
        chronometer = (0, 0, 0)
        sec_counter = 0

        n += 1  # Record number
        state = 'running'   # Update state

    # Running loop
    while state == 'running' or state == 'paused':
        t_current = time.ticks_ms()

        # Update chronometer
        sec_counter, start_time = incr_sec_counter(sec_counter, start_time)

        # Check if button was pressed to stop running
        if button.value() == 0:
            if t_current - t_button > 500:  # Debouncing
                t_button = time.ticks_ms()
                state = 'saving'    # Update state
                send_sms(sim_card, "Program stopped running", NUMBER)
                break

        if t_current - t_rfid > 500:    # Debouncing
            t_rfid = time.ticks_ms()
            # Read RFID card to pause/resume
            if rfid_read(rfid, CARD_ID):
                state = ('running' if state == 'paused' else 'paused')  # Update state

        if state == 'running':
            led.value(0)

            chronometer = calculate_time(sec_counter)
            
            # Read GPS data
            if t_current - t_gps > 1000:    # Update GPS data every second
                t_gps = time.ticks_ms()
                data = micropyGPS.get_data(gps, gps_module)
                if data:                    
                    # Save GPS data
                    lat = data[0]
                    lon = data[1]
                    speed = data[2]
                    gps_data.append(str(lat) + "," + str(lon) + "," + str(speed))

            update_lcd(lcd, lat, lon, speed, chronometer)

        elif state == 'paused':
            led.value(1)
            start_time = time.time()

    
    if state == 'saving':
        led.value(0)

        gps_data.insert(0, str(n))
        gps_data.insert(1, chronometer_str(chronometer))

        lcd.fill(0)
        lcd.text('Saving...', 0, 0, 1)
        lcd.show()
        time.sleep(1)

        # Save data in SD card
        gps_data = write_data_SD(vfs, gps_data, n)

        lcd.fill(0)
        lcd.text('Send to phone?', 0, 0, 1)
        lcd.text('Press button', 0, 10, 1)
        lcd.show()

        while button.value() == 1:
            pass

        led.value(1)
        lcd.fill(0)
        lcd.text('Sending...', 0, 0, 1)
        lcd.show()
        time.sleep(1)
        
        if send_data_BLE(sp, read_data_SD(vfs, n)):
            lcd.text('Data sent', 0, 10, 1)
            lcd.show()
        else:
            lcd.text('No connection', 0, 10, 1)
            lcd.show()

        state = 'idle'
