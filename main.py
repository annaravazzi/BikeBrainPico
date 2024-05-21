# TODO: 
# TEST BLE COMMUNICATION
# MAYBE? ADD LED FOR ALARM MODE (BLINKING)
# ADD RESET SYSTEM?

'''
Imports
'''
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
import ujson as json
from math import sqrt, sin, cos, atan2, radians
import lib.dht11 as dht11

'''
Constants
'''
# Pins #
# LCD
LCD_SCK  = 14
LCD_CS   = 13
LCD_MOSI = 15
# RFID
RFID_SCK  = 2
RFID_MISO = 0
RFID_MOSI = 3
RFID_CS   = 1
RFID_RST  = 10
# GPS
GPS_TX = 8
GPS_RX = 9
# SD
SD_SCK  = 6
SD_MISO = 4
SD_MOSI = 7
SD_CS   = 5
# SIM800L
SIM_RX = 17
SIM_TX = 16
# Others
TEMP         = 28
STOP_START   = 27
PAUSE_RESUME = 26
BUZZER       = 12

# User data #
NUMBER = ""
WEIGHT = 0.0

# Other constants #
CARD_ID = 3186880355
BLE_PACKET_SIZE = 20
ALARM_DISTANCE = 0.0001

'''Functions'''

# Initializing functions #
def init_LCD ():
    spi = SPI(1, baudrate=1_000_000, sck=Pin(LCD_SCK, Pin.OUT), mosi=Pin(LCD_MOSI, Pin.OUT))
    cs = Pin(LCD_CS, Pin.OUT, value=0)
    fbuf = lcd12864.LCD12864(spi, cs)
    return fbuf

def init_RFID ():
    rfid = mfrc522.MFRC522(spi_id=0, sck=RFID_SCK, miso=RFID_MISO, mosi=RFID_MOSI, cs=RFID_CS, rst=RFID_RST)
    return rfid

def init_GPS ():
    gps_module = UART(1, baudrate=9600, tx=Pin(GPS_TX), rx=Pin(GPS_RX))
    time_zone = -3
    gps = micropyGPS.MicropyGPS(time_zone)
    return gps_module, gps

def init_SD ():
    cs = Pin(SD_CS, Pin.OUT)
    spi = SPI(0, baudrate=1000000, polarity=0, phase=0, bits=8, firstbit=SPI.MSB, sck=Pin(SD_SCK), mosi=Pin(SD_MOSI), miso=Pin(SD_MISO))
    sd = sdcard.SDCard(spi, cs)
    return sd

def init_BLE (): 
    ble = bluetooth.BLE()
    sp = BLESimplePeripheral(ble)
    return sp

def init_SIM800L ():
    sim_card = sim800l.SIM800(0, uart_rx=Pin(SIM_RX), uart_tx=Pin(SIM_TX), baud=115200)
    sim_card.send_command(f'AT+CMGF={"1"}')
    return sim_card

# Display updates #
def lcd_no_info (lcd, ble_connected):
    lcd.fill(0)
    lcd.text('No user data', 0, 0, 1)
    lcd.text('Please send data', 0, 10, 1)
    if ble_connected:
        lcd.text('Bluetooth on', 0, 50, 1)
    else:
        lcd.text('Bluetooth off', 0, 50, 1)
    lcd.show()

def lcd_idle (lcd, data_synced, ble_connected, gps_connected):
    lcd.fill(0)
    lcd.text('Press button', 0, 0, 1)
    lcd.text('to start', 0, 10, 1)
    if data_synced:
        lcd.text('Data synced', 0, 20, 1)
    else:
        if not ble_connected:
            lcd.text('Unsynced data', 0, 20, 1)
            lcd.text('Please connect', 0, 30, 1)
            lcd.text('to phone', 0, 40, 1)
    if not gps_connected:
        lcd.text('No GPS signal', 0, 50, 1)
    lcd.show()

def lcd_sending (lcd, synced):
    lcd.fill(0)
    lcd.text('Syncing data', 0, 0, 1)
    lcd.text('Please wait', 0, 10, 1)
    lcd.text('...', 0, 20, 1)
    if synced:
        lcd.text('Done', 0, 30, 1)
    lcd.show()

def lcd_running_paused (lcd, speed, chronometer, date, current_time, calories, temp, dist, gps_connected, dist_unit='km'):
    lcd.fill(0)
    lcd.text(current_time, 0, 0, 1)
    lcd.text(date, 48, 0, 1)
    lcd.text(chronometer_str(chronometer), 0, 10, 1)
    if dist_unit == 'km':
        lcd.text(str(round(dist,1)) + 'km', 0, 20, 1)
    else:
        lcd.text(str(dist*1000) + 'm', 0, 20, 1)
    lcd.text(str(round(calories,1)) + 'kcal', 0, 30, 1)
    lcd.text(str(round(speed,1)) + 'km/h', 0, 40, 1)
    lcd.text(str(round(temp,1)) + '°C', 88, 50, 1)
    if not gps_connected:
        lcd.text('No signal', 0, 50, 1)
    lcd.show()

def lcd_saving (lcd, error):
    lcd.fill(0)
    lcd.text('Saving...', 0, 0, 1)
    if error:
        lcd.text('Error saving', 0, 10, 1)
        lcd.text('Please wait', 0, 20, 1)
    lcd.show()

def lcd_alarm (lcd, gps_connected):
    lcd.fill(0)
    lcd.text('Alarm on', 0, 0, 1)
    if gps_connected:
        lcd.text('GPS signal OK', 0, 10, 1)
    else:
        lcd.text('No GPS signal', 0, 10, 1)
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

# Calculate distance between two points using Haversine formula (in km)
def distance (lat0, lon0, lat1, lon1):
    R = 6371.0
    lat0 = radians(lat0)
    lon0 = radians(lon0)
    lat1 = radians(lat1)
    lon1 = radians(lon1)
    dlon = lon1 - lon0
    dlat = lat1 - lat0
    a = sin(dlat / 2)**2 + cos(lat0) * cos(lat1) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

# Estimate calories burned (kcal/s) using speed in mph, weight in kg
# Source: https://sites.google.com/site/compendiumofphysicalactivities/Activity-Categories/bicycling?authuser=0
def calculate_calories (weight, speed):
    mets = 0.0
    if speed < 5.5:
        mets = 3.5
    elif speed < 9.4:
        mets = 5.8
    elif speed < 11.9:
        mets = 6.8
    elif speed < 13.9:
        mets = 8.0
    elif speed < 15.9:
        mets = 10.0
    elif speed < 19.0:
        mets = 12.0
    else:
        mets = 15.8
    return (mets * 3.5 * weight / 200.0) / 60.0

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

def write_data_SD (vfs, data):
    uos.mount(vfs, "/sd")
    i = 0
    for file in uos.ilistdir("/sd"):
        i = max(i, int(file[0].split("_")[1].split(".")[0]))
    i += 1
    if data:
        try:
            with open("/sd/data_" + str(i) + ".txt", "w") as f:
                for line in data:
                    f.write(line + "\n")
                f.write('$') # End of file character
                uos.umount("/sd")
            return True
        except:
            uos.umount("/sd")
            return False

def read_data_SD (vfs):
    data = []
    tmp = []
    uos.mount(vfs, "/sd")
    for file in uos.ilistdir("/sd"):
        with open("/sd/" + file[0], "r") as f:
            tmp.append(file[0])
            tmp.append(f.read())
            data.append(tmp)
            tmp = []
            
    uos.umount("/sd")    
    return data

def is_SD_empty (vfs):
    uos.mount(vfs, "/sd")
    if len(list(uos.ilistdir("/sd"))) == 0:
        uos.umount("/sd")
        return True
    uos.umount("/sd")
    return False

def send_data_BLE (sp, data):
    data_bytes = bytes(data, 'utf-8')
    num_bytes = len(data_bytes)
    packets = [data_bytes[i:i+BLE_PACKET_SIZE] for i in range(0, num_bytes, BLE_PACKET_SIZE)]
    for packet in packets:
        if sp.is_connected():
            sp.send(packet)
        else:
            return False
    return True

def save_user_data (data):
    with open("user_data.json", "w") as f:
        json.dump(data, f)

def on_rx(data):
    string_data = data.decode('utf-8').rstrip()
    global NUMBER, WEIGHT, user_data_flag
    NUMBER = string_data.split(",")[0]
    WEIGHT = float(string_data.split(",")[1])
    user_data_flag = True

def receive_data_BLE (sp):
    if sp.is_connected():
        sp.on_write(on_rx)

def send_sms (sim800l, message, number):
    # send sms
    sim800l.send_command("AT+CMGS=\"" + number + "\"")
    sim800l.uart.write(message + chr(26))
    
def button_pressed (button, t_current, t_button):
    if button.value() == 0:
        if t_current - t_button > 100:
            return True
    return False

def rfid_read (rfid, CARD_ID, t_current=None, t_rfid=None):
    if t_current and t_rfid:
        flag = (t_current - t_rfid > 500)    # Debouncing
    else:
        flag = True
    if flag:
        rfid.init()
        (stat, tag_type) = rfid.request(rfid.REQIDL)
        if stat == rfid.OK:
            (stat, uid) = rfid.SelectTagSN()
            if stat == rfid.OK:
                card = int.from_bytes(bytes(uid), "little")
                if card == CARD_ID:
                    return True
    return False

def check_movement (lat0, lon0, lat1, lon1):
    return (distance(lat0, lon0, lat1, lon1) > ALARM_DISTANCE)

# Main

user_data_flag = False
try:
    with open("user_data.json", "r") as f:
        loaded_user_data = json.load(f)
        NUMBER = loaded_user_data["number"]
        WEIGHT = loaded_user_data["weight"]
        user_data_flag = True
except:
    pass

# States: no_info, idle, sending, running, pause, saving, alarm_idle, alarm_active
state = ('no_info' if not user_data_flag else 'idle')

# Initialize peripherals
lcd = init_LCD()
rfid = init_RFID()
gps_module, gps = init_GPS()
sd = init_SD()
vfs = uos.VfsFat(sd)
sp = init_BLE()
sim_card = init_SIM800L()
stop_start = Pin(STOP_START, Pin.IN, Pin.PULL_UP)
pause_resume = Pin(PAUSE_RESUME, Pin.IN, Pin.PULL_UP)
buzzer = Pin(BUZZER, Pin.OUT, Pin.PULL_DOWN, 0)
temp = dht11.DHT11(Pin(TEMP, Pin.OUT, Pin.PULL_DOWN))

# Current GPS data
lat = lon = speed = 0.0
date = clock = ""

# Registered data
start_date = start_clock = finish_date = finish_clock = ""
calories = 0.0
travel_distance = 0.0
max_speed = 0.0
coordinates = []
alarm_lat = alarm_lon = 0.0

# Data list format: [start date, start time, finish date, finish time, elapsed time, distance, max speed, calories, coordinates]
data_list = []

# Manage debouncing and periodic data updates
t_rfid = t_gps = t_ss_button = t_pr_button = t_buzzer = t_tracker = 0
t_current = 0

# Manage pausable chronometer
start_time = 0
sec_counter = 0
chronometer = (0, 0, 0)

# Main loop
while True:

    gps_data = micropyGPS.get_data(gps, gps_module)
    if gps_data:
        lat = gps_data[0]
        lon = gps_data[1]
        speed = gps_data[2]
        date = gps_data[3]
        clock = gps_data[4]

    t_current = time.ticks_ms()

    if state == 'no_info':
        lcd_no_info(lcd, sp.is_connected())
        receive_data_BLE(sp)
        if user_data_flag:
            save_user_data({"number": NUMBER, "weight": WEIGHT})
            state = 'idle'

    elif state == 'idle':
        if is_SD_empty(vfs):
            sync_flag = True
        else:
            sync_flag = False
            if sp.is_connected():
                ble_flag = True
                state = 'sending'
            else:
                ble_flag = False

        if gps_data:
            gps_flag = True
            if stop_start.value() == 0:
                send_sms(sim_card, "Exercise started at " + str(lat) + "," + str(lon), NUMBER)
                t_ss_button = time.ticks_ms()
                start_time = time.time()
                data_list.append(date) # Save start date
                data_list.append(clock) # Save start time
                state = 'running'
            elif rfid_read(rfid, CARD_ID):
                t_rfid = time.ticks_ms()
                alarm_lat = lat
                alarm_lon = lon
                send_sms(sim_card, "Alarm mode turned on at " + str(lat) + "," + str(lon), NUMBER)
                state = 'alarm_idle'
        else:
            gps_flag = False

        lcd_idle(lcd, sync_flag, ble_flag, gps_flag)

    elif state == 'sending':
        lcd_sending(lcd, False)
        time.sleep(1)
        data = read_data_SD(vfs)
        for d in data:
            if send_data_BLE(sp, d[1]):
                uos.remove("/sd/" + d[0])
        if is_SD_empty(vfs):
            lcd_sending(lcd, True)
            time.sleep(1)
            state = 'idle'

    elif state == 'running' or state == 'paused':

        sec_counter, start_time = incr_sec_counter(sec_counter, start_time)

        if gps_data:
            gps_flag = True
        else:
            gps_flag = False

        # Check if button was pressed to stop running
        if button_pressed (stop_start, t_current, t_ss_button):
            t_button = time.ticks_ms()
            data_list.append(date) # Save finish date (last received)
            data_list.append(clock) # Save finish time (last received)
            data_list.append(chronometer_str(chronometer)) # Save elapsed time
            data_list.append(str(round(travel_distance,1))) # Save distance
            data_list.append(str(round(max_speed,1))) # Save max speed
            data_list.append(str(round(calories,1))) # Save calories
            for coord in coordinates:
                data_list.append(coord) # Save coordinates
            coordinates = []
            chronometer = (0, 0, 0)
            sec_counter = 0
            state = 'saving'    # Update state
            send_sms(sim_card, "Exercise stopped at " + str(lat) + "," + str(lon), NUMBER)
        
        # Check if button was pressed to pause/resume
        if button_pressed (pause_resume, t_current, t_pr_button):
            t_pr_button = time.ticks_ms()
            state = 'pause' if state == 'running' else 'running'    # Update state

        if state == 'running':

            chronometer = calculate_time(sec_counter)

            if t_current - t_gps > 1000:    # Update from gps every second
                t_gps = time.ticks_ms()
                if gps_data:
                    if coordinates:
                        prev_lat = coordinates[-1].split(",")[0]
                        prev_lon = coordinates[-1].split(",")[1]
                    else:
                        prev_lat = lat
                        prev_lon = lon
                    # Save data to list
                    coordinates.append(str(lat) + "," + str(lon))
                    travel_distance += distance(prev_lat, prev_lon, lat, lon)

                    if gps_data[2] > max_speed:
                        max_speed = gps_data[2]
                    
                    calories += calculate_calories(WEIGHT, speed*0.6213711922)

        else:
            start_time = time.time()

        if travel_distance >= 1.0:
            dist_unit = 'km'
        else:
            dist_unit = 'm'
        lcd_running_paused(lcd, speed, chronometer, date, clock, calories, temp.temperature, travel_distance, gps_flag, dist_unit)


    elif state == 'saving':
        lcd_saving(lcd, False)
        time.sleep(1)
        if write_data_SD(vfs, data_list):
            data_list = []
            state = 'idle'
        else:
            lcd_saving(lcd, True)

    elif state == 'alarm_idle' or state == 'alarm_active':
        if gps_data:
            lcd_alarm(lcd, True)
        else:
            lcd_alarm(lcd, False)

        if rfid_read(rfid, CARD_ID, t_current, t_rfid):
            t_rfid = time.ticks_ms()
            buzzer.off()
            send_sms(sim_card, "Alarm deactivated at " + str(lat) + "," + str(lon), NUMBER)
            state = 'idle'
        
        if state == 'alarm_idle':
            if gps_data and check_movement(alarm_lat, alarm_lon, gps_data[0], gps_data[1]):
                send_sms(sim_card, "Alarm activated at " + str(lat) + "," + str(lon), NUMBER)
                state = 'alarm_active'
        else:
            if t_current - t_buzzer > 1000:
                t_buzzer = time.ticks_ms()
                if buzzer.value() == 0:
                    buzzer.on()
                else:
                    buzzer.off()
            if t_current - t_tracker > 1000:
                t_tracker = time.ticks_ms()
                if gps_data:
                    send_sms(sim_card, "Current location: " + str(lat) + "," + str(lon), NUMBER)
    else:
        pass

# while True:

#     if state == 'idle':
#         lcd.fill(0)
#         lcd.text('Press button', 0, 0, 1)
#         lcd.text('to start', 0, 10, 1)
#         lcd.show()

#     # Check if button was pressed to start running
#     if button.value() == 0:
        
#         send_sms(sim_card, "Program started running", NUMBER)

#         t_button = time.ticks_ms()  # Debouncing

#         # Initialize chronometer
#         start_time = time.time()
#         chronometer = (0, 0, 0)
#         sec_counter = 0

#         n += 1  # Record number
#         state = 'running'   # Update state

#     # Running loop
#     while state == 'running' or state == 'paused':
#         t_current = time.ticks_ms()

#         # Update chronometer
#         sec_counter, start_time = incr_sec_counter(sec_counter, start_time)

#         # Check if button was pressed to stop running
#         if button.value() == 0:
#             if t_current - t_button > 500:  # Debouncing
#                 t_button = time.ticks_ms()
#                 state = 'saving'    # Update state
#                 send_sms(sim_card, "Program stopped running", NUMBER)
#                 break

#         if t_current - t_rfid > 500:    # Debouncing
#             t_rfid = time.ticks_ms()
#             # Read RFID card to pause/resume
#             if rfid_read(rfid, CARD_ID):
#                 state = ('running' if state == 'paused' else 'paused')  # Update state

#         if state == 'running':
#             led.value(0)

#             chronometer = calculate_time(sec_counter)
#             data = micropyGPS.get_data(gps, gps_module)
#             if data:
#                 date = gps.date_string(formatting='s_dmy')
#                 current_time = gps.time_string()

#             # Read GPS data
#             if t_current - t_gps > 1000:    # Update GPS data every second
#                 t_gps = time.ticks_ms()
#                 if data:                    
#                     # Save GPS data
#                     lat = data[0]
#                     lon = data[1]
#                     speed = data[2]
#                     gps_data.append(str(lat) + "," + str(lon) + "," + str(speed))

#             update_lcd(lcd, lat, lon, speed, chronometer, date, current_time)

#         elif state == 'paused':
#             led.value(1)
#             start_time = time.time()
#             data = micropyGPS.get_data(gps, gps_module)
#             if data:
#                 date = gps.date_string(formatting='s_dmy')
#                 current_time = gps.time_string()
#                 update_lcd(lcd, lat, lon, speed, chronometer, date, current_time)

    
#     if state == 'saving':
#         led.value(0)

#         gps_data.insert(0, str(n))
#         gps_data.insert(1, chronometer_str(chronometer))

#         lcd.fill(0)
#         lcd.text('Saving...', 0, 0, 1)
#         lcd.show()
#         time.sleep(1)

#         # Save data in SD card
#         gps_data = write_data_SD(vfs, gps_data, n)

#         lcd.fill(0)
#         lcd.text('Send to phone?', 0, 0, 1)
#         lcd.text('Press button', 0, 10, 1)
#         lcd.show()

#         while button.value() == 1:
#             pass

#         lcd.fill(0)
#         lcd.text('Sending...', 0, 0, 1)
#         lcd.show()
#         time.sleep(1)
        
#         if send_data_BLE(sp, read_data_SD(vfs, n)):
#             lcd.text('Data sent', 0, 10, 1)
#             lcd.show()
#         else:
#             lcd.text('No connection', 0, 10, 1)
#             lcd.show()

#         time.sleep(1)

#         state = 'idle'