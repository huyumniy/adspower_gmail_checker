import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from utils import get_today_date_formatted
from datetime import datetime
from pprint import pprint
from utils import get_data_by_date, is_valid_date_format

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = '1XbTZSQiYycVwlk9Qqucy_V7IFQLfdbRMDU9DUn9u9qc'


def get_sheet_names():
    try:
        service = get_google_sheets_service()
        if not service:
            return None

        spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        sheets = spreadsheet.get('sheets', [])
        sheet_names = [sheet['properties']['title'] for sheet in sheets]
        return sheet_names
    except HttpError as error:
        print(f"An HTTP error occurred: {error}")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def get_google_sheets_service():
    try:
        creds = None
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
                creds = flow.run_local_server(port=0)

            with open("token.json", "w") as token:
                token.write(creds.to_json())

        service = build("sheets", "v4", credentials=creds)
        return service
    except Exception as e:
        print(f"An error occurred while creating the service: {e}")
        return None


def get_data_from_google_sheets(sheet="main"):
    try:
        service = get_google_sheets_service()
        if not service:
            return None
        range_name = f"{sheet}!A2:G"
        request = service.spreadsheets().values().batchGet(spreadsheetId=SPREADSHEET_ID, ranges=[range_name])
        response = request.execute()
        values = ''
        values_raw = response['valueRanges'][0]
        values = values_raw.get('values')
        if values == None:
            return False
        else: return values
    except HttpError as error:
        print(f"An HTTP error occurred: {error}")
        return None
    except Exception as e:
        print('get_data_from_google_sheets')
        print(f"An error occurred: {e}")
        return None
    


def get_sheet_id(sheet_name):
    try:
        service = get_google_sheets_service()
        spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        sheets = spreadsheet.get('sheets', [])
        for sheet in sheets:
            if sheet['properties']['title'] == sheet_name:
                return sheet['properties']['sheetId']
        return None
    except HttpError as error:
        print(f"An HTTP error occurred: {error}")
        return None


def save_data_to_google_sheets(sheet, data):
    try:
        service = get_google_sheets_service()
        if not service:
            return

        # Ensure data is in the correct format
        formatted_data = []
        for row in data:
            if isinstance(row, list):
                formatted_data.append([str(cell) if cell is not None else "" for cell in row])
            else:
                print(f"Invalid row format: {row}")
                return False

        # Get existing data to find the next empty row
        existing_data = get_data_from_google_sheets(sheet=sheet)
        next_row = 2
        if existing_data:
            next_row = len(existing_data) + 2  # +2 because data starts at A2

        range_name = f"{sheet}!A{next_row}"
        body = {
            "values": formatted_data
        }
        print(service.spreadsheets())
        result = service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID, range=range_name,
            valueInputOption="USER_ENTERED", body=body).execute()
        print(result)
        sheet_id = get_sheet_id(sheet)
        if sheet_id is None:
            print("Sheet ID not found.")
            return False

        print(f"{result.get('updatedCells')} cells updated.")

        requests = [
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,  # Adjust if necessary
                        "startRowIndex": next_row - 1,  # Adjust to 0-index
                        "endRowIndex": next_row,
                        "startColumnIndex": 0,
                        "endColumnIndex": len(data[0])
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {
                                "red": 0.0,
                                "green": 1.0,
                                "blue": 0.0
                            }
                        }
                    },
                    "fields": "userEnteredFormat.backgroundColor"
                }
            }
        ]

        # Update the background color of the updated cells to green
        # Add requests to paint F column cells yellow if they contain data
        for i, row in enumerate(formatted_data):
            if len(row) >= 6 and row[5]:  # F column is the 6th column (index 5)
                requests.append(
                    {
                        "repeatCell": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": next_row - 1,
                                "endRowIndex": next_row,
                                "startColumnIndex": 5,
                                "endColumnIndex": 6
                            },
                            "cell": {
                                "userEnteredFormat": {
                                    "backgroundColor": {
                                        "red": 1.0,
                                        "green": 1.0,
                                        "blue": 0.0
                                    }
                                }
                            },
                            "fields": "userEnteredFormat.backgroundColor"
                        }
                    }
                )

        batch_update_request_body = {
            "requests": requests
        }

        response = service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body=batch_update_request_body
        ).execute()

        print("Cells updated with green background color.")

        # Update a cell to force recalculation
        force_recalc_range = f"{sheet}!A1"
        force_recalc_body = {
            "values": [[""]]
        }
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID, range=force_recalc_range,
            valueInputOption="USER_ENTERED", body=force_recalc_body).execute()

        print("Sheet recalculated by updating a dummy cell.")
        return True

    except HttpError as error:
        print(f"An HTTP error occurred: {error}")
        return False
    except Exception as e:
        print('save_data_to_google_sheets')
        print(f"An error occurred: {e}")
        return False



def get_data_from_range(sheet="main", start_row=2, end_row=None, start_col="A", end_col="G", spreadsheet_id=SPREADSHEET_ID):
    try:
        service = get_google_sheets_service()
        if not service:
            return None

        if end_row is None:
            range_name = f"{sheet}!{start_col}{start_row}:{end_col}"
        else:
            range_name = f"{sheet}!{start_col}{start_row}:{end_col}{end_row}"

        request = service.spreadsheets().values().batchGet(spreadsheetId=spreadsheet_id, ranges=[range_name])
        response = request.execute()

        values = response['valueRanges'][0].get('values', [])

        return values
    except HttpError as error:
        print(f"An HTTP error occurred: {error}")
        return None
    except Exception as e:
        print('get_data_from_range')
        print(f"An error occurred: {e}")
        return None


def get_data_from_all_sheets():
    service = get_google_sheets_service()

    sheet_metadata = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    sheets = sheet_metadata.get('sheets', [])

    all_data = {}

    for sheet in sheets:
        sheet_name = sheet['properties']['title']
        data_range = f'{sheet_name}!H2:I3'
        result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=data_range).execute()
        values = result.get('values', [])

        if values:
            all_data[sheet_name] = values
    
    return all_data


def get_data_from_google_sheet_A(today_datetime):
    try:
        print(today_datetime)
        service = get_google_sheets_service()
        spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        sheets = spreadsheet.get('sheets', [])
        sheet_names = [sheet['properties']['title'] for sheet in sheets]

        if not service:
            return None
        
        data = []
        for sheet_name in sheet_names:
            print(sheet_name)
            range_name = f"{sheet_name}!A2:D"
            request = service.spreadsheets().values().batchGet(spreadsheetId=SPREADSHEET_ID, ranges=[range_name])
            response = request.execute()
            print(response)

            # Retrieve the list of lists
            values = response['valueRanges'][0].get('values', [])
            is_appended = False
            for row in values:
                if not row: continue
                # Check if the first column (A) matches today_datetime and append the whole row if it matches
                if row[0] == today_datetime:
                    data.append({sheet_name: row})
                    is_appended = True
            if not is_appended: data.append({sheet_name: []})

        return data
    except HttpError as error:
        print(f"An HTTP error occurred: {error}")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


if __name__ == "__main__":
    # Example usage for getting data
    # save_data_to_google_sheets(sheet="Тест", data=[['10.07', 1, 25]])
    today_date = get_today_date_formatted()
    all_data = get_data_from_google_sheet_A(today_date)
    print(all_data)
    message = f":calendar:Статистика по працівникам за *{today_date}* день:calendar::\n"
    for data_example in all_data:
        for sheet_name, data in data_example.items():
            message += f"Дані зі сторінки *{sheet_name}:*"
            if data == []: message += f" - Немає даних\n"
            else: message += f" - Аккаунтів: *{data[2]}/{data[3]}*\n"
    print(message)