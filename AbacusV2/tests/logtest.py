import os
from datetime import datetime

file_to_check = "activitytest.log"

if os.path.exists("Data/logs/"+file_to_check):
    print("Test complete")
else:
    print("test failed stupid")

#Note-----it works