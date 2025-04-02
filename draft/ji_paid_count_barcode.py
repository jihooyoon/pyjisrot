import sys
import csv
import re

#Check argument
if len(sys.argv) < 2:
    print("Usage: python <script_file.py> <input_file.csv>")
    sys.exit()

#Get file path from argument
file_path = sys.argv[1]
print("Input File: ", file_path)

#defined
subscriptionCancelingEvents = ["Subscription charge canceled",\
                                "Subscription charge frozen"]

subscriptionActivatingEvents = ["Subscription charge activated",\
                                "Subscription charge unfrozen"]

oneTimeActivatingEvents = ["Charge activated"]

excludeEmailPattern = r"magestore"

standardPattern = r"standard"
proPattern = r"pro"
pack2kPattern = r"2000"
pack5kPattern = r"5000"
pack15kPattern = r"15000"

#init
subscriptionChecked = {}
paidCount = 0
oneTimeCount = 0
subscriptionCount = 0
proCount = 0
standardCount = 0
pack2kCount = 0
pack5kCount = 0
pack15kCount = 0

installedCount = 0
uninstalledCount = 0
uninstalledCountWOInstalled = 0
oldDomainChecked = {}

with open(file_path,"r", newline="", encoding="utf-8") as file:
    reader = csv.DictReader(file)
    data = list(reader)

    for idx, row in enumerate(reversed(data)):     
        if re.search(excludeEmailPattern, row["Shop email"]):
            continue

        #Count Install, Uninstall
        if (row["Event"] == "Installed"):
            installedCount += 1
        if (row["Event"] == "Uninstalled"):
            uninstalledCount += 1
        
        if not(oldDomainChecked.get(row["Shop domain"], False)):
            for iIdx, iRow in enumerate(data):
                if (iRow["Shop domain"] == row["Shop domain"]):
                    oldDomainChecked[iRow["Shop domain"]] = True
                    
                    if (iRow["Event"] == "Uninstalled"):
                        uninstalledCountWOInstalled += 1
                    
                    break



        #Check One-Time
        if (row["Event"] in oneTimeActivatingEvents):
            print(row["Shop domain"] + "    One-Time")
            oneTimeCount += 1
            if re.search(pack2kPattern, row["Details"]):
                pack2kCount += 1
                continue
            if re.search(pack5kPattern, row["Details"]):
                pack5kCount += 1
                continue
            if re.search(pack15kPattern, row["Details"]):
                pack15kCount += 1
                continue
        
        if subscriptionChecked.get(row["Shop domain"], False):
            continue
        
        #Check Subscription
        if (row["Event"] in subscriptionCancelingEvents):
            subscriptionChecked[row["Shop domain"]] = True

            for iIdx, iRow in enumerate(reversed(data)):
                if (iRow["Shop domain"] == row["Shop domain"]):
                    if (iIdx <= idx):
                        continue
                    if (iRow["Date"] != row["Date"]):
                        break
                    if (iRow["Event"] in subscriptionActivatingEvents):
                        subscriptionChecked[row["Shop domain"]] = False
                        break
            continue
        
        if (row["Event"] in subscriptionActivatingEvents):
            subscriptionChecked[row["Shop domain"]] = True
            count = True
            
            for iIdx, iRow in enumerate(reversed(data)):
                if (iRow["Shop domain"] == row["Shop domain"]):
                    if (iIdx <= idx):
                        continue
                    if (iRow["Date"] != row["Date"]):
                        break
                    if (iRow["Event"] in subscriptionCancelingEvents):
                        count = False
                        break

            if not(count):
                continue
            print(row["Shop domain"] + "    Subscription" + " - " + row["Details"])
            subscriptionCount += 1
            if re.search(standardPattern, row["Details"]):
                standardCount += 1
                continue
            if re.search(proPattern, row["Details"]):
                proCount += 1
                continue

#Print Detailed Result
print("\nInstalled: ", installedCount)
print("Uninstalled ", uninstalledCount)
print("Churn Rate: ", uninstalledCount/installedCount * 100)
print("Uninstalled without Installed: ", uninstalledCountWOInstalled)

totalPaidCount = subscriptionCount + oneTimeCount
print("\nTotal Paid Count:", totalPaidCount)
print("    Subscription Count: ", subscriptionCount)
print("        Standard: ", standardCount)
print("        Pro: ", proCount)
print("    One-Time Count: ", oneTimeCount)
print("        2k: ", pack2kCount)
print("        5k: ", pack5kCount)
print("        15k: ", pack15kCount)

#Print Error
if (oneTimeCount != pack15kCount + pack5kCount + pack2kCount):
    print("\nError detected: One-Time Count is not equal total of Packages Counts")

if (subscriptionCount != proCount + standardCount):
    print("\nError detected: Subscription Count is not equal total of Plan Counts")