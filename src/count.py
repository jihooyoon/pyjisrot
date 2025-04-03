import csv
import re

from definitions import common, msdef, sbmdef

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

                for i_index, i_row in enumerate(reversed(data)):
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
                    if re.search(plan["reg_pattern"], row[common.EVENT_FIELD]):
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
    
    return count_result, detailed_results