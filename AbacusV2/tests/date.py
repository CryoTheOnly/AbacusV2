import date
import datetime
from datetime import date
import threading
import os
import time

user_msg = input("Test:")

def logger():
    Time = datetime.datetime.now().strftime("%H:%M:%S")
    Date = datetime.date.today()
    Date = str(Date)
    log_file = "data/logs/"+Date+".log"
    if os.path.exists(log_file):
        if os.path.exists(log_file):
            def log_message():
                with open(log_file, "a+") as file:
                    file.write("\n"+Time+"----"+user_msg)
            threading.Thread(target=log_message).start()
        else:
            def log_message_create():
                with open(log_file, "w") as file:
                    file.write("File created at----"+Time+"----"+user_msg)
            threading.Thread(target=log_message_create).start()
        time.sleep(2)

logger()