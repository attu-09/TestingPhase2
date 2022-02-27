import datetime as dt
import time as t
import subprocess
import random
i=0
while i<100:
	p = subprocess.Popen("TH.sh", stdout=subprocess.PIPE, shell=True)
	time = str(dt.datetime.now())
	(output, err) = p.communicate()
	L = random.randint(400,600)
	lux = " , Light Intensity : "+str(L)
	p_status = p.wait()
	#print("Command output : ", output)
	#print("Command exit status/return code : ", p_status)
	file = open("weather.txt", "a")
	file.writelines("\n"+time+" , "+", ".join(str(output)[2:len(output)-1].split("\\n"))+lux+"\n")
	file.close()
	i+=1
	t.sleep(10)
