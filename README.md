# pureflow_fan_monitor

I have a couple of [PureFlow QT7 fanless fans](https://www.amazon.com/dp/B072PS3FR1?ref=ppx_yo2ov_dt_b_product_details&th=1) that I want to monitor and control through Home Assistant.

The fans are IR controlled, which presents three challenges:

1. How to detect if the fan is actually receiving power
2. How to detect the current power level (0 - 12)
3. How to remotely turn the fan on / off

I have solved this with a Raspberry Pi Zero W that runs two services:
1. *OCR* - a camera monitors the fan's LCD display and the pi does OCR to determine power level
2. *IR Control* - an IR transmitter is used to send commands to the fan

This repo contains all of the documentation for setting this up.

## System overview

### Required hardware

- *Raspberry Pi Zero W* - the brains of the whole thing
- *Raspberry Pi camera* - for taking pictures of the fan's LCD
- *IR Transmitter* - sends commands to the fan
- *220 Ohm resistor* - limits LED current draw and protects the PI
- *BC-337 transistor* - allows LED to be switched on/off by a GPIO pin
- *3d printed enclosure* - for mounting to the base of the fan

(See below for hardware instuctions)

### Software components

- *[SSOCR utility](https://github.com/auerswal/ssocr)* - performs the OCR process
- *pureflow_OCR.service* - Python script, running as a service, that monitors the fan LCD and reports changes over MQTT
- *pureflow_webIR.service* - Simple Flask web app for managing program and issuing IR transmissions in response to HTTP API calls

## Installation

### Install ssocr
`sudo apt install ssocr -y`

### Install pigpio daemon

This is needed by the PiIR package for sending IR commands.

`sudo apt install pigpio -y`
`sudo systemctl enable pigpiod`
`sudo systemctl start pigpiod`

### Create python virtual environment

This isn't strictly necessary, but highly recommended. If you skip this step, you'll need to adjust some of the paths in the service files accordingly.

`python3 -m venv .venv`
`. .venv/bin/activate`

### Python dependencies

For the *displayOCR* service:
`pip install picamera`
`pip install Wand`
`pip install paho-mqtt`
`pip install Pillow`

For the *webIR* service:
`pip install flask`
`pip install gunicorn`
`pip install PiIR`

### Recommended additional preparation

This involves constant writing and reading of files and can wear out an sd card. To reduce the wear, I recommended that you create a small RAM disk using tmpfs so that the image files are all processed in memory and not on the card.

`sudo mkdir /var/tempmem`

`sudo nano /etc/fstab`

Add this line to the end of fstab:
`tmpfs /var/tempmem tmpfs nodev,nosuid,size=400M 0 0`

`sudo mount -a`

You can use a different path, just update the config file accordingly.

### Configuring the system services

## Hardware instructions

This is based on https://blog.gordonturner.com/2020/05/31/raspberry-pi-ir-receiver/

Other transistors and resistors might work. I'm not a hardware guy, I'm just cobbling together stuff I've found on the web. Follow my instructions at your own risk ;)