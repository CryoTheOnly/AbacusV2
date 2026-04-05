import os
import requests
import json
import datetime
import time
import re
import threading
from dotenv import load_dotenv




load_dotenv("keys/.env")
MIAMI_API = '22283eed1be64d4488c181217260302'
HOME_API="place"
Date = datetime.date.today()
Date = str(Date)
#change to make military time
Mt = False



def get_time():
    while True:
        now = datetime.datetime.now()
        ampm = now.strftime("%p")
        Human_Time = now.strftime("%H:%M")
        Human_Time_Min = now.strftime("%M")
        Human_Time_Hour = now.strftime("%H")
        if Mt == True:
            print(Human_Time + " Time in Miami.")
            # calculate remaining seconds until next minute, minus 5s buffer
            left = 60 - now.second - 5 - (now.microsecond / 1_000_000)
            time.sleep(left)
            # extra 5-second stop so it doesn’t run forever instantly
            time.sleep(5)
        elif Mt == False:
            left = 60 - now.second - 5 - (now.microsecond / 1_000_000)
            hour = int(Human_Time_Hour)
            if hour == 0:
                hour = 12
            elif hour > 12:
                hour -= 12
            Minute = str(Human_Time_Min)
            hour = str(hour)
            Human_Time_Hour = str(hour+ ":"+Minute + " " + ampm)
            print(Human_Time_Hour)
            time.sleep(left)
            time.sleep(5)
threading.Thread(target=get_time, daemon=True).start()

while True:

    MiamiUrl = "https://api.weatherapi.com/v1/current.json"
    Miami_params = {
        "key": MIAMI_API,
        "q": "Miami",
        "aqi": "no"
    }

    response = requests.get(MiamiUrl, params=Miami_params)
    data = response.json()

    def feels_like_M():
        FF = "feelslike_f"
        match = re.search(rf"\b{FF}\b\W*([A-Za-z0-9_]+)", str(data), re.IGNORECASE)
        if match:
            MiamiTempature = str(match.group(1))
            print(MiamiTempature + " Miami")

        else:
            print("No match found.")
            Time = datetime.datetime.now().strftime("%H:%M:%S")
            log_file = "data/errors/"+Date+".log"
            print("Error! SHUTTING DOWN")
            if os.path.exists(log_file):
                with open(log_file, "a+") as file:
                    file.write("\n"+Time+"eror for weather fix ts gng")
           
            else:
                Time = datetime.datetime.now().strftime("%H:%M:%S")
                log_file = "data/errors/"+Date+".log"
                print("Error! SHUTTING DOWN")
                if os.path.exists(log_file):
                    with open(log_file, "w") as file:
                        file.write("\n"+Time+"----WEATHER ERROR----")            
        time.sleep(120)


        
    feels_like_M()    