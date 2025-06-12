import csv
import re

DEFAULT_INTERNAL_EMAIL_PATTERN = r"magestore"

SUBSCRIPTION_CANCELED_STRINGS = ["Subscription charge canceled",\
                                 "Subscription charge frozen"]

SUBSCRIPTION_ACTIVATED_STRINGS = ["Subscription charge activated",\
                                  "Subscription charge unfrozen"]

ONE_TIME_ACTIVATED_STRINGS = ["Charge activated"]

INSTALLED_STRING = "Installed"
UNINSTALLED_STRING = "Uninstalled"
UNINSTALLED_OLD_STRING = "UninstalledOld"

ONE_TIME_STRING = "One-Time"

SUBSCRIPTION_STATUS_CANCELED = "Canceled"
SUBSCRIPTION_STATUS_ACTIVE = "Active"
SUBSCRIPTION_STATUS_NONE = "None"
SUBSCRIPTION_STATUS_CHANGED = "Changed"

SUBSCRIPTION_PLAN_NONE = "None"

KEY_FIELD = "Shop domain"
EVENT_FIELD = "Event"
DETAILS_FIELD = "Details"
TIME_FIELD = "Date"
EMAIL_FIELD = "Shop email"

DEFAULT_PAID_SUBSCRIPTIONS = [
    {"code":"standard",
     "name":"Standard",
     "reg_pattern":r"standard",
     "price":8.49,
     "currency": "USD"},

    {"code":"pro",
     "name":"Pro",
     "reg_pattern":r"pro",
     "price":27.99,
     "currency": "USD"},
]

DEFAULT_PAID_ONE_TIME = [
    {"code":"pack2k",
     "name":"2000 Labels",
     "reg_pattern":r"2000",
     "price":11.99,
     "currency": "USD"},

    {"code":"pack5k",
     "name":"5000 Labels",
     "reg_pattern":r"5000",
     "price":22.99,
     "currency": "USD"},

     {"code":"pack15k",
     "name":"15000 Labels",
     "reg_pattern":r"15000",
     "price":44.99,
     "currency": "USD"},
]

def count_from_csv(file_path,
                   subscriptions,
                   one_times,
                   excl_pattern = DEFAULT_INTERNAL_EMAIL_PATTERN,
                   excl_ref_field = EMAIL_FIELD,
                   merchant_key = KEY_FIELD):
    
    detailed_results = []

    installed_count = 0
    uninstalled_count = 0
    uninstalled_count_wo_installed = 0

    one_time_count = 0
    subscription_count = 0
    resubscription_count = 0
    subscription_canceled_count = 0

    with open(file_path, "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        data = list(reader)

        merchant_data = {}

        # Analyze & Count detailed data
        for idx, row in enumerate(reversed(data)):
            
            #Skip excluded records
            if re.search(excl_pattern, row[excl_ref_field]):
                continue

            merchant_data.setdefault(row[merchant_key], {
                "checked": False,
                "subscription_checked": False,
                "subscription_status": SUBSCRIPTION_STATUS_NONE,
                "subscription_plan": SUBSCRIPTION_PLAN_NONE,
                "installed_count": 0,
                "uninstalled_count": 0,
                "subscription_activated_count": 0,
                "subscription_canceled_count": 0,
                "one_time_count": 0,
            })

            merchant = merchant_data.get(row[merchant_key], None)
            
            #Count Install, Uninstall
            if (row[EVENT_FIELD] == INSTALLED_STRING):
                installed_count += 1
                merchant["installed_count"] += 1
            if (row[EVENT_FIELD] == UNINSTALLED_STRING):
                uninstalled_count += 1
                merchant["uninstalled_count"] += 1

            #Count Uninstalled without Installed
            if not merchant.get("checked", False): #Check if merchant not checked yet
                for i_idx, i_row in enumerate(data):
                    if (i_row[merchant_key] == row[merchant_key]):
                        merchant["checked"] = True

                        if (i_row[EVENT_FIELD] == UNINSTALLED_STRING):
                            uninstalled_count_wo_installed += 1

                        break

            #Check One-Time
            if (row[EVENT_FIELD] in ONE_TIME_ACTIVATED_STRINGS):
                one_time_count += 1
                merchant["one_time_count"] += 1

                for pack in one_times:
                    if (pack.get("count", "undefined") == "undefined"):
                        pack["count"] = 0
                    if merchant.get(pack["name"], 0) == 0:
                        merchant[pack["name"]] = 0
                    if re.search(pack["reg_pattern"], row[DETAILS_FIELD]):
                        pack["count"] += 1
                        merchant[pack["name"]] += 1
                        detailed_results.append({
                            merchant_key: row[merchant_key],
                            "paid_type": "One-Time",
                            "detail": pack["name"]})
                        break
                
                continue

            #Check Subscription
            sub_checked = merchant.get("subscription_checked", False) if merchant else False
            if sub_checked:
                continue

            if (row[EVENT_FIELD] in SUBSCRIPTION_CANCELED_STRINGS):
                merchant["subscription_canceled_count"] += 1
                merchant_data.setdefault(row[merchant_key], {})["subscription_checked"] = True
                merchant_data[row[merchant_key]]["subscription_status"] = SUBSCRIPTION_STATUS_CANCELED

                # Shopify Mechanism: REVERSE last 2 subscription activated/canceled events with the same event time
                # For the same merchant,
                # if there is a subscription activated event right before the canceled event with the same time,
                # that mean this is ACTIVATED, NOT CANCELED 
                # => Mark this canceling is not counted, for preventing wrong counting
                #    Also, Re-Mark the merchant as NOT Checked, for counting as activated in the next iteration
                for i_idx, i_row in enumerate(reversed(data)):
                    if (i_row[merchant_key] == row[merchant_key]):
                        if (i_idx <= idx):
                            continue
                        if (i_row[TIME_FIELD] != row[TIME_FIELD]):
                            break
                        
                        if (i_row[EVENT_FIELD] in SUBSCRIPTION_ACTIVATED_STRINGS):
                            merchant_data[row[merchant_key]]["subscription_status"] = SUBSCRIPTION_STATUS_NONE
                            merchant_data[row[merchant_key]]["subscription_checked"] = False
                            break

                if merchant_data[row[merchant_key]]["subscription_status"] != SUBSCRIPTION_STATUS_CANCELED:
                    continue
                
                subscription_canceled_count += 1

                for plan in subscriptions:
                    if (plan.get("canceled_count", "undefined") == "undefined"):
                        plan["canceled_count"] = 0
                    if re.search(plan["reg_pattern"], row[DETAILS_FIELD]):
                        merchant_data[row[merchant_key]]["subscription_plan"] = plan["name"]
                        plan["canceled_count"] += 1
                        detailed_results.append({
                            merchant_key: row[merchant_key],
                            "paid_type": "Subscription Canceled",
                            "detail": plan["name"]})
                        
                        break
            
            if (row[EVENT_FIELD] in SUBSCRIPTION_ACTIVATED_STRINGS):
                merchant["subscription_activated_count"] += 1
                merchant_data.setdefault(row[merchant_key], {})["subscription_checked"] = True
                merchant_data[row[merchant_key]]["subscription_status"] = SUBSCRIPTION_STATUS_ACTIVE

                # Shopify Mechanism: REVERSE last 2 subscription activated/canceled events with the same event time
                # For the same merchant,
                # if there is a subscription canceled event right before the activated event with the same time,
                # that mean this is CANCELED, NOT ACTIVATED
                # => Mark this activation is not counted, for preventing wrong counting
                #    Also, Re-Mark the merchant as NOT Checked, for counting as canceled in the next iteration
                for i_idx, i_row in enumerate(reversed(data)):
                    if (i_row[merchant_key] == row[merchant_key]):
                        if (i_idx <= idx):
                            continue
                        if (i_row[TIME_FIELD] != row[TIME_FIELD]):
                            break
                        if (i_row[EVENT_FIELD] in SUBSCRIPTION_CANCELED_STRINGS):
                            merchant_data[row[merchant_key]]["subscription_status"] = SUBSCRIPTION_STATUS_NONE
                            merchant_data[row[merchant_key]]["subscription_checked"] = False
                            break

                if merchant_data[row[merchant_key]]["subscription_status"] != SUBSCRIPTION_STATUS_ACTIVE:
                    continue

                subscription_count += 1
                
                for plan in subscriptions:
                    if (plan.get("count", "undefined") == "undefined"):
                        plan["count"] = 0
                    if re.search(plan["reg_pattern"], row[DETAILS_FIELD]):
                        merchant_data[row[merchant_key]]["subscription_plan"] = plan["name"]
                        plan["count"] += 1
                        detailed_results.append({
                            merchant_key: row[merchant_key],
                            "paid_type": "Subscription",
                            "detail": plan["name"]})
                        
                        break

                continue
        
        # Check real subscription status
        for merchant in merchant_data.values():
            
            # Check plan changed
            if (merchant["subscription_status"] == SUBSCRIPTION_STATUS_ACTIVE and
                merchant["subscription_activated_count"] == merchant["subscription_canceled_count"]):
                resubscription_count += 1
                merchant["subscription_status"] = SUBSCRIPTION_STATUS_CHANGED

                for plan in subscriptions:
                    if (plan.get("changed_count", "undefined") == "undefined"):
                        plan["changed_count"] = 0
                    if plan["name"] == merchant["subscription_plan"]:
                        plan["changed_count"] += 1
                        break
            
            # Remove wrong canceled count
            if (merchant["subscription_status"] == SUBSCRIPTION_STATUS_CANCELED and
                merchant["subscription_activated_count"] == merchant["subscription_canceled_count"]):
                subscription_canceled_count -= 1
                merchant["subscription_status"] = SUBSCRIPTION_STATUS_NONE

                for plan in subscriptions:
                    if (plan.get("canceled_count", "undefined") == "undefined"):
                        plan["canceled_count"] = 0
                    if plan["name"] == merchant["subscription_plan"]:
                        plan["canceled_count"] -= 1
                        break
            
            
    
    count_result = {
        INSTALLED_STRING: installed_count,
        UNINSTALLED_STRING: uninstalled_count,
        UNINSTALLED_OLD_STRING: uninstalled_count_wo_installed,
        ONE_TIME_STRING: one_time_count,
        SUBSCRIPTION_STATUS_ACTIVE: subscription_count,
        SUBSCRIPTION_STATUS_CANCELED: subscription_canceled_count,
        SUBSCRIPTION_STATUS_CHANGED: resubscription_count
    }
    
    return count_result, subscriptions, one_times, detailed_results

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python count_legacy.py <path_to_csv_file> [--debug]")
        sys.exit(1)

    print("Running Default: Count for Magestore Barcode App")
    print("--------------------------------------------------")
    
    # Get file path from argument
    file_path = sys.argv[1]
    print("Input File: ", file_path)
    print("--------------------------------------------------")

    # Load default definitions
    subscriptions = DEFAULT_PAID_SUBSCRIPTIONS
    one_times = DEFAULT_PAID_ONE_TIME
    excl_pattern = DEFAULT_INTERNAL_EMAIL_PATTERN
    excl_ref_field = EMAIL_FIELD
    merchant_key = KEY_FIELD
    count_result, subscriptions, one_times, detailed_results = count_from_csv(
        file_path, subscriptions, one_times, excl_pattern, excl_ref_field, merchant_key)
    
    one_time_count_check = 0
    subscriptions_count_check = 0
    subscriptions_canceled_count_check = 0
    subscriptions_changed_count_check = 0

    #Print results
    print("SUMMARIZE RESULTS")
    print("Installed: ", count_result[INSTALLED_STRING])
    print("Uninstalled ", count_result[UNINSTALLED_STRING])
    print("Churn Rate: ", count_result[UNINSTALLED_STRING]/count_result[INSTALLED_STRING] * 100)
    print("Uninstalled without Installed: ", count_result[UNINSTALLED_OLD_STRING])

    print("\nTotal Paid Count:", count_result[SUBSCRIPTION_STATUS_ACTIVE] + count_result[ONE_TIME_STRING])  
    
    print("    Subscription Count: ", count_result[SUBSCRIPTION_STATUS_ACTIVE])
    for sub in subscriptions:
        subscriptions_count_check += sub.get('count', 0)
        print(f"        {sub['name']}: {sub.get('count', 0)}")
    
    print("    Subscription Canceled Count: ", count_result[SUBSCRIPTION_STATUS_CANCELED])
    for sub in subscriptions:
        subscriptions_canceled_count_check += sub.get('canceled_count', 0)
        print(f"        {sub['name']}: {sub.get('canceled_count', 0)}")

    print("    Subscription Changed Count: ", count_result[SUBSCRIPTION_STATUS_CHANGED])
    for sub in subscriptions:
        subscriptions_changed_count_check += sub.get('changed_count', 0)
        print(f"        {sub['name']}: {sub.get('changed_count', 0)}")
    
    print("    One-Time Count: ", count_result[ONE_TIME_STRING])
    for one_time in one_times:
        one_time_count_check += one_time.get('count', 0)
        print(f"        {one_time['name']}: {one_time.get('count', 0)}")

    print("--------------------------------------------------")

    #Check if counts match
    if (count_result[ONE_TIME_STRING] != one_time_count_check):
        print("Error detected: One-Time Count is not equal total of Packages Counts")
        print("---------------------------------------------------")

    if (count_result[SUBSCRIPTION_STATUS_ACTIVE] != subscriptions_count_check):
        print("Error detected: Subscription Count is not equal total of Plans Counts")
        print("---------------------------------------------------")

    if (count_result[SUBSCRIPTION_STATUS_CANCELED] != subscriptions_canceled_count_check):
        print("Error detected: Subscription Canceled Count is not equal total of Plans Canceled Counts")
        print("---------------------------------------------------")

    if (count_result[SUBSCRIPTION_STATUS_CHANGED] != subscriptions_changed_count_check):
        print("Error detected: Subscription Changed Count is not equal total of Plans Changed Counts")
        print("---------------------------------------------------")

    # Print detailed results
    if len(sys.argv) > 2 and sys.argv[2] == "--debug":
        print("DETAILED RESULTS")
        for detail in detailed_results:
            print(f"{detail[merchant_key]} - {detail['paid_type']}: {detail['detail']}")
        print("--------------------------------------------------")
