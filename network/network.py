import os
import sys
import datetime
import time
import subprocess
import requests
import json
 
FILE = os.path.join(os.getcwd(), "networkinfo.log")
 
# creating log file in the currenty directory
# ??getcwd?? get current directory,
# os function, ??path?? to specify path
path = "/etc/entomologist/"
with open(path + "ento.conf",'r') as file:
	data=json.load(file)
def ping():
    # to ping a particular IP
    try:
        requests.get("https://www.google.com")
        return True
    except:
        return False
 
 
def calculate_time(start, stop):
   
    # calculating unavailability
    # time and converting it in seconds
    difference = stop - start
    seconds = float(str(difference.total_seconds()))
    return str(datetime.timedelta(seconds=seconds)).split(".")[0]
 
def upload_text_file(filepath):
    filename = filepath.split('/')[-1]
    url=f"https://w19bo3qwde.execute-api.us-east-1.amazonaws.com/v1/{bucket}/{filename}"
    try:
            
        http_resp = requests.put(url, data = open(filepath))
        print(f"Uploaded file with response code {http_resp.status_code}")
    except:
        print(f"Could not upload file. Response Code: {http_resp.status_code}")


def first_check():
    # to check if the system was already
    # connected to an internet connection
 
    if ping():
        # if ping returns true
        live = "\nCONNECTION ACQUIRED\n"
        print(live)
        connection_acquired_time = datetime.datetime.now()
        acquiring_message = "connection acquired at: " + str(connection_acquired_time).split(".")[0]
        print(acquiring_message)
        log = open('/usr/sbin/network/ifconfig.txt', 'w')
        log.write('ifconfig data for device : '+data['device']["SERIAL_ID"]+" at "+ str(connection_acquired_time).split(".")[0]+'\n')
        log.flush()  # <-- here's something not to forget!
        c = subprocess.Popen(['ifconfig'], stdout=log, stderr=log, shell=True)
        c = subprocess.Popen(['mmcli','-m','0'], stdout=log, stderr=log, shell=True)
        device=data['device']["SERIAL_ID"]
        log.close()
        upload_text_file('/usr/sbin/network/ifconfig.txt')

        #param={'device':device,'ip':ip}
        #resp=requests.get(url,params=param)

 
        with open(FILE, "a") as file:
           
            # writes into the log file
            file.write(live)
            file.write(acquiring_message)
 
        return True
 
    else:
        # if ping returns false
        not_live = "\nCONNECTION NOT ACQUIRED\n"
        print(not_live)
        #------------------------
        #--reconnecting using 4g routine--
        time.sleep(10)
        subprocess.call(["/usr/sbin/4g/4g.sh"])
        #------------------------
        with open(FILE, "a") as file:
           
            # writes into the log file
            file.write(not_live)
        return False
 

def main():
   
    # main function to call functions
    monitor_start_time = datetime.datetime.now()
    monitoring_date_time = "monitoring started at: " + \
        str(monitor_start_time).split(".")[0]
 
    if first_check():
        # if true
        print(monitoring_date_time)
        # monitoring will only start when
        # the connection will be acquired
 
    else:
        # if false
        while True:
           
            # infinite loop to see if the connection is acquired
            if not ping():
                 
                # if connection not acquired
                subprocess.call(["/usr/sbin/4g/4g.sh"])
                time.sleep(5)
            else:
                 
                # if connection is acquired
                first_check()
                print(monitoring_date_time)
                break
 
    with open(FILE, "a") as file:
       
        # write into the file as a into networkinfo.log,
        # "a" - append: opens file for appending,
        # creates the file if it does not exist???
        file.write("\n")
        file.write(monitoring_date_time + "\n")
 
    while True:
       
        # infinite loop, as we are monitoring
        # the network connection till the machine runs
        if ping():
             
            # if true: the loop will execute after every 5 seconds
            time.sleep(5)
 
        else:
            # if false: fail message will be displayed
            down_time = datetime.datetime.now()
            fail_msg = "disconnected at: " + str(down_time).split(".")[0]
            print(fail_msg)
 
            with open(FILE, "a") as file:
                # writes into the log file
                file.write(fail_msg + "\n")
 
            while not ping():

                #------------------------
                #--reconnecting using 4g routine--
                time.sleep(5)
                subprocess.call(["/usr/sbin/4g/4g_restart.sh"])
                #------------------------
                # infinite loop, will run till ping() return true
                time.sleep(1)
 
            up_time = datetime.datetime.now()
            # after loop breaks, connection restored
            uptime_message = "connected again: " + str(up_time).split(".")[0]
 
            down_time = calculate_time(down_time, up_time)
            unavailablity_time = "connection was unavailable for: " + down_time
 
            print(uptime_message)
            print(unavailablity_time)
 
            with open(FILE, "a") as file:
                 
                # log entry for connection restoration time,
                # and unavailability time
                file.write(uptime_message + "\n")
                file.write(unavailablity_time + "\n")
 
main()
