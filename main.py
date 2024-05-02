import lcd12864
import mfrc522
import micropyGPS
import sdcard
import machine
import time
import uos

# Pins
RST = 10
LCD_SCK = 14
LCD_CS = 13
LCD_MOSI = 15
RFID_SCK = 2
RFID_MISO = 0
RFID_MOSI = 3
RFID_CS = 1
GPS_TX = 8
GPS_RX = 9
SD_SCK = 18
SD_MISO = 16
SD_MOSI = 19
SD_CS = 17

# State
state = 'updating'

# Initialize the LCD
def init_LCD ():
    spi = machine.SPI(1, baudrate=1_000_000, sck=machine.Pin(LCD_SCK, machine.Pin.OUT), mosi=machine.Pin(LCD_MOSI, machine.Pin.OUT))
    cs = machine.Pin(LCD_CS, machine.Pin.OUT, value=0)
    fbuf = lcd12864.LCD12864(spi, cs)
    return fbuf

# Initialize the RFID
def init_RFID ():
    rfid = mfrc522.MFRC522(spi_id = 0, sck = RFID_SCK, miso = RFID_MISO, mosi = RFID_MOSI, cs = RFID_CS, rst = RST)
    return rfid

# Initialize the GPS
def init_GPS ():
    gps_module = machine.UART(1, baudrate = 9600, tx = machine.Pin(8), rx = machine.Pin(9))
    time_zone = -3
    gps = micropyGPS.MicropyGPS(time_zone)
    return gps_module, gps

# Initialize the SD Card
def init_SD ():
    cs = machine.Pin(SD_CS, machine.Pin.OUT)

    spi = machine.SPI(0,
                    baudrate=1000000,
                    polarity=0,
                    phase=0,
                    bits=8,
                    firstbit=machine.SPI.MSB,
                    sck=machine.Pin(SD_SCK),
                    mosi=machine.Pin(SD_MOSI),
                    miso=machine.Pin(SD_MISO))
    
    # Initialize SD card
    sd = sdcard.SDCard(spi, cs)
    vfs = uos.VfsFat(sd)
    uos.mount(vfs, "/sd")

    return sd

# Main

lcd = init_LCD()
rfid = init_RFID()
gps_module, gps = init_GPS()
sd = init_SD()
led = machine.Pin('LED', machine.Pin.OUT, value=0)
button = machine.Pin(28, machine.Pin.IN, machine.Pin.PULL_UP)
gps_data = []

t_rfid = t_gps = t_button = 0


while True:
    curr_time = time.ticks_ms()

    if button.value() == 0:
        if curr_time - t_button > 1000:
            t_button = time.ticks_ms()
            state = 'stopped'

    if curr_time - t_rfid > 1000:
        t_rfid = time.ticks_ms()
        rfid.init()
        (stat, tag_type) = rfid.request(rfid.REQIDL)
        if stat == rfid.OK:
            (stat, uid) = rfid.SelectTagSN()
            if stat == rfid.OK:
                card = int.from_bytes(bytes(uid), "little")
                print("CARD ID: "+str(card))
                state = ('updating' if state == 'paused' else 'paused')

    if state == 'updating':
        led.value(0)
        # Read GPS data
        if curr_time - t_gps > 1000:
            t_gps = time.ticks_ms()
            data = micropyGPS.get_data(gps, gps_module)
            if data:
                latitude = data[0]
                longitude = data[1]
                speed = data[2]

                # Display GPS data
                lcd.fill(0)
                lcd.text(str(latitude), 0, 0, 1)
                lcd.text(str(longitude), 0, 10, 1)
                lcd.text(str(speed), 0, 20, 1)
                lcd.show()  
                
                # Save GPS data
                gps_data.append(str(latitude) + ", " + str(longitude) + ", " + str(speed))

    elif state == 'paused':
        led.value(1)
    
    elif state == 'stopped':
        led.value(0)
        lcd.fill(0)
        lcd.text('Saving...', 0, 0, 1)
        lcd.show()
        # Save GPS data to file
        if gps_data:
            with open("/sd/gps_data.txt", "w") as f:
                for line in gps_data:
                    f.write(line + "\r\n")
                gps_data = []
        uos.umount("/sd")
        break