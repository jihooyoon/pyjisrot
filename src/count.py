import csv
import re

from definitions import common, msdef, sbmdef

def count_from_csv(file_path,
                   subscriptions,
                   one_times,
                   excl_pattern = msdef.DEFAULT_INTERNAL_EMAIL_PATTERN,
                   excl_ref_field = common.EMAIL_FIELD):
    
    with open(file_path, "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        data = list(reader)

        for idx, row in enumerate(reversed(data)):
            
            #Skip excluded records
            if re.search(internal_email_pattern, row[excl_ref_field]):
                continue

            #Count Install, Uninstall
