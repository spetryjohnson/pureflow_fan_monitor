import os, sys, datetime, time, io 

# For handling the config file
from configparser import ConfigParser, ExtendedInterpolation

# For image generation and preparation
from shutil import copyfile
from picamera import PiCamera
from wand.image import Image
from PIL import Image as PilImage, ImageDraw as PilImageDraw

# For shelling out to ssocr
import subprocess

# For MQTT
import paho.mqtt.client as mqtt
import json

# For RCP communication
import _thread
from multiprocessing.connection import Listener
from multiprocessing import ProcessError as MultiprocProcessError

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
CROP_STARTX = config['OCR'].getint('CROP_STARTX')
CROP_STARTY = config['OCR'].getint('CROP_STARTY')
CROP_ENDX = config['OCR'].getint('CROP_ENDX')
CROP_ENDY = config['OCR'].getint('CROP_ENDY')
SEND_MQTT = config['OCR'].getboolean('SEND_MQTT')
MQTT_HOST = config['OCR'].get('MQTT_HOST')
MQTT_TOPIC = config['OCR'].get('MQTT_TOPIC')
MAX_TIME_BETWEEN_MQTT_LOG_SEC = config['OCR'].getint('MAX_TIME_BETWEEN_MQTT_LOG_SEC')
ADD_CROP_BOX_TO_IMG = config['OCR'].getboolean('ADD_CROP_BOX_TO_IMG')
DEBUG = config['OCR'].getboolean('DEBUG')
STATIC_FILE_PATH = config['OCR'].get('STATIC_FILE_PATH')
LAST_CHANGE_ORIG_PATH = config['OCR'].get('LAST_CHANGE_ORIG_PATH')
LAST_CHANGE_PROC_PATH = config['OCR'].get('LAST_CHANGE_PROC_PATH')
LAST_CHANGE_TEXT_PATH = config['OCR'].get('LAST_CHANGE_TEXT_PATH')
LAST_ERROR_PATH = config['OCR'].get('LAST_ERROR_PATH')
MAX_IMAGES_TO_KEEP = config['OCR'].getint('MAX_IMAGES_TO_KEEP')
LOOP_DELAY_SEC = config['OCR'].getfloat('LOOP_DELAY_SEC')
USE_RPC = config['OCR'].getboolean('USE_RPC')
RPC_PORT = config['OCR'].getint('RPC_PORT')
RPC_SECRET = bytes(config['OCR'].get('RPC_SECRET', 'Super secret'), 'utf-8')

#--------------------------------------------------------
# Use a background thread to listen to commands from the web app 
#--------------------------------------------------------
def startListenerThread():
	global DEBUG, ADD_CROP_BOX_TO_IMG
	
	address = ('localhost', RPC_PORT)
	listener = Listener(address, authkey=RPC_SECRET)

	while True:
		if (DEBUG): print('[listener] Waiting for connection...')
		try:
			conn = listener.accept()
		except MultiprocProcessError:
			print('[listener] Error making connection. Could be invalid secret key from client')
			continue
		
		if (DEBUG): print ('[listener] Connection accepted from ', listener.last_accepted)

		if (DEBUG): print ('[listener] Waiting for message...')
		msg = conn.recv()
		if (DEBUG): print ('[listener] Received: ', msg)
		
		# Ugh I'm on python 3.9 which doesn't have switch case. 
		# What is this the 1700s?
		if (msg == 'toggleBoundingBox'):
			ADD_CROP_BOX_TO_IMG = not ADD_CROP_BOX_TO_IMG
		elif (msg == 'toggleDebug'):
			DEBUG = not DEBUG
		else:
			print('[listener] Unrecognized command: ', msg)
			
		if (DEBUG): print('[listener] Closing connection')
		conn.close()
	
	if (DEBUG): print('[listener] Closing listener')
	listener.close()

#--------------------------------------------------------
# Main program
#--------------------------------------------------------
if __name__ == '__main__':
	# local vars
	if (SEND_MQTT):
		mqttClient = mqtt.Client()
	
	imageCounter = 0			# For rotating image names
	valueOfLastChange = ''		# Value that last triggered a change in value
	timeOfLastChange = datetime.datetime.now()

	if (USE_RPC):
		print('Start background listener... ', end='', flush=True)
		_thread.start_new(startListenerThread, ())	
		print('Done!')

	print('Init camera....', end='', flush=True)
	with PiCamera() as camera:
		camera.resolution  = (640, 480)
		camera.contrast = 85
		time.sleep(2)
		print(' Ready!')

		# For each image we store the original image, the processed image,
		# and the OCR reading.

		while(True):
			now = datetime.datetime.now()	
			
			if (imageCounter >= MAX_IMAGES_TO_KEEP):
				imageCounter = 1
			else:
				imageCounter = imageCounter + 1

			pathPrefix = STATIC_FILE_PATH + 'reading-' + str(imageCounter)

			origImagePath = pathPrefix + '-orig.jpg'
			procImagePath = pathPrefix + '-processed.jpg'
			textReadingPath = pathPrefix + '-reading.txt'
			
			if (DEBUG): print('Getting image ' + origImagePath + '...', end='', flush=True)
			camera.capture(origImagePath)
			if (DEBUG): print('Done!')
			
			if (ADD_CROP_BOX_TO_IMG):
				if (DEBUG): print('Adding bounding box to ' + origImagePath + '... ', end='', flush=True)
				origImg = PilImage.open(origImagePath)
				draw = PilImageDraw.Draw(origImg)
				draw.rectangle((CROP_STARTX, CROP_STARTY, CROP_ENDX, CROP_ENDY), fill = None, outline="red")
				origImg.save(origImagePath, "JPEG")
				if (DEBUG): print('Done!')
			
			if (DEBUG): print('Processing image ' + procImagePath + '... ', end='', flush=True)
			with Image(filename = origImagePath) as image:
				with image.clone() as clone:
					clone.crop(CROP_STARTX, CROP_STARTY, CROP_ENDX, CROP_ENDY)
					clone.rotate(-90, 'black')
					clone.negate(False, None)
					clone.save(filename = procImagePath)
			if (DEBUG): print('Done!')
			
			try:
				if (DEBUG): print('Doing OCR on ' + procImagePath + '... ', end='', flush=True)
				
				try:
					newReading = subprocess \
					.check_output(['ssocr', '-d', '1', procImagePath], stderr=subprocess.PIPE) \
					.decode(sys.stdout.encoding) \
					.strip()
				except subprocess.CalledProcessError as e:
					# don't need to output error, message already sent to stderr/stdout
					# logging it can be useful though
					message = e.stderr.decode()
					if (DEBUG): print('ERROR: ' + message)
					
					f = open(LAST_ERROR_PATH, 'w')
					f.write(message)
					f.close()
					
					newReading = "off"
				
				# Special handling for known issues
				if (newReading == 'y'): newReading = '4'
				elif (newReading == 'e'): newReading = 'off'
				
				# Write reading to disk
				f = open(textReadingPath, 'w')
				f.write(newReading)
				f.close()
				
				if (DEBUG): print('(' + newReading + ') Done!')
				
				valueChanged = (newReading != valueOfLastChange)
				secondsSinceChange = abs(now - timeOfLastChange).seconds
				timeToReport = (secondsSinceChange > MAX_TIME_BETWEEN_MQTT_LOG_SEC)

				# If a change occurred then update the files that capture the last change trigger
				if (valueChanged):
					if (DEBUG): print('Value changed, updating "last update" files...')
					valueOfLastChange = newReading
					timeOfLastChange = now
					copyfile(origImagePath, LAST_CHANGE_ORIG_PATH)
					copyfile(procImagePath, LAST_CHANGE_PROC_PATH)
					copyfile(textReadingPath, LAST_CHANGE_TEXT_PATH)
					print(newReading + ' [NEW]')
				elif (timeToReport):
					print(newReading)

				# Notify MQTT
				if (SEND_MQTT and (valueChanged or timeToReport)):
					if (DEBUG): print('Sending MQTT update...', end='', flush=True)

					jsonData = json.dumps({ \
						"currentState": newReading, \
						"changedOn": now \
					}, default = str)

					mqttClient.connect(MQTT_HOST)	
					mqttClient.publish(MQTT_TOPIC, jsonData, retain=True)
					mqttClient.disconnect()	
					if (DEBUG): print('Done!')
				
				if (LOOP_DELAY_SEC > 0):
					time.sleep(LOOP_DELAY_SEC)
				
			# mqtt connection exception - slight delay then continue
			except Exception as e: 
				print('ERROR: ', e)
				time.sleep(3)
		