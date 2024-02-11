# pureflow_fan_monitor

I have a couple of [PureFlow QT7 fanless fans](https://www.amazon.com/dp/B072PS3FR1?ref=ppx_yo2ov_dt_b_product_details&th=1) that I want to monitor and control through Home Assistant.

Specifically, I want Home Assistant to:

- Know if the fan is physically powered on or not
- Know the power level in use (0-9)
- Turn the fan on/off as part of automations 

I have solved this with a Raspberry Pi Zero W that monitors the fan's LCD display, determines what power level is in use, and then reports that value over MQTT. 

The pi also hosts a simple API that will toggle the fan's power (via IR) in response to HTTP messages.

This repo contains all of the documentation for setting this up.

# Hardware setup

Required components:

- **Raspberry Pi Zero W** - the brains of the whole thing
- **Raspberry Pi camera** - for taking pictures of the fan's LCD
- **[IR LED](https://www.amazon.com/dp/B00M1PN5TK?psc=1&ref=ppx_yo2ov_dt_b_product_details)** - IR transmitter that sends commands to the fan
- **220 Ohm resistor** - limits LED current draw and protects the PI
- **BC-337 transistor** - allows LED to be switched on/off by a GPIO pin
- **3d printed enclosure** - (optional) for mounting to the base of the fan

![Fritzing image showing a circuit from 5V to LED to collector side of transistor, with resistor between base and GPIO 15](/assets/circuit-layout_bb.png)

> [!NOTE]
> Other transistors and resistors might work. I'm not a hardware guy, so follow my instructions at your own risk ;)

# Software installation

This system relies on two Python scripts that are installed as systemd services:

- **pureflow_OCR.service** - Monitors the fan's LCD screen and reports the current power level over MQTT
- **pureflow_webIR.service** - Web app that triggers IR transmissions in response to HTTP requests

## Install ssocr

`ssocr` is a third party tool for doing OCR of "seven segment displays", e.g. the LCD that displays the power level.

```
sudo apt install ssocr -y
```

## Install pigpio daemon

This is needed by the PiIR package for sending IR commands.

```
sudo apt install pigpio -y
sudo systemctl enable pigpiod
sudo systemctl start pigpiod
```

## Create virtual Python environment (optional) 

It's recommended to use a virtual environment, unless this is the only Python script running on the pi. Even then, it's good practice. (If you skip this step, you'll need to adjust paths in the service files accordingly)

```
python3 -m venv .venv
. .venv/bin/activate
```

## Create the OCR service

```
pip install picamera Wand paho-mqtt Pillow

sudo cp displayOCR/pureflow_OCR.service /lib/systemd/system
sudo systemctl enable pureflow_OCR.service
sudo systemctl start pureflow_OCR.service
```

## Create the web service

```
pip install flask gunicorn PiIR

sudo cp webIR/pureflow_webIR.service /lib/systemd/system
sudo systemctl enable pureflow_webIR.service
sudo systemctl start pureflow_webIR.service
```

# Adding the monitor to the fan

> [!IMPORTANT]
> You will need to tweak the config file based on how you mount the camera to the fan.

## Placement

I place my monitors on the right hand side of the fans so that all of the cables can route behind the fan and be hidden from view.

You want the camera to be 90 degrees rotated with respect to the LCD display. Technically you should be able to use any orientation, since we rotate the image before processing it anyways, but in my testing I found *significant* performance degredation (at least on a pi zero w) when rotating by values other than exactly 90 degrees.

## Testing the camera

Access the web app at **http://<ip_or_host>:8080**. It will show you the current power reading, the image that last caused a *change* to the power reading, and the 10 most recent readings.

For each reading you'll see the raw image captured by the camera as well as the processed image that was used for OCR.  

![Screenshot of the web app showing recent images and readings](/assets/webIR-screenshot.png)

> [!NOTE]
> If it isn't cropping the image correctly for your placement either adjust the camera so that it is, or adjust the cropping region defined in `config.ini`.

## Adjusting the cropped region

> [!NOTE]
> The fan supports speeds up to 12, but I only go up to 4 or 5. I designed this app to read the rightmost digit only.

In the web app, click the "toggle bounding box" link. This will begin adding a red box over the images showing the region that is being cropped and processed.

Load one of those images into an image editor and determine the X,Y coordinates that cleanly isolate the rightmost digit of the LCD display. 

Put those coordinates into `config.ini`

```
X,Y of top-left start and bottom-right end of the cropping region

CROP_STARTX = 250	
CROP_STARTY = 0 	
CROP_ENDX = 640
CROP_ENDY = 222
```

> [!IMPORTANT]
> Don't forget to disable the bounding box once you get it working, it adds unnecessary load.

# Setting up Home Assistant

The monitor will post power level changes to Home Assistant via MQTT. 

Home Assistant will use a Template Switch to monitor the state and to trigger IR commands to the fan when the switch is toggled.

![Screenshot of Home Assistant showing a template switch and the current power level in a dashboard](/assets/ha-screenshot.png)

## MQTT setup

Edit `config.ini` and include your MQTT broker information.

```
SEND_MQTT = True
MQTT_HOST = your.mqtt.host
MQTT_TOPIC = home/rooms/office/deskfan/power
```

## MQTT sensor 

In Home Assistant, edit `configuration.yaml` and define a new sensor:

```
mqtt:
  sensor:
    - name: "Pureflow Fan Power Level"
      unique_id: "sensor_office_deskfan_power"
      state_topic: "home/rooms/office/deskfan/power"
      value_template: "{{ value_json.currentState }}"
      payload_available: "online"
      payload_not_available: "offline"
      json_attributes_topic: "home/rooms/office/deskfan"
      json_attributes_template: "{{ value_json | tojson }}"
```

## MQTT REST command

In Home Assistant, edit `configuration.yaml` and define a new REST command. This allows HA to make HTTP calls to the web service.

```
rest_command:
  pureflow_fan_toggle_power:
    url: "http://<ip_or_hostname_of_pi>:8080/toggle"
    method: GET
```

## Template switch

A Template Switch in Home Assistant will act as a power button. It uses the current power level to determine if the fan is "on" or "off" and calls the appropriate service to switch states.

```
switch:
  - platform: template
    switches:
      pureflow_fan_dynamic_switch:
        unique_id: "pureflow_fan_dynamic_switch"
        friendly_name: "Pureflow Fan Dynamic Switch"
        value_template: "{{ not states('sensor.pureflow_fan_power_level') in ['off', '0'] }}"
        turn_on:
          - condition: state
            entity_id: switch.pureflow_fan_dynamic_switch
            state: 'off'
          - service: rest_command.pureflow_fan_toggle_power
        turn_off:
          - condition: state
            entity_id: switch.pureflow_fan_dynamic_switch
            state: 'on'
          - service: rest_command.pureflow_fan_toggle_power
```

# Troubleshooting

## Checking the logs of a running service

`sudo journalctl -f -u pureflow_OCR.service`

## Running the web server manually for testing

`flask run --host=0.0.0.0 --port 8080 --debug`
