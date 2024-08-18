import logging
import sys
import os
import requests
import time
from utils import get_data_by_date, format_fdata, get_data_from_sheet
from sheets_api import get_data_from_range
import nodriver as uc

API_KEY = 'http://local.adspower.net:50325'

# Define custom log levels
SUCCESS = 25
FAILURE = 35
INFO = 20
logging.addLevelName(SUCCESS, "SUCCESS")
logging.addLevelName(FAILURE, "FAILURE")
logging.addLevelName(INFO, 'INFO')

# Configure logger
class CustomFormatter(logging.Formatter):
    # Colors
    grey = "\x1b[38;21m"
    green = "\x1b[32m"
    yellow = "\x1b[33m"
    red = "\x1b[31m"
    bold_red = "\x1b[31;1m"
    blue = "\x1b[34m"
    reset = "\x1b[0m"

    # Format strings for different parts of the log
    log_format = "{time_color}%(asctime)s{reset} [{level_color}%(levelname)s{reset}] {msg_color}%(message)s{reset}"

    FORMATS = {
        logging.DEBUG: log_format.format(time_color=blue, level_color=grey, msg_color=grey, reset=reset),
        logging.INFO: log_format.format(time_color=blue, level_color=grey, msg_color=yellow, reset=reset),
        SUCCESS: log_format.format(time_color=blue, level_color=green, msg_color=yellow, reset=reset),
        INFO: log_format.format(time_color=blue, level_color=grey, msg_color=yellow, reset=reset),
        logging.WARNING: log_format.format(time_color=blue, level_color=red, msg_color=yellow, reset=reset),
        logging.ERROR: log_format.format(time_color=blue, level_color=red, msg_color=yellow, reset=reset),
        FAILURE: log_format.format(time_color=blue, level_color=bold_red, msg_color=yellow, reset=reset),
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt='%H:%M:%S')
        return formatter.format(record)

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
ch.setFormatter(CustomFormatter())
logger.addHandler(ch)

def ads_request(API_KEY, endpoint='/'):
    while True:
        resp = requests.get(API_KEY + endpoint).json()
        if resp["code"] != 0:
            if resp["msg"] == 'Too many request per second, please check':
                time.sleep(1)
            else:
                logger.error(f"{resp['msg']}")
                logger.error("Please check ads_id")
                return None
        else:
            return resp

async def main(config, data, adspower_api=None):
    driver = await uc.Browser.create(config=config)
    retries = 3
    
    for attempt in range(retries):
        page = await driver.get('https://mail.google.com/mail/u/0/#inbox')
        loading = 0
        while await page.evaluate('document.readyState') == 'loading': 
            if loading == 60: break
            time.sleep(1)
            loading += 1
        if loading == 60: 
            logger.info(f"Спроба {attempt + 1} перезавантажити сторінку")
            continue
        isValid = None
        try: 
            isValid = await page.wait_for(f'div[role][data-identifier*=\"{data["email"]}\"]', timeout=10)
        except: 
            pass
        
        if isValid: 
            break
        else:
            try: 
                isValid = await page.wait_for(f'a[aria-label*=\"{data["email"]}\"]', timeout=10)
            except: 
                pass
        
        if isValid:
            break
        else:
            await page.reload()
            logger.info(f"Спроба {attempt + 1} перезавантажити сторінку")
    
    await page.close()
    ads_request(adspower_api if adspower_api else API_KEY, f'/api/v1/browser/stop?serial_number={data["serial_number"]}')
    isValid = isValid is not None
    return isValid

def run_test(data, adspower_api=None):
    active_browsers = []
    necessary_browsers = []
    for ads_user in data:
        serial_number = ads_user['serial_number']
        group_list = f'/api/v1/browser/active?serial_number={serial_number}'
        resp = ads_request(adspower_api if adspower_api else API_KEY, group_list)
        if resp['data']['status'] == 'Active':
            active_browsers.append(ads_user)
            continue
        else:
            necessary_browsers.append(ads_user)

    if active_browsers:
        for active_browser in active_browsers:
            logger.warning(f"Деякі браузери залишились увімкненими: {active_browser['email']}, {active_browser['serial_number']}")
        return {"status": False, "data": active_browsers}

    success_count, processed_count, problem_browsers = uc.loop().run_until_complete(process_browsers(necessary_browsers))

    if success_count == len(necessary_browsers):
        logger.log(SUCCESS, f"Кількість валідних браузерів: {success_count}/{len(necessary_browsers)}")
    else:
        logger.log(FAILURE, f"Кількість валідних браузерів: {success_count}/{len(necessary_browsers)}")

    logger.info(f"Кількість оброблених браузерів: {processed_count}/{len(necessary_browsers)}")
    
    data = {"status": True, "additional": problem_browsers, "data": success_count, "processed": necessary_browsers}
    return data

async def process_browsers(necessary_browsers, adspower_api=None):
    success_count, processed_count = 0, 0
    problem_browsers = []
    for necessary_browser in necessary_browsers:
        group_list = f'/api/v1/browser/start?serial_number={necessary_browser["serial_number"]}'
        for _ in range(0, 5):
            resp = ads_request(adspower_api if adspower_api else API_KEY, group_list)
            if resp: 
                break
        if not resp: 
            logger.error("В одному з браузерів сталася непередбачувана помилка")
            continue
        host, port = resp['data']['ws']['selenium'].split(':')
        if host and port:
            config = uc.Config(
                user_data_dir=None, headless=False, browser_executable_path=None,
                browser_args=None, sandbox=True, lang='en-US', host=host, port=int(port)
            )
            result = await main(config=config, data=necessary_browser, adspower_api=adspower_api)
            if result: 
                success_count += 1
                logger.log(INFO, f"Оброблено браузерів: {processed_count + 1}/{len(necessary_browsers)} | {necessary_browser['email']}")
            else: 
                logger.error(f"В одному з браузерів не було знайдено пошти: {necessary_browser['email']}, {necessary_browser['serial_number']}")
                problem_browsers.append(f"В одному з браузерів не було знайдено пошти: {necessary_browser['email']}, {necessary_browser['serial_number']}")
            processed_count += 1
    return success_count, processed_count, problem_browsers

if __name__ == "__main__":
    link = input('link: ')
    adspower_api = input('adspower api: ')
    formatted_link = link.split('/')[5]
    data = get_data_from_range(sheet="Work mail", start_col="B", end_col="C", spreadsheet_id=formatted_link)
    ddata = get_data_from_sheet(data)
    fdata = format_fdata(ddata)
    run_test(fdata, adspower_api)
