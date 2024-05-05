'''
MicroPython module to manage the LCD 128x64 display, commanded by the ST7920 controller, using SPI interface.
Original source: https://gist.github.com/phoreglad/ca01e9b66ff76abdb2e098ad47130921
'''


from machine import Pin, SPI
import framebuf


'''
When starting a transmission a start byte is required. It consists of 5 consecutive 〝1〞（sync character）. Serial transfer counter
will be reset and synchronized. Following 2 bits for read(1)/write(0)（RW）and register(0)/data(1) select（RS）. Last 4 bits is filled by 〝0〞。

After receiving the sync character and RW and RS bits, every 8 bits instruction/data will be separated into 2 groups. Higher
4 bits（DB7~DB4）will be placed in first section followed by 4 〝0〞. And lower 4 bits（DB3~DB0）will be placed in second
section followed by 4 〝0
'''

SYNC = 0b11111000

class LCD12864(framebuf.FrameBuffer):
    def __init__(self, spi, cs):
        self._spi = spi
        self._cs = cs
        self.width = 128
        self.height = 64
        self._buf = bytearray(128 * 64 // 2)
        self._bufmv = memoryview(self._buf)
        super().__init__(self._buf, 128, 64, framebuf.MONO_HLSB)
        self._disp_init()
    
    def _disp_init(self):
        self.write_cmd(0x30)
        self.write_cmd(0x30)
        self.write_cmd(0xC)
        self.write_cmd(0x34)
        self.write_cmd(0x34)
        self.write_cmd(0x36)
        
    def _send(self, buf):
        #self._cs(1)
        self._cs.value(1)
        self._spi.write(buf)
        self._cs.value(0)
        #self._cs(0)

    def _format_byte(self, byte):
        return [byte & 0xf0, (byte & 0xf) << 4]

    def write_cmd(self, cmd):
        buf = [SYNC]
        if isinstance(cmd, int):
            buf += self._format_byte(cmd)
        else:
            for c in cmd:
                buf += self._format_byte(c)
        self._send(bytes(buf))
        
    def write_data(self, data: bytearray):
        buf = [SYNC | 0x2]
        for b in data:
            buf += self._format_byte(b)
        self._send(bytes(buf))

    def set_address(self, x, y):
        self.write_cmd([0x80 + y, 0x80 + x])
        
    def show(self):
        for j in range(2):
            for i in range(32):
                self.set_address(8*j, i)
                self.write_data(bytearray(self._bufmv[(512 * j) + i * 16 : (512 * j) + (16 + i * 16)]))

# Test

import time

if __name__ == '__main__':
    
    spi = SPI(1, baudrate=1_000_000, sck=Pin(14, Pin.OUT), mosi=Pin(15, Pin.OUT), miso=Pin(12, Pin.IN))
    cs = Pin(13, Pin.OUT, value=0)
    fbuf = LCD12864(spi, cs)
    print(fbuf._spi)
    fbuf.fill(0)

    while True:
        fbuf.fill(0)
        fbuf.text('Hello!', 32, 32, 1)
        fbuf.show()
        time.sleep(1)
        fbuf.fill(0)
        fbuf.text('world!', 32, 32, 1)
        fbuf.show()
        time.sleep(1)
    
    # fbuf.text('Hello world!', 0, 0, 1)
    # fbuf.ellipse(64, 31, 32, 16, 1, True)
    # fbuf.ellipse(64, 31, 16, 32, 1, True)
    
    # fbuf.ellipse(64, 31, 22, 22, 1, True)
    
    # fbuf.ellipse(64, 31, 30, 14, 0, True)
    # fbuf.ellipse(64, 31, 14, 30, 0, True)
    # fbuf.ellipse(64, 31, 28, 12, 1, True)
    # fbuf.ellipse(64, 31, 12, 28, 1, True)
    
    # fbuf.ellipse(64, 31, 15, 15, 0, True)
    # fbuf.ellipse(64, 31, 10, 10, 1, True)
    # fbuf.ellipse(64, 31, 5, 5, 0, True)

    # fbuf.show()