from pipeline import run_account_pipeline
from larkapi import LarkSheetClient
from logger import get_logger
from datetime import datetime
from zoneinfo import ZoneInfo
import traceback
import time
import uuid



# TZ = ZoneInfo("Asia/Taipei")
# def get_next_5min():
#     now = datetime.now(TZ)
#     minute = (now.minute // 5 + 1) * 5
#     if minute < 60:
#         return now.replace(minute=minute, second=0, microsecond=0)
#     else:
#         return now.replace(hour=now.hour + 1, minute=0, second=0, microsecond=0)

# def sleep_until(dt):
#     now = datetime.now(TZ)
#     sec = (dt - now).total_seconds()
#     if sec > 0:
#         time.sleep(sec)
        

# cycle = 0
# while True:
    # cycle += 1
uid = str(uuid.uuid4())

try:
    logger = get_logger(service = "account-search-service" ,logger_name = 'account-search', stage='initialization')
    logger.extra["stage"] ,logger.extra["uid"] = "lark_client_initialization" ,uid
    
    logger.info("Initializing Lark Sheet client Started")
    client = LarkSheetClient(app_id= "cli_a86751faa8f9d029" ,app_secret="TjZ5cprV3v3Y6Afj3UcZtea1qayrzpVn" ,logger=logger)
    logger.info("Initializing Lark Sheet client Completed")
    
    run_account_pipeline(logger=logger, client=client, sheet_token="Y4kHsx8L7herZXtbQgdlIsjZgOd", input_id="Ljf7WY", output_id="dfhASp", record_id="MXFdf3", uid=uid)
    logger.info("Cycle completed successfully.")

except Exception as e:
    logger.error(f"Cycle failed: {str(e)}")
    logger.error(traceback.format_exc())

    # next_run = get_next_5min()
    # logger.info(f"Next run scheduled at {next_run}")
    # sleep_until(next_run)