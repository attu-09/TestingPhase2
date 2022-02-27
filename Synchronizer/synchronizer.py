import time
import json
from datetime import datetime
import requests
import subprocess
import logging as log

time.sleep(20)
log.basicConfig(filename="/var/log/ento/sync.log", encoding='utf-8', level=log.INFO,filemode='w',format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

global scriptStatus
scriptStatus=False
path = "/etc/entomologist/"
def entoDataWriter(parent,key,value):
    data=None
    with open(path + "ento.conf",'r') as file:
        data=json.load(file)
    data[parent][key]=value
    with open(path + "ento.conf",'w') as file:
        file.write(json.dumps(data,indent=4))

def testDevice(duration):
    log.info("Started testing the device")
    global scriptStatus
    if not scriptStatus:
        #start the services
        subprocess.call(["systemctl","restart","cam"])
        subprocess.call(["systemctl","restart","cloud"])
        log.info("Script restarted successfully of cam and cloud")
    log.info("Device is in testing state now")
    while duration:
        duration-=1
        time.sleep(1)
    log.info("Testing completed fully")
    entoDataWriter('device','TEST_FLAG','False')

def writeInScriptStatus(val): 
    global scriptStatus
    data=None
    with open(path + "scriptStatus.json",'r') as file:
        data=json.load(file)
    with open(path + "scriptStatus.json",'w') as file:
        data['status']=val
        file.write(json.dumps(data,indent=2))
        scriptStatus=val
    log.info(f"Writing in scriptstatus {val}")

def checkProvisonState():
    log.info("checking Provison state")
    while True:
        data=None
        with open(path + "ento.conf",'r') as file:
            data=json.load(file)

        if data['device']['PROVISION_STATUS']=='True':
            log.info("Device Provisoned")
            break
        else:
            log.info("Trying For Provison")
            try:
                #call for provisoning script
                subprocess.call(["python3","/usr/sbin/provision/boot.py"])
                
            except Exception as e:
                with open (path + "Error.txt", "a") as file:
                    file.write(str(e))
                log.error("Some error occured during provisoning")

        time.sleep(10)

def mainLoop():
    global scriptStatus
    log.info("STARTING MAIN LOOP..")
    while True:
        data=None
        with open(path + "ento.conf",'r') as file:
            data=json.load(file)

        if data['device']['TEST_FLAG']=='True':
            duration=int(data['device']['TEST_DURATION'])*60
            testDevice(duration)
        
        ON_TIME=int(data['device']['ON_TIME'])
        OFF_TIME=int(data['device']['OFF_TIME'])
        curTime=datetime.now().hour
        
        #Implement the raw logic of testFlag

        if ON_TIME<=curTime and curTime<OFF_TIME:
            if not scriptStatus:
                #Start both the services and write the status of the service in the status file
                subprocess.call(["systemctl","restart","cam"])
                subprocess.call(["systemctl","restart","cloud"])
                writeInScriptStatus(True)
                log.info("Cam and upload service started")
        else:
            log.info("Timing not matching")
            if scriptStatus:
                #Stop the service
                subprocess.call(["systemctl","stop","cam"])
                subprocess.call(["systemctl","stop","cloud"])
                writeInScriptStatus(False)
                log.info("Cam and upload service stopped")
    
        time.sleep(5)

if __name__=="__main__":
    log.info("SYNC STARTED..")
    entoDataWriter('device','TEST_FLAG','False')
    writeInScriptStatus(False)
    checkProvisonState()
    log.info("Starting JOB reciever..")
    subprocess.call(["systemctl","restart","jobreceiver"])
    mainLoop()

