from datetime import datetime
import re


def check_duplicates(data):
    seen = set()
    duplicates = []

    for entry in data:

        if entry['email'] in seen:
            duplicates.append(entry['email'])
        elif entry['serial_number'] in seen:
            duplicates.append(entry['serial_number'])
        else:
            seen.add(entry['email'])
            seen.add(entry['serial_number'])
    print(seen, duplicates)
    return duplicates


def get_today_date_formatted():
    today = datetime.today()
    formatted_date = today.strftime("%d.%m")
    return formatted_date


def validate_name_and_date(text):
    
    parts = text.split(' ')
    name, date, link = parts
    
    # Regular expression to check if the date is in the format DD.MM
    date_pattern = r'^\d{2}\.\d{2}$'
    
    # Validate the date format
    if not re.match(date_pattern, date):
        return False
    
    return True


def is_valid_date_format(date_string):
    # Define the regular expression pattern for "mm.dd"
    pattern = r'^(0[1-9]|[12][0-9]|3[01])\.(0[1-9]|1[0-2])$'
    
    # Use the re.match() function to check if the date_string matches the pattern
    if re.match(pattern, date_string):
        return True
    else:
        return False


def get_data_by_date(data, date):
    result = []
    start_collecting = False
    
    for item in data:
        if item == [date, date]:
            start_collecting = True
            continue
        if start_collecting:
            if len(item) > 1:
                if item and '@' in item[1]:  # Check if the item is a valid entry (contains an email)
                    result.append(item)
                else:  # Stop collecting when the next date or an empty array is encountered
                    break
    
    return result

def get_data_from_sheet(data):
    result = []

    for item in data:
        if len(item) > 1:
            if item and '@' in item[1]:
                result.append(item)
            else: break
    
    return result


def format_fdata(data):
    result = []
    for el in data:
        result.append({'email': el[1], 'serial_number': el[0]})
    return result
    
    
def clean_url(url: str) -> str:
    return url.strip('<>')