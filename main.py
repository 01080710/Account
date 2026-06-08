from pipeline import run_account_pipeline
from larkapi import LarkSheetClient
from logger import get_logger
import traceback
import uuid




uid = str(uuid.uuid4())
app_id , app_secret = "cli_a86751faa8f9d029" ,"TjZ5cprV3v3Y6Afj3UcZtea1qayrzpVn"
sheet_token ,input_id ,output_id, record_id = "HtYXsSuG5hyTNBtrnLsl8boTgBc" ,"e04894" ,"uSQERs" ,"UxZYN9" # production
# sheet_token ,input_id ,output_id, record_id = "Y4kHsx8L7herZXtbQgdlIsjZgOd" ,"Ljf7WY" ,"dfhASp" ,"MXFdf3" # develope
try:
    logger = get_logger(service = "account-search-service" ,logger_name = 'account-search', stage='initialization')
    logger.extra["stage"] ,logger.extra["uid"] = "lark_client_initialization" ,uid
    
    logger.info("Initializing Lark Sheet client Started")
    client = LarkSheetClient(app_id=app_id ,app_secret=app_secret ,logger=logger)
    logger.info("Initializing Lark Sheet client Completed")
    
    run_account_pipeline(logger=logger, client=client, sheet_token=sheet_token, input_id=input_id, output_id=output_id, record_id=record_id, uid=uid)
    logger.info("Cycle completed successfully.")

except Exception as e:
    logger.error(f"Cycle failed: {str(e)}")
    logger.error(traceback.format_exc())

