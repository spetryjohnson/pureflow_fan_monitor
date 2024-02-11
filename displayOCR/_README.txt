------------------------------------------
CLI app, run as a system service, that uses the ssocr service
to read the fan display. The values are written to a file
(which is read by the web app) and also pushed out over MQTT
------------------------------------------

--------------------------------------------
Install ssocr
--------------------------------------------
sudo apt install ssocr -Y

--------------------------------------------
RAM disk for storing images, to reduce wear on sd card
--------------------------------------------
https://www.hellojona.com/2017/06/create-a-ram-disk-tmpfs-in-raspberry-pi-3/

sudo mkdir /var/tempmem
sudo nano /etc/fstab
  -> tmpfs /var/tempmem tmpfs nodev,nosuid,size=400M 0 0
sudo mount -a

--------------------------------------------
Python virtual env
--------------------------------------------
python3 -m venv .venv
. .venv/bin/activate
pip install picamera
pip install Wand
pip install paho-mqtt
pip install Pillow

// Had some weird issue where pillow was installed in pi/.local/..., but I couldn't remove it with 
// pip --user, b/c it kept saying "--user" was unknown option. Finally fixed it by modifying
// the systemd service file to use the python packages from the pi user's folder

--------------------------------------------
To install this as a systemd service
--------------------------------------------
sudo cp pureflow_OCR.service /lib/systemd/system
sudo systemctl enable pureflow_OCR.service
sudo systemctl start pureflow_OCR.service

--------------------------------------------
To see system output
--------------------------------------------
sudo journalctl -f -u pureflow_OCR.service
