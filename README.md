# BikeBrain Raspberry Pi Pico code

This is the code for the device section of the project *BikeBrain* (click [here](https://github.com/GustavoAdamee/BikeBrainApp) to see the code for the app section)

## About the project

*BikeBrain* is a project that aims to offer cyclists a monitoring and security device to their bikes. It works as a cyclecomputer that supplies the user with training metrics through a screen and logs their performance in a mobile app synchronized with the device. It also counts with an alarm and GPS tracking system, sending updates on the bike's status to the user's phone.

This project was developed for the Integration Workshop 2 course, Computer Engineering — UTFPR.

Click [here](https://polarized-sunfish-007.notion.site/BikeBrain-1c0d6820db4348789af1ce9e1d309f0f) to know more.

## Hardware

- 1x Raspberry Pi Pico W (RP2040)
- 1x LCD Screen 128x64 ST7920
- 1x RFID module MFRC522
- 1x MicroSD card module
- 1x GPS module GY-NEO6MV2
- 1x GSM/GPRS SIM800L V2 module
- 1x DHT11 temperature sensor
- 1x Active buzzer
- 2x Push buttons
- 1x LED
- 3x Resistors (1k, 10k, 100)
- 1x BC548 transistor

## Software

- MicroPython v1.22.2
- MicroPico VSCode extension
- Various drivers for the modules (source is on top of each file)

## Circuit