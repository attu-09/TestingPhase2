#!/usr/bin/env python3

import json
import shutil
import sys
from os import makedirs
from os.path import join
from time import sleep
import os
from awscrt import io, mqtt
from awsiot import iotidentity, mqtt_connection_builder
from update_boot_status import update_boot_status
import json

create_keys_and_certificate_response = None
register_thing_response = None


topic = "topic/${iot:Connection.Thing.Attributes[serialID]}/${iot:Connection.Thing.ThingName}"

with open(f"/etc/entomologist/ento.conf",'r') as file:
    data=json.load(file)

iot_endpoint = data["device"]["ENDPOINT_URL"] # AWS ARN
provisionstatus=data["device"]["PROVISION_STATUS"]

if provisionstatus=="True":
    print("device already provisioned")
    sys.exit("to retry provision, restart boot service...")

def on_connection_interrupted(connection, error, **kwargs):
	print(f"Connection interrupted. error: {error}")


def on_connection_resumed(connection, return_code, session_present, **kwargs):
	print(f"Connection resumed. return_code: {return_code} session_present: {session_present}")

	if return_code == mqtt.ConnectReturnCode.ACCEPTED and not session_present:
		print("Session did not persist. Resubscribing to existing topics...")
		resubscribe_future, _ = connection.resubscribe_existing_topics()
		resubscribe_future.add_done_callback(on_resubscribe_complete)


def on_resubscribe_complete(resubscribe_future):
	resubscribe_results = resubscribe_future.result()
	print(f"Resubscribe results: {resubscribe_results}")
	for resub_topic, qos in resubscribe_results['topics']:
		if qos is None:
			sys.exit(f"Server rejected resubscribe to topic: {resub_topic}")


def createkeysandcertificate_execution_accepted(response):
	try:
		global create_keys_and_certificate_response
		create_keys_and_certificate_response = response
		# print(f"Received a new message: {create_keys_and_certificate_response}")
		return
	except Exception as e:
		sys.exit(e)


def createkeysandcertificate_execution_rejected(rejected):
	sys.exit(f"CreateKeysAndCertificate Request rejected with code:'{rejected.error_code}' message:'{rejected.error_message}' statuscode:'{rejected.status_code}'")


def on_publish_create_keys_and_certificate(future):
	try:
		future.result()  # Raises exception if publish failed
		print("Published CreateKeysAndCertificate request..")
	except Exception as e:
		print("Failed to publish CreateKeysAndCertificate request.")
		sys.exit(e)


def registerthing_execution_accepted(response):
	try:
		global register_thing_response
		register_thing_response = response
		print(f"Received a new message {register_thing_response} ")
		return
	except Exception as e:
		sys.exit(e)


def registerthing_execution_rejected(rejected):
	sys.exit(f"RegisterThing Request rejected with code:'{rejected.error_code}' message:'{rejected.error_message}' statuscode:'{rejected.status_code}'")


def wait_for_create_keys_and_certificate_response():
	loop_count = 0
	while loop_count < 10 and create_keys_and_certificate_response is None:
		if create_keys_and_certificate_response is not None:
			break
		print(f"Waiting... CreateKeysAndCertificateResponse: {json.dumps(create_keys_and_certificate_response)}")
		loop_count += 1
		sleep(1)


def on_publish_register_thing(future):
	try:
		future.result()  # Raises exception if publish failed
		print("Published RegisterThing request..")
	except Exception as e:
		print("Failed to publish RegisterThing request.")
		sys.exit(e)


def wait_for_register_thing_response():
	loop_count = 0
	while loop_count < 10 and register_thing_response is None:
		if register_thing_response is not None:
			break
		loop_count += 1
		print(f"Waiting... RegisterThingResponse: {json.dumps(register_thing_response)}")
		sleep(1)

for _ in range(1):
    if provisionstatus=="False":
        # Parse connection configuration values
        print(iot_endpoint)
        root_cert_path = "/etc/entomologist/bootstrap/AmazonRootCA1.pem"
        print(root_cert_path)
        private_key_path = "/etc/entomologist/bootstrap/private.pem.key"
        print(private_key_path)
        claim_cert_path = "/etc/entomologist/bootstrap/certificate.pem.crt"
        print(claim_cert_path)
        provisioning_template_name = "CameraProvisioningTemplate"

        #device_serial_id = sys.argv[1]
        device_serial_id = data["device"]["SERIAL_ID"]

        # Establish connection to your AWS account's IoT endpoint
        event_loop_group = io.EventLoopGroup(1)
        host_resolver = io.DefaultHostResolver(event_loop_group)
        client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)

        mqtt_connection = mqtt_connection_builder.mtls_from_path(
        	endpoint=iot_endpoint,
        	cert_filepath=claim_cert_path,
        	pri_key_filepath=private_key_path,
        	client_bootstrap=client_bootstrap,
        	ca_filepath=root_cert_path,
        	client_id=device_serial_id,
        	on_connection_interrupted=on_connection_interrupted,
        	on_connection_resumed=on_connection_resumed,
        	clean_session=False,
        	keep_alive_secs=6)

        print(f"Connecting to {iot_endpoint} with client ID '{device_serial_id}'...")
        connected_future = mqtt_connection.connect()
        identity_client = iotidentity.IotIdentityClient(mqtt_connection)

        # Wait for connection to be fully established.
        connected_future.result()
        print("Connected!")

        # Subscribe to four AWS-managed topics required for obtaining a certificate issued by the fleet provisioning method
        createkeysandcertificate_subscription_request = iotidentity.CreateKeysAndCertificateSubscriptionRequest()
        print("Subscribing to CreateKeysAndCertificate Accepted topic...")
        createkeysandcertificate_subscribed_accepted_future, _ = identity_client.subscribe_to_create_keys_and_certificate_accepted(
        	request=createkeysandcertificate_subscription_request,
        	qos=mqtt.QoS.AT_LEAST_ONCE,
        	callback=createkeysandcertificate_execution_accepted)

        # Wait for subscription to succeed
        createkeysandcertificate_subscribed_accepted_future.result()

        print("Subscribing to CreateKeysAndCertificate Rejected topic...")
        createkeysandcertificate_subscribed_rejected_future, _ = identity_client.subscribe_to_create_keys_and_certificate_rejected(
        	request=createkeysandcertificate_subscription_request,
        	qos=mqtt.QoS.AT_LEAST_ONCE,
        	callback=createkeysandcertificate_execution_rejected)

        # Wait for subscription to succeed
        createkeysandcertificate_subscribed_rejected_future.result()

        registerthing_subscription_request = iotidentity.RegisterThingSubscriptionRequest(provisioning_template_name)
        print("Subscribing to RegisterThing Accepted topic...")
        registerthing_subscribed_accepted_future, _ = identity_client.subscribe_to_register_thing_accepted(
        	request=registerthing_subscription_request,
        	qos=mqtt.QoS.AT_LEAST_ONCE,
        	callback=registerthing_execution_accepted)

        # Wait for subscription to succeed
        registerthing_subscribed_accepted_future.result()

        print("Subscribing to RegisterThing Rejected topic...")
        registerthing_subscribed_rejected_future, _ = identity_client.subscribe_to_register_thing_rejected(
        	request=registerthing_subscription_request,
        	qos=mqtt.QoS.AT_LEAST_ONCE,
        	callback=registerthing_execution_rejected)
        # Wait for subscription to succeed
        registerthing_subscribed_rejected_future.result()




        # Publish message to CreateKeysAndCertificate and save the credentials returned to disk
        print("Publishing to CreateKeysAndCertificate...")
        publish_future = identity_client.publish_create_keys_and_certificate(request=iotidentity.CreateKeysAndCertificateRequest(), qos=mqtt.QoS.AT_LEAST_ONCE)
        publish_future.add_done_callback(on_publish_create_keys_and_certificate)

        wait_for_create_keys_and_certificate_response()

        if create_keys_and_certificate_response is None:
        	raise Exception('CreateKeysAndCertificate API did not succeed')

        # create_keys_and_certificate_response will contain the follow key-value pairs:
        ## certificate_id
        ## certificate_ownership_token
        ## certificate_pem
        ## private_key
        # certificate_id and certificate_ownership_token are used in a subsequent call to activate the certificate; they do not need to be retained.
        # certificate_pem and private_key should be securely stored on the device to make post-registration IoT API calls.



        long_term_credentials_path = "/etc/entomologist/cert/"


        claim_cert_long_term_path = join(long_term_credentials_path, "certificate.pem.crt")


        private_key_long_term_path = join(long_term_credentials_path, "private.pem.key")


        root_cert_long_term_path = join(long_term_credentials_path, "AmazonRootCA1.pem")


        # Creating Thing Request

        register_thing_request = iotidentity.RegisterThingRequest(
        	template_name=provisioning_template_name,
        	certificate_ownership_token=create_keys_and_certificate_response.certificate_ownership_token,
        	parameters={
                "serialID": device_serial_id
        				})

        print("Publishing to RegisterThing topic...")
        registerthing_publish_future = identity_client.publish_register_thing(register_thing_request, mqtt.QoS.AT_LEAST_ONCE)
        registerthing_publish_future.add_done_callback(on_publish_register_thing)

        wait_for_register_thing_response()
        # perm_config.optionxform = str  # Maintains capitalization of variables: https://stackoverflow.com/questions/1611799/preserve-case-in-configparser
        # perm_config["SETTINGS"] = {
        # 	"SECURE_CERT_PATH": long_term_credentials_path,
        # 	"ROOT_CERT": root_cert_long_term_path,
        # 	"CLAIM_CERT": claim_cert_long_term_path,
        # 	"SECURE_KEY": private_key_long_term_path,
        # 	"IOT_ENDPOINT": iot_endpoint,
        # 	"IOT_TOPIC": topic
        # }
        # with open(join(long_term_credentials_path, "perm_config.ini"), "w") as outfile:
        # 	perm_config.write(outfile)

        if register_thing_response is None:

        	sys.exit("Device Colud not be provisioned")
        else:
        	# Save long-term credentials to disk and create a config file defining variables for these files

        	makedirs(long_term_credentials_path, exist_ok=True)

        	with open(claim_cert_long_term_path, "w") as outfile:
        		outfile.write(create_keys_and_certificate_response.certificate_pem)

        	with open(private_key_long_term_path, "w") as outfile:
        		outfile.write(create_keys_and_certificate_response.private_key)

        	shutil.copy2(root_cert_path, root_cert_long_term_path)

        	update_boot_status(device_serial_id)

        	sys.exit("Device provisioned successfully")

  
