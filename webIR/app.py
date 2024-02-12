import datetime, os, glob
from flask import Flask, render_template
from piir import Remote
from pathlib import Path

# For handling the config file
from configparser import ConfigParser, ExtendedInterpolation

# For RPC to the OCR app
from multiprocessing.connection import Client

#--------------------------------------------------------
# Load config file
#
# (See config file for setting documentation)
#
# Some of these can be changed at runtime through RPC calls, others
# cannot. For simplicity everything is a mutable global.
#--------------------------------------------------------
config = ConfigParser(interpolation=ExtendedInterpolation())
config.read('../config.ini')
STATIC_FILE_PATH = config['Web'].get('STATIC_FILE_PATH')
LAST_CHANGE_TEXT_PATH = config['Web'].get('LAST_CHANGE_TEXT_PATH')
USE_RPC = config['Web'].getboolean('USE_RPC')
RPC_PORT = config['Web'].getint('RPC_PORT')
RPC_SECRET = bytes(config['Web'].get('RPC_SECRET', 'Super secret'), 'utf-8')
IR_LED_GPIO = config['Web'].getint('IR_LED_GPIO')

# Local settings (not in config)
AUTO_RERESH_SECONDS = 0

#--------------------------------------------------------
# Flash web app
#-----------------------------
app = Flask(__name__, 
	static_url_path='/static/', 
	static_folder=STATIC_FILE_PATH)

@app.route('/')
def hello_world():
	now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

	# Show current reading
	currentReading = '';
	if (os.path.exists(LAST_CHANGE_TEXT_PATH)):
		with open(LAST_CHANGE_TEXT_PATH) as filetext:
			for line in filetext:
				currentReading = currentReading + line

	# Show list of images, most recent first
	origImages = glob.glob(STATIC_FILE_PATH + '*-orig.jpg')
	origImages.sort(key=os.path.getmtime, reverse=True)
	origImageNames = [os.path.basename(x) for x in origImages]
	
	return render_template('index.html', now=now, autoRefreshSec=AUTO_RERESH_SECONDS, currentReading=currentReading, origImageNames=origImageNames)

@app.route('/toggle')
def toggle():
	remote = Remote('pureflow-IR-commands.json', IR_LED_GPIO)
	remote.send('power')
	return render_template('toggle.html')

@app.route('/toggleBoundingBox')
def toggleBoundingBox():
	if (not USE_RPC):
		abort(409)
	
	address = ('localhost', RPC_PORT)
	conn = Client(address, authkey=RPC_SECRET)
	conn.send('toggleBoundingBox')
	conn.close()
	return ('Success', 200)

@app.route('/toggleDebug')
def toggleDebug():
	if (not USE_RPC):
		abort(409)
	
	address = ('localhost', RPC_PORT)
	conn = Client(address, authkey=RPC_SECRET)
	conn.send('toggleDebug')
	conn.close()
	return ('Success', 200)


@app.route('/toggleAutoRefresh')
def toggleAutoRefresh():
	global AUTO_RERESH_SECONDS

	if (AUTO_RERESH_SECONDS == 0):
		AUTO_RERESH_SECONDS = 1
	else:
		AUTO_RERESH_SECONDS = 0

	return ('Success', 200)
