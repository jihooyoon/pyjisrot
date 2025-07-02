import csv
import re
from definitions import msdef
from definitions import common
from definitions import sbmdef


# Function to build merchant data from CSV file
def init_merchant_data_and_basic_count(event_csv_file_path,
                        one_time_packages,
                        excl_pattern = msdef.DEFAULT_INTERNAL_EMAIL_PATTERN,
                        excl_ref_field = common.EMAIL_FIELD,
                        merchant_key = common.KEY_FIELD):
    
    with open(event_csv_file_path, "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        raw_data = list(reader)
        
    #Setup total data structure
    total_data = {
        "start_time": 0,
        "end_time": 0,
        "installed_count": 0,
        "uninstalled_count": 0,
        "store_closed_count": 0,
        "store_reopened_count": 0,
        "one_time_count": 0,
        "one_time_details": {},
    }

    # Get time range data
    if raw_data:
        total_data["start_time"] = raw_data[0].get(common.TIME_FIELD, 0)
        total_data["end_time"] = raw_data[-1].get(common.TIME_FIELD, 0)

    # Init merchant data
    merchant_data = {}
    
    for row in raw_data:
        # Skip excluded records
        if re.search(excl_pattern, row[excl_ref_field]):
            continue

        #Setup merchant data structure
        merchant_data.setdefault(row[merchant_key], {
            "checked": False,
            
            "installed_count": 0,
            "uninstalled_count": 0,
            "store_closed_count": 0,
            "store_reopened_count": 0,
            "installing_events": [],
            
            "subscription_activated_count": 0,
            "subscription_canceled_count": 0,
            "subscription_events": [],
            
            "one_time_count": 0,
            "one_time_details": {},
            "one_time_events": [],
        })

        current_merchant = merchant_data[row[merchant_key]]

        # Count Install, Uninstall, Store Closed
        if re.search(common.INSTALLED_STRING, row[common.EVENT_FIELD]):
            total_data["installed_count"] += 1
            current_merchant["installed_count"] += 1
            current_merchant["installing_events"].append(row)
            continue
        
        if re.search(common.UNINSTALLED_STRING, row[common.EVENT_FIELD]):
            total_data["uninstalled_count"] += 1
            current_merchant["uninstalled_count"] += 1
            current_merchant["installing_events"].append(row)
            continue

        if re.search(common.STORE_CLOSED_STRING, row[common.EVENT_FIELD]):
            total_data["store_closed_count"] += 1
            current_merchant["store_closed_count"] += 1
            current_merchant["installing_events"].append(row)
            continue

        if re.search(common.STORE_REOPENED_STRING, row[common.EVENT_FIELD]):
            total_data["store_reopened_count"] += 1
            current_merchant["store_reopened_count"] += 1
            current_merchant["installing_events"].append(row)
            continue

        # Count One-Time
        if (row[common.EVENT_FIELD] in common.ONE_TIME_ACTIVATED_STRINGS):
            
            total_data["one_time_count"] += 1
            current_merchant["one_time_count"] += 1
            current_merchant["one_time_events"].append(row)

            for pack in one_time_packages:
                # Init detailed package count in total if not set
                pack.setdefault("count", 0)
                
                # Init detailed package count for current merchant if not set
                current_merchant["one_time_details"].setdefault(pack["name"], 0)
                
                if re.search(pack["reg_pattern"], row[common.DETAILS_FIELD]):
                    pack["count"] += 1
                    current_merchant["one_time_details"][pack["name"]] += 1
                    break

            continue
        
        # Count Subscription
        if (row[common.EVENT_FIELD] in common.SUBSCRIPTION_ACTIVATED_STRINGS):
            current_merchant["subscription_activated_count"] += 1
            current_merchant["subscription_events"].append(row)
            continue
        
        if (row[common.EVENT_FIELD] in common.SUBSCRIPTION_CANCELED_STRINGS):
            current_merchant["subscription_canceled_count"] += 1
            current_merchant["subscription_events"].append(row)
            continue

    
    # Store total One-Time data
    for pack in one_time_packages:
        total_data["one_time_details"].setdefault(pack["name"], 0)
        total_data["one_time_details"][pack["name"]] = pack.get("count", 0)
    
    return total_data, merchant_data


def process_data_and_final_count(total_data, merchant_data, subscriptions):
    """
    This function updates the merchant data with the final status 
    and update the total data with the final counting results.
    """
    # Calculate final counts for total data
    total_data["merchant_growth"] = total_data["installed_count"] + total_data["store_reopened_count"]\
        - total_data["uninstalled_count"] - total_data["store_closed_count"]
    total_data["total_churn_rate"] = (total_data["uninstalled_count"] / total_data["installed_count"]) * 100\
        if total_data["installed_count"] > 0 else 0

    # Init old uninstalled count
    total_data.setdefault("old_uninstalled_count", 0)

    # Init subscription counting results of total data
    total_data.setdefault("new_sub_count", 0)
    total_data.setdefault("canceled_sub_count", 0)

    # Process merchant data
    for merchant in merchant_data.values():

        # Update installed status
        t_installed_count = merchant["installed_count"] + merchant["store_reopened_count"]
        t_uninstalled_count = merchant["uninstalled_count"] + merchant["store_closed_count"]
        
        if (t_installed_count > t_uninstalled_count):
            merchant["installed_status"] = common.INSTALLED_STRING
        elif (t_installed_count < t_uninstalled_count):
            merchant["installed_status"] = common.UNINSTALLED_STRING
            # Determine if this is old merchant
            if merchant["installing_events"]\
                and merchant["installing_events"][0][common.EVENT_FIELD] == common.UNINSTALLED_STRING:
                    merchant["installed_status"] = common.UNINSTALLED_OLD_STRING
                    total_data["old_uninstalled_count"] += 1
        else:
            merchant["installed_status"] = common.NONE
        
        # Determine the final subscription status
        if (merchant["subscription_activated_count"] > merchant["subscription_canceled_count"]):
            merchant["subscription_status"] = common.SUBSCRIPTION_STATUS_ACTIVE
            total_data["new_sub_count"] += 1
        elif (merchant["subscription_activated_count"] < merchant["subscription_canceled_count"]):
            merchant["subscription_status"] = common.SUBSCRIPTION_STATUS_CANCELED
            total_data["canceled_sub_count"] += 1
        else:
            merchant["subscription_status"] = common.NONE
    
    # Update final total data
    total_data["churn_rate"] = ((total_data["uninstalled_count"] - total_data["old_uninstalled_count"]) / total_data["installed_count"]) * 100\
        if total_data["installed_count"] > 0 else 0
    total_data["sub_growth"] = total_data["new_sub_count"] - total_data["canceled_sub_count"]
    total_data["paid_growth"] = total_data["sub_growth"] + total_data["one_time_count"]

    return total_data, merchant_data


def count_from_csv(file_path,
                   subscriptions,
                   one_times,
                   excl_pattern = msdef.DEFAULT_INTERNAL_EMAIL_PATTERN,
                   excl_ref_field = common.EMAIL_FIELD,
                   merchant_key = common.KEY_FIELD):
    
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
                "subscription_status": common.SUBSCRIPTION_STATUS_NONE,
                "subscription_plan": common.SUBSCRIPTION_PLAN_NONE,
                "installed_count": 0,
                "uninstalled_count": 0,
                "subscription_activated_count": 0,
                "subscription_canceled_count": 0,
                "one_time_count": 0,
            })

            merchant = merchant_data.get(row[merchant_key], None)
            
            #Count Install, Uninstall
            if (row[common.EVENT_FIELD] == common.INSTALLED_STRING):
                installed_count += 1
                merchant["installed_count"] += 1
            if (row[common.EVENT_FIELD] == common.UNINSTALLED_STRING):
                uninstalled_count += 1
                merchant["uninstalled_count"] += 1

            #Count Uninstalled without Installed
            if not merchant.get("checked", False): #Check if merchant not checked yet
                for i_idx, i_row in enumerate(data):
                    if (i_row[merchant_key] == row[merchant_key]):
                        merchant["checked"] = True

                        if (i_row[common.EVENT_FIELD] == common.UNINSTALLED_STRING):
                            uninstalled_count_wo_installed += 1

                        break

            #Check One-Time
            if (row[common.EVENT_FIELD] in common.ONE_TIME_ACTIVATED_STRINGS):
                one_time_count += 1
                merchant["one_time_count"] += 1

                for pack in one_times:
                    if (pack.get("count", "undefined") == "undefined"):
                        pack["count"] = 0
                    if merchant.get(pack["name"], 0) == 0:
                        merchant[pack["name"]] = 0
                    if re.search(pack["reg_pattern"], row[common.DETAILS_FIELD]):
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

            if (row[common.EVENT_FIELD] in common.SUBSCRIPTION_CANCELED_STRINGS):
                merchant["subscription_canceled_count"] += 1
                merchant_data.setdefault(row[merchant_key], {})["subscription_checked"] = True
                merchant_data[row[merchant_key]]["subscription_status"] = common.SUBSCRIPTION_STATUS_CANCELED

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
                        if (i_row[common.TIME_FIELD] != row[common.TIME_FIELD]):
                            break
                        
                        if (i_row[common.EVENT_FIELD] in common.SUBSCRIPTION_ACTIVATED_STRINGS):
                            merchant_data[row[merchant_key]]["subscription_status"] = common.SUBSCRIPTION_STATUS_NONE
                            merchant_data[row[merchant_key]]["subscription_checked"] = False
                            break

                if merchant_data[row[merchant_key]]["subscription_status"] != common.SUBSCRIPTION_STATUS_CANCELED:
                    continue
                
                subscription_canceled_count += 1

                for plan in subscriptions:
                    if (plan.get("canceled_count", "undefined") == "undefined"):
                        plan["canceled_count"] = 0
                    if re.search(plan["reg_pattern"], row[common.DETAILS_FIELD]):
                        merchant_data[row[merchant_key]]["subscription_plan"] = plan["name"]
                        plan["canceled_count"] += 1
                        detailed_results.append({
                            merchant_key: row[merchant_key],
                            "paid_type": "Subscription Canceled",
                            "detail": plan["name"]})
                        
                        break
            
            if (row[common.EVENT_FIELD] in common.SUBSCRIPTION_ACTIVATED_STRINGS):
                merchant["subscription_activated_count"] += 1
                merchant_data.setdefault(row[merchant_key], {})["subscription_checked"] = True
                merchant_data[row[merchant_key]]["subscription_status"] = common.SUBSCRIPTION_STATUS_ACTIVE

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
                        if (i_row[common.TIME_FIELD] != row[common.TIME_FIELD]):
                            break
                        if (i_row[common.EVENT_FIELD] in common.SUBSCRIPTION_CANCELED_STRINGS):
                            merchant_data[row[merchant_key]]["subscription_status"] = common.SUBSCRIPTION_STATUS_NONE
                            merchant_data[row[merchant_key]]["subscription_checked"] = False
                            break

                if merchant_data[row[merchant_key]]["subscription_status"] != common.SUBSCRIPTION_STATUS_ACTIVE:
                    continue

                subscription_count += 1
                
                for plan in subscriptions:
                    if (plan.get("count", "undefined") == "undefined"):
                        plan["count"] = 0
                    if re.search(plan["reg_pattern"], row[common.DETAILS_FIELD]):
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
            if (merchant["subscription_status"] == common.SUBSCRIPTION_STATUS_ACTIVE and
                merchant["subscription_activated_count"] == merchant["subscription_canceled_count"]):
                resubscription_count += 1
                merchant["subscription_status"] = common.SUBSCRIPTION_STATUS_CHANGED

                for plan in subscriptions:
                    if (plan.get("changed_count", "undefined") == "undefined"):
                        plan["changed_count"] = 0
                    if plan["name"] == merchant["subscription_plan"]:
                        plan["changed_count"] += 1
                        break
            
            # Remove wrong canceled count
            if (merchant["subscription_status"] == common.SUBSCRIPTION_STATUS_CANCELED and
                merchant["subscription_activated_count"] == merchant["subscription_canceled_count"]):
                subscription_canceled_count -= 1
                merchant["subscription_status"] = common.SUBSCRIPTION_STATUS_NONE

                for plan in subscriptions:
                    if (plan.get("canceled_count", "undefined") == "undefined"):
                        plan["canceled_count"] = 0
                    if plan["name"] == merchant["subscription_plan"]:
                        plan["canceled_count"] -= 1
                        break
    
    count_result = {
        common.INSTALLED_STRING: installed_count,
        common.UNINSTALLED_STRING: uninstalled_count,
        common.UNINSTALLED_OLD_STRING: uninstalled_count_wo_installed,
        common.ONE_TIME_STRING: one_time_count,
        common.SUBSCRIPTION_STATUS_ACTIVE: subscription_count,
        common.SUBSCRIPTION_STATUS_CANCELED: subscription_canceled_count,
        common.SUBSCRIPTION_STATUS_CHANGED: resubscription_count
    }
    
    return count_result, subscriptions, one_times, detailed_results

def count_all_stats(file_path, price_definitions = sbmdef, excluding_definitions = msdef, log = False):
    """
    Count statistics from one event history CSV file.\n
    Return total data and merchant data.
    """
    total_data, merchant_data = init_merchant_data_and_basic_count(file_path,
                                                                   price_definitions.ONE_TIMES_PACKAGES,
                                                                   excl_pattern = excluding_definitions.EXCLUDING_PATTERN,
                                                                   excl_ref_field = excluding_definitions.EXCLUDING_FIELD)
    if log:
        print("Initialized merchant data and counted basic statistics.")
    
    total_data, merchant_data = process_data_and_final_count(total_data, merchant_data, price_definitions.SUBSCRIPTION_PLANS)
    if log:
        print("Processed data and finalized counts.")

    merchant_data = {
        "start_time": total_data["start_time"],
        "end_time": total_data["end_time"],
        **merchant_data
    }

    return total_data, merchant_data


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python count_legacy.py <path_to_csv_file> [--debug]")
        sys.exit(1)

    if len(sys.argv) > 2 and sys.argv[2] == "--dev":
        from definitions import sbmdef
        import json, os
        
        total_data, merchant_data = init_merchant_data_and_basic_count(sys.argv[1], sbmdef.ONE_TIMES_PACKAGES)
        print("Development mode: Initialized merchant data and counted basic statistics.")
        
        total_data, merchant_data = process_data_and_final_count(total_data, merchant_data, sbmdef.SUBSCRIPTION_PLANS)
        print("Development mode: Processed data and finalized counts.")
        
        merchant_data = {
            "start_time": total_data["start_time"],
            "end_time": total_data["end_time"],
            **merchant_data
        }

        try:
            os.mkdir("dev_out")
            print("Directory 'dev_out' created successfully.")
        except FileExistsError:
            print("Directory 'dev_out' already exists.")
        except OSError as e:
            print(f"Error creating directory: {e}")

        with open("dev_out/out_total_data.json", 'w', encoding='utf-8') as fo:
            json.dump(total_data, fo, ensure_ascii=False, indent=4)
            print("Total Data written to dev_out/out_total_data.json")
       
        with open("dev_out/out_merchant_data.json", 'w', encoding='utf-8') as fo:
            json.dump(merchant_data, fo, ensure_ascii=False, indent=4)
            print("Merchant Data written to dev_out/out_merchant_data.json")
        
        sys.exit(0)

    print("Running Default: Count for Magestore Barcode App")
    print("--------------------------------------------------")
    
    # Get file path from argument
    file_path = sys.argv[1]
    print("Input File: ", file_path)
    print("--------------------------------------------------")

    # Import definitions
    import definitions.sbmdef as appdef

    subscriptions = appdef.SUBSCRIPTION_PLANS
    one_times = appdef.ONE_TIMES_PACKAGES
    excl_pattern = msdef.DEFAULT_INTERNAL_EMAIL_PATTERN
    excl_ref_field = common.EMAIL_FIELD
    merchant_key = common.KEY_FIELD
    count_result, subscriptions, one_times, detailed_results = count_from_csv(
        file_path, subscriptions, one_times, excl_pattern, excl_ref_field, merchant_key)
    
    one_time_count_check = 0
    subscriptions_count_check = 0
    subscriptions_canceled_count_check = 0
    subscriptions_changed_count_check = 0

    #Print results
    print("SUMMARIZE RESULTS\n")
    print("Installed: ", count_result[common.INSTALLED_STRING])
    print("Uninstalled ", count_result[common.UNINSTALLED_STRING])
    print("Churn Rate: ", count_result[common.UNINSTALLED_STRING]/count_result[common.INSTALLED_STRING] * 100)
    print("Uninstalled without Installed: ", count_result[common.UNINSTALLED_OLD_STRING])

    print("\nTotal Paid Count:", count_result[common.SUBSCRIPTION_STATUS_ACTIVE] + count_result[common.ONE_TIME_STRING])  
    
    print()
    print("    Subscription Count: ", count_result[common.SUBSCRIPTION_STATUS_ACTIVE])
    for sub in subscriptions:
        subscriptions_count_check += sub.get('count', 0)
        print(f"        {sub['name']}: {sub.get('count', 0)}")
    
    print("    Subscription Canceled Count: ", count_result[common.SUBSCRIPTION_STATUS_CANCELED])
    for sub in subscriptions:
        subscriptions_canceled_count_check += sub.get('canceled_count', 0)
        print(f"        {sub['name']}: {sub.get('canceled_count', 0)}")

    print("    Subscription Changed Count: ", count_result[common.SUBSCRIPTION_STATUS_CHANGED])
    for sub in subscriptions:
        subscriptions_changed_count_check += sub.get('changed_count', 0)
        print(f"        {sub['name']}: {sub.get('changed_count', 0)}")
    
    print()
    print("    New Subscriptions: ", count_result[common.SUBSCRIPTION_STATUS_ACTIVE] - count_result[common.SUBSCRIPTION_STATUS_CHANGED])
    print()
    
    print("    One-Time Count: ", count_result[common.ONE_TIME_STRING])
    for one_time in one_times:
        one_time_count_check += one_time.get('count', 0)
        print(f"        {one_time['name']}: {one_time.get('count', 0)}")

    print()
    print("    Paid Growth:", count_result[common.SUBSCRIPTION_STATUS_ACTIVE] + count_result[common.ONE_TIME_STRING]
            - count_result[common.SUBSCRIPTION_STATUS_CANCELED] - count_result[common.SUBSCRIPTION_STATUS_CHANGED])
    
    print("--------------------------------------------------")

    #Check if counts match
    if (count_result[common.ONE_TIME_STRING] != one_time_count_check):
        print("Error detected: One-Time Count is not equal total of Packages Counts")
        print("---------------------------------------------------")

    if (count_result[common.SUBSCRIPTION_STATUS_ACTIVE] != subscriptions_count_check):
        print("Error detected: Subscription Count is not equal total of Plans Counts")
        print("---------------------------------------------------")

    if (count_result[common.SUBSCRIPTION_STATUS_CANCELED] != subscriptions_canceled_count_check):
        print("Error detected: Subscription Canceled Count is not equal total of Plans Canceled Counts")
        print("---------------------------------------------------")

    if (count_result[common.SUBSCRIPTION_STATUS_CHANGED] != subscriptions_changed_count_check):
        print("Error detected: Subscription Changed Count is not equal total of Plans Changed Counts")
        print("---------------------------------------------------")

    # Print detailed results
    if len(sys.argv) > 2 and sys.argv[2] == "--debug":
        print("DETAILED RESULTS")
        for detail in detailed_results:
            print(f"{detail[merchant_key]} - {detail['paid_type']}: {detail['detail']}")
        print("--------------------------------------------------")

    
    