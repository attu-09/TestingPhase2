#!/usr/bin/env python3

import paho.mqtt.client as mqtt
import json
import time

with open(f"/etc/entomologist/ento.conf",'r') as file:
	data=json.load(file)

MQTT_BROKER = data["device"]["ENDPOINT_URL"] # AWS ARN
DEVICE_SERIAL_ID = data["device"]["SERIAL_ID"]
PORT = 8883
MQTT_KEEP_INTERVAL = 44
TOPIC = f"cameraDevice/{DEVICE_SERIAL_ID}/booted"

def on_connect(client, userdata, flags, rc):
	if rc == 0:
		print("Publish Client Connected\n")

	else:
		print("Bad connection: Publish Client")


def on_publish(client, userdata, message):

	print("Device Status set to Booted.")
	# print("File names published to topic.\n\nDisconnecting from publish client...\n")
	client.disconnect()

def update_boot_status(serialID):
	rootCA = '/etc/entomologist/cert/AmazonRootCA1.pem'
	cert = '/etc/entomologist/cert/certificate.pem.crt'
	privateKey = '/etc/entomologist/cert/private.pem.key'

	payload = {"serialID":serialID,"bootStatus":True}
	payload = json.dumps(payload)

	pubClient = mqtt.Client('digitalEntomologist')
	# Setting Certificates
	pubClient.tls_set(rootCA, cert, privateKey)

	# Callback functions
	pubClient.on_connect = on_connect
	pubClient.on_publish = on_publish

	# Connecting to broker and publishing payload.
	pubClient.connect(MQTT_BROKER, PORT, MQTT_KEEP_INTERVAL)
	pubClient.publish(TOPIC, payload, 1)
	data={}
	with open(f"/etc/entomologist/ento.conf",'r') as file:
		data=json.load(file)
		dataa=data["device"]

	with open(f"/etc/entomologist/ento.conf",'w') as file:
		dataa.update({"PROVISION_STATUS":"True"})
		data.update({"device":dataa})
		json.dump(data,file,indent=4,separators=(',', ': '))
	pubClient.loop_forever()
	# config for provision code
