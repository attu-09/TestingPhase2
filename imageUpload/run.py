#!/usr/bin/env python3

import paho.mqtt.client as mqtt
import datetime as dt
import subprocess
import random
import json
import ast
import time
import os
import multiprocessing
from sub import start_subscribe
from pub import start_publish
from imageUpload import image_upload_manager
from verification import start_verification

# AWS Setup

with open(f"/etc/entomologist/ento.conf",'r') as file:
	data=json.load(file)


DEVICE_SERIAL_ID = data["device"]["SERIAL_ID"]
provisionstatus=data["device"]["PROVISION_STATUS"]


MQTT_BROKER = data["device"]["ENDPOINT_URL"]
PORT = 8883
MQTT_KEEP_INTERVAL = 44
rootCA = '/etc/entomologist/cert/AmazonRootCA1.pem'
cert = '/etc/entomologist/cert/certificate.pem.crt'
privateKey = '/etc/entomologist/cert/private.pem.key'

BUCKET_NAME = "test-entomoligist"

# Publish Details

PUBLISH_CLIENT_NAME = 'digitalEntomologist'
PUBLISH_TOPIC = f'cameraDevice/generateURL/{DEVICE_SERIAL_ID}'
PUBLISH_QoS = 1

# Subscribe Details

SUBSCRIBE_CLIENT_NAME = 'iot-data'
SUBSCRIBE_TOPIC = f'cameraDevice/getURL/{DEVICE_SERIAL_ID}'
SUBSCRIBE_QoS = 0

# Verification Details

VERIFICATION_TOPIC = f'cameraDevice/fileUploaded/{DEVICE_SERIAL_ID}'

# Buffer Storage Path

BUFFER_IMAGES_PATH = '/media/mmcblk1p1/'


def generate_payload(filesList):



	payload = {
		"device-serialID":DEVICE_SERIAL_ID,
		"bucket-name":BUCKET_NAME,
		"files": filesList
	}

	return json.dumps(payload)

def signed_url_file_exist():

	while "signedUrls.json" not in os.listdir():
		time.sleep(2)
	return True


def upload_manager(filesList):

	batchSize = len(filesList)

	publishPayload = generate_payload(filesList)


	# Create start_subscribe and start_publish as two processes by implementing mulitprocessess.
	p1 = multiprocessing.Process(target = start_subscribe, args = [
		MQTT_BROKER,
		PORT,
		MQTT_KEEP_INTERVAL,
		SUBSCRIBE_CLIENT_NAME,
		SUBSCRIBE_TOPIC,
		SUBSCRIBE_QoS,
		rootCA,
		cert,
		privateKey])

	p2 = multiprocessing.Process(target = start_publish, args =[
		MQTT_BROKER,
		PORT,
		MQTT_KEEP_INTERVAL,
		PUBLISH_CLIENT_NAME,
		PUBLISH_TOPIC,
		PUBLISH_QoS,
		publishPayload,
		rootCA,
		cert,
		privateKey])

	p1.start()
	p2.start()
	p1.join()
	p2.join()

	# Create a better implementation once the signedUrls.json file has been created.
	if signed_url_file_exist():

		p3 = multiprocessing.Process(target = start_verification, args = [
		MQTT_BROKER,
		PORT,
		MQTT_KEEP_INTERVAL,
		SUBSCRIBE_CLIENT_NAME,
		VERIFICATION_TOPIC,
		SUBSCRIBE_QoS,
		batchSize,
		rootCA,
		cert,
		privateKey])

		p4 = multiprocessing.Process(target = image_upload_manager)

		p3.start()
		p4.start()
		p3.join()
		p4.join()


		os.remove('signedUrls.json')

def weather():
	p = subprocess.Popen("/usr/sbin/weather/hts221", stdout=subprocess.PIPE, shell=True) # Use script file instead.
	tim = str(dt.datetime.now())
	(output, err) = p.communicate()
	L = random.randint(400,600)
	lux = " , Light Intensity : "+str(L)
	p_status = p.wait()
	#print("Command output : ", output)
	#print("Command exit status/return code : ", p_status)
	file = open("weather.txt", "a")
	file.writelines("\n"+tim+" , "+", ".join(str(output)[2:len(output)-1].split("\\n"))+lux+"\n")
	file.close()
	time.sleep(3)

def weatherupload():
	filename = "weather.txt"

	if not os.path.isfile(filename):
		print('File does not exist.')
	else:
		with open(filename) as f:
			content = f.readlines()

	if os.path.exists(filename):
		time = str(dt.datetime.now())
		time = time.replace(" ", "_")
		string=BUFFER_IMAGES_PATH+"weather_"+time+"_"+DEVICE_SERIAL_ID+".txt"
		
		file = open(string, "a")
		file.writelines(content)
		file.close()
		os.remove(filename)

def main():
	while True:
		if provisionstatus=="True":
			weather()
			while len(os.listdir(BUFFER_IMAGES_PATH)):
				filesList = os.listdir(BUFFER_IMAGES_PATH)[:10]
				weatherupload()
				upload_manager(filesList)
			print("waiting...")
			time.sleep(1)
		else:
			print("waiting...")
			time.sleep(10)



if __name__ == '__main__':

	main()
