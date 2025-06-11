import csv
import re
from definitions import msdef
from definitions import common

def count_from_csv_legacy(file_path,
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

    with open(file_path, "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        data = list(reader)

        merchant_checked = {}
        subscription_checked = {}

        for idx, row in enumerate(reversed(data)):
            
            #Skip excluded records
            if re.search(excl_pattern, row[excl_ref_field]):
                continue

            #Count Install, Uninstall
            if (row[common.EVENT_FIELD] == common.INSTALLED_STRING):
                installed_count += 1
            if (row[common.EVENT_FIELD] == common.UNINSTALLED_STRING):
                uninstalled_count += 1

            if not(merchant_checked.get(row[merchant_key], False)):
                for i_idx, i_row in enumerate(data):
                    if (i_row[merchant_key] == row[merchant_key]):
                        merchant_checked[i_row[merchant_key]] = True

                        if (i_row[common.EVENT_FIELD] == common.UNINSTALLED_STRING):
                            uninstalled_count_wo_installed += 1

                        break

            #Check One-Time
            if (row[common.EVENT_FIELD] in common.ONE_TIME_ACTIVATED_STRINGS):
                one_time_count += 1

                for pack in one_times:
                    if (pack.get("count", "undefined") == "undefined"):
                        pack["count"] = 0
                    if re.search(pack["reg_pattern"], row[common.DETAILS_FIELD]):
                        pack["count"] += 1
                        detailed_results.append({
                            merchant_key: row[merchant_key],
                            "paid_type": "One-Time",
                            "detail": pack["name"]})
                        break
                
                continue

            #Check Subscription
            if subscription_checked.get(row[merchant_key], False):
                continue

            if (row[common.EVENT_FIELD] in common.SUBSCRIPTION_CANCELED_STRINGS):
                subscription_checked[row[merchant_key]] = True

                for i_idx, i_row in enumerate(reversed(data)):
                    if (i_row[merchant_key] == row[merchant_key]):
                        if (i_idx <= idx):
                            continue
                        if (i_row[common.TIME_FIELD] != row[common.TIME_FIELD]):
                            break
                        if (i_row[common.EVENT_FIELD] in common.SUBSCRIPTION_ACTIVATED_STRINGS):
                            subscription_checked[row[merchant_key]] = False
                            break

                continue

            if (row[common.EVENT_FIELD] in common.SUBSCRIPTION_ACTIVATED_STRINGS):
                subscription_checked[row[merchant_key]] = True
                count = True

                for i_idx, i_row in enumerate(reversed(data)):
                    if (i_row[merchant_key] == row[merchant_key]):
                        if (i_idx <= idx):
                            continue
                        if (i_row[common.TIME_FIELD] != row[common.TIME_FIELD]):
                            break
                        if (i_row[common.EVENT_FIELD] in common.SUBSCRIPTION_CANCELED_STRINGS):
                            count = False
                            break

                if not(count):
                    continue

                subscription_count += 1

                for plan in subscriptions:
                    if (plan.get("count", "undefined") == "undefined"):
                        plan["count"] = 0
                    if re.search(plan["reg_pattern"], row[common.DETAILS_FIELD]):
                        plan["count"] += 1
                        detailed_results.append({
                            merchant_key: row[merchant_key],
                            "paid_type": "Subscription",
                            "detail": plan["name"]})
                        
                        break

                continue
    
    
    count_result = {
        common.INSTALLED_STRING: installed_count,
        common.UNINSTALLED_STRING: uninstalled_count,
        common.UNINSTALLED_OLD_STRING: uninstalled_count_wo_installed,
        common.ONE_TIME_STRING: one_time_count,
        common.SUBSCRIPTION_STRING: subscription_count,
    }
    
    return count_result, subscriptions, one_times, detailed_results

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python count_legacy.py <path_to_csv_file>")
        sys.exit(1)

    print("Running Default: Count for Magestore Barcode App")
    print("--------------------------------------------------")
    
    # Get file path from argument
    file_path = sys.argv[1]
    print("Input File: ", file_path)
    print("--------------------------------------------------")

    # Import definitions
    import definitions.sbmdef as appdef

    subscriptions = appdef.DEFAULT_PAID_SUBSCRIPTIONS
    one_times = appdef.DEFAULT_PAID_ONE_TIME
    excl_pattern = msdef.DEFAULT_INTERNAL_EMAIL_PATTERN
    excl_ref_field = common.EMAIL_FIELD
    merchant_key = common.KEY_FIELD
    count_result, subscriptions, one_times, detailed_results = count_from_csv_legacy(
        file_path, subscriptions, one_times, excl_pattern, excl_ref_field, merchant_key)
    
    one_time_count_check = 0
    subscriptions_count_check = 0

    #Print results
    print("SUMMARIZE RESULTS")
    print("Installed: ", count_result[common.INSTALLED_STRING])
    print("Uninstalled ", count_result[common.UNINSTALLED_STRING])
    print("Churn Rate: ", count_result[common.UNINSTALLED_STRING]/count_result[common.INSTALLED_STRING] * 100)
    print("Uninstalled without Installed: ", count_result[common.UNINSTALLED_OLD_STRING])

    print("\nTotal Paid Count:", count_result[common.SUBSCRIPTION_STRING] + count_result[common.ONE_TIME_STRING])  
    print("    Subscription Count: ", count_result[common.SUBSCRIPTION_STRING])
    for sub in subscriptions:
        subscriptions_count_check += sub.get('count', 0)
        print(f"        {sub['name']}: {sub.get('count', 0)}")
    print("    One-Time Count: ", count_result[common.ONE_TIME_STRING])
    for one_time in one_times:
        one_time_count_check += one_time.get('count', 0)
        print(f"        {one_time['name']}: {one_time.get('count', 0)}")

    print("--------------------------------------------------")

    #Check if counts match
    if (count_result[common.ONE_TIME_STRING] != one_time_count_check):
        print("Error detected: One-Time Count is not equal total of Packages Counts")
        print("---------------------------------------------------")

    if (count_result[common.SUBSCRIPTION_STRING] != subscriptions_count_check):
        print("Error detected: Subscription Count is not equal total of Plans Counts")
        print("---------------------------------------------------")

    # Print detailed results
    print("DETAILED RESULTS")
    for detail in detailed_results:
        print(f"{detail[merchant_key]} - {detail['paid_type']}: {detail['detail']}")
    print("--------------------------------------------------")

    
    