#!/usr/bin/env python3

import paho.mqtt.client as mqtt
from datetime import datetime
import os
import time
import json
import threading
import logging as log

log.basicConfig(filename='/var/tmp/job.log', filemode='w', level=log.INFO, format='[%(asctime)s]- %(message)s', datefmt='%d-%m-%Y %I:%M:%S %p')

now=datetime.now()
time_stamp=now.strftime("%m/%d/%Y, %H:%M:%S")
path = "/etc/entomologist/"
with open(path + "ento.conf",'r') as file:
	data=json.load(file)

MQTT_BROKER = data["device"]["ENDPOINT_URL"]
SERIAL_ID = data["device"]["SERIAL_ID"]
PORT = 8883
MQTT_KEEP_INTERVAL = 44
JOB_CLIENT = f'JobReciverClient-{SERIAL_ID}'
JOB_TOPIC = f'cameraDevice/job/{SERIAL_ID}'
QoS = 0

rootCA = path + 'cert/AmazonRootCA1.pem'
cert = path + 'cert/certificate.pem.crt'
privateKey = path + 'cert/private.pem.key'


def updateData(name,keyValue):
        data={}
        with open(path + "ento.conf",'r') as file:
            data=json.load(file)
            dataa=data[name]
        with open(path + "ento.conf",'w') as file:
            dataa.update(keyValue)
            data.update({name:dataa})
            json.dump(data,file,indent=4,separators=(',', ': '))


def on_message(client, userdata, message):
	
	jobconfig = json.loads(message.payload.decode('utf-8'))
	log.info(f"Job Recieved\n{jobconfig}")

	t_job = threading.Thread(name='parse', target=parse,args=(jobconfig,client))
	t_job.start()

def parse(jobconfig,client):
	try:
		if jobconfig['deviceId'] == SERIAL_ID:
			if 'Device-Test-Flag' in jobconfig['device'] and jobconfig['device']['Device-Test-Flag']=='True':
				updateData("device",{"TEST_FLAG":"True"})
				testDuration = jobconfig['device']['Device-Test-Duration']
				updateData("device",{"TEST_DURATION":testDuration})

			if 'Device-On-Time' in jobconfig['device']:
				onTime=jobconfig['device']['Device-On-Time']
				updateData("device",{"ON_TIME":onTime})

			if 'Device-Off-Time' in jobconfig['device']:
				offTime=jobconfig['device']['Device-Off-Time']
				updateData("device",{"OFF_TIME":offTime})
			log.info("JOB RECIEVED and PARSED Successfully..")
	except:
		log.info("Tried to parsed and failed..")



def on_connect(client, userdata, flags, rc):
	if rc == 0:
		log.info("Job client connected")
		
	else:
		log.info("Bad connection: Unable to connect")

def start_recieving_job():
	log.info("I have started receiving job..")
	global jobClient

	jobClient = mqtt.Client(JOB_CLIENT)

	jobClient.tls_set(rootCA, cert, privateKey)

	jobClient.on_connect = on_connect
	jobClient.on_message = on_message

	# In case of connection error (due to internet) it will retry to connect.
	while True:
		try:
			jobClient.connect(MQTT_BROKER, PORT, MQTT_KEEP_INTERVAL)
			break
		except:
			log.info("Im in except block of startjob")
			time.sleep(5)

	jobClient.loop_forever()

def restart_recieving_job():

	global jobClient

	jobClient.disconnect()

	log.info(f"{'-'*20} Restarting Job Reciever {'-'*20}")

	time.sleep(3)

	start_recieving_job()


log.info("JOB STARTED RUNNING..")
start_recieving_job()
	
