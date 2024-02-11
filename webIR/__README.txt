------------------------------------------
Web app, run as a system service, that sends
IR commands to toggle the fan power.

The /toggle endpoint is hit by a REST command from HomeAssistant

Using Flask as the web framework, and hosting it in gunicorn
------------------------------------------

Resources:
  https://flask.palletsprojects.com/en/2.3.x/quickstart/
  https://developers.redhat.com/articles/2023/08/17/how-deploy-flask-application-python-gunicorn#the_application
  
The IR commands in pureflow-IR-commands.json were captured using
an IR receiver that is not part of the final build for this project.

--------------------------------------------
Run the pigpio daemon, which is needed by PiIR
--------------------------------------------
sudo apt install pigpio -y
sudo systemctl enable pigpiod
sudo systemctl start pigpiod

--------------------------------------------
Create Python virtual env to run the app
--------------------------------------------
python3 -m venv .venv
. .venv/bin/activate
pip install flask
pip install gunicorn
pip install PiIR

--------------------------------------------
To run the app manually in flask debug server
--------------------------------------------
flask run --host=0.0.0.0 --port 8080 --debug

--------------------------------------------
To run the app through gunicorn
--------------------------------------------
gunicorn --config gunicorn_config.py app:app

--------------------------------------------
To install this as a systemd service
--------------------------------------------
sudo cp pureflow_webIR.service /lib/systemd/system
sudo systemctl enable pureflow_webIR.service
sudo systemctl start pureflow_webIR.service

--------------------------------------------
To see system output
--------------------------------------------
sudo journalctl -f -u pureflow_webIR.service