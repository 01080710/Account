from larkapi  import (raise_validation_error)
from record   import transformer_df
from general  import run_admin_jobs
from payload  import payload_type
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import asyncio
import mapping



def run_account_pipeline(logger, client, sheet_token, input_id, output_id, record_id, uid):
    
    ### Step 0 : Check whether the existing data belongs to a previous date. -> ouput_id
    logger.extra["stage"] ,logger.extra["uid"] = f"check_output_date" ,uid
    logger.info("Starting validation of existing records in the output sheet.")
    df2 = client.query_sheet(spreadsheet_token=sheet_token, sheet_id=output_id)
    logger.info(f"Existing records found in output sheet. " f"total_rows={len(df2)-1}. " f"Validating data freshness.")

    if len(df2) > 1: # 是否太鬆散，需確認 !
        df2 = pd.DataFrame(df2[1:], columns=df2[0])
        df2["comparisionTime"] = pd.to_datetime(df2["comparisionTime"], errors="coerce")
        mode_time = df2["comparisionTime"].mode().iloc[0]  # Getting mode's  date 
        today = datetime.now().date()                      # Getting today's date
        if mode_time.date() < today:
            logger.info(f"Outdated data detected (data_date={mode_time.date()}, " f"today={today}). Resetting output sheet.")
            client.delete_sheet(spreadsheet_token=sheet_token ,sheet_id=output_id, start_index=2)                   # Remove all existing records while keeping the header row
            client.add_sheet(spreadsheet_token=sheet_token ,sheet_id=output_id ,length=1 ,major_dimension="ROWS")   # Add an empty row for the new day's data
            logger.info("Output sheet has been successfully reset.")
    else:
        logger.info("No existing records found in the output sheet.")
    logger.info("Output sheet validation completed.")   
        
        
        
        
    ### Step 1 : Determine whether to proceed with execution. -> input_id
    logger.extra["stage"] ,logger.extra["uid"] = f"check_input_execution" ,uid
    logger.info(f"Starting input sheet validation. input_id={input_id}")

    df = client.query_sheet(spreadsheet_token=sheet_token,sheet_id=input_id)
    df = pd.DataFrame(df[1:], columns = df[0])
    logger.info(f"Input sheet loaded successfully. total_rows={max(len(df)-1, 0)}")

    requestor_ok = ('Requestor' in df.columns and df['Requestor'].notna().any())
    data_ok = (not df.drop(columns=['Requestor']).isna().all().all())
    logger.info(f"Validation result: " f"requestor_ok={requestor_ok}, " f"data_ok={data_ok}")

    err_comparisionTime = datetime.now(ZoneInfo("Asia/Taipei")).strftime("%Y-%m-%d %H:%M:%S")
    if not requestor_ok and not data_ok: # Flase + False
        error_message = "Input validation failed: 'Requestor' 欄位未填寫，且未提供任何'Account' 或 'UserId' 查詢資料。"
        logger.error("Input validation failed. " "Missing Requestor and query data.")
        raise "both od parameters are empty,and no mission running."
        
    elif not requestor_ok:                 # Flase + True
        error_message = "Input validation failed: 'Requestor' 欄位為必填欄位。"
        logger.error("Input validation failed. " "Requestor field is missing.")
        raise_validation_error(client, sheet_token, record_id, err_comparisionTime ,error_message)

    elif not data_ok:                      # True + False
        error_message = "Input validation failed: 未提供任何查詢資料，請至少填寫一個 'Account' 或 'UserId'。"
        logger.error("Input validation failed. "  "No query data provided.")
        raise_validation_error(client, sheet_token, record_id, err_comparisionTime, error_message, requestor=df.at[0, 'Requestor'])

    logger.info("Input validation completed successfully.")




    ### step2 : Validate crawler account range and execution status.
    logger.extra["stage"] ,logger.extra["uid"] = f"check_specific_column" ,uid
    logger.info("Start validating crawler input columns.")

    row0 = df.iloc[0, 1:]
    valid_columns = row0[row0.notna()].index.tolist()
    if not valid_columns:
        logger.error("No valid account column found in input sheet.")
        raise ValueError("Invalid input: no valid account column.")

    valid_column = valid_columns[0]
    logger.info(f"Detected valid column: {valid_column}")

    Ids = df[valid_column].dropna().astype(str).unique().tolist()
    requestor = df.at[0, 'Requestor']
    logger.info(f"Extracted IDs successfully. " f"total_ids={len(Ids)}, requestor={requestor}")

    account_type  = ['RebateAccount', 'TradingAccount'] 
    column_type   = ['userId', 'Account'] 
    Account = next((x for x in account_type if x in valid_column), None)
    column  = next(('UserId' if x == 'userId' else 'Account' for x in column_type if x in valid_column) ,None)
    logger.info(f"Resolved account mapping. " f"account_type={Account}, column_type={column}")
    logger.info("Crawler input validation completed.")




    ### step3 : Run the crawler.
    logger.extra["stage"] ,logger.extra["uid"] = f"crawler_execution" ,uid
    logger.info("Crawler execution started.")
    url_map ,country_map ,enable_map  = mapping.url_map ,mapping.country_map ,mapping.enable_map
    jobs = payload_type(Ids ,report_type=url_map[Account] ,column_type=column) 
    result = asyncio.run(run_admin_jobs(BRANDS = ["VFSC" ,"VFSC2"], jobs = jobs ,logger=logger))
    logger.info(f"Crawler execution completed. " f"result_counts={len(result) if result else None}")



    ### step4 : Perform data cleaning and column transformation.
    logger.extra["stage"] ,logger.extra["uid"] = f"data_cleaning" ,uid
    logger.info(f"data cleaning started.")

    suc_comparisionTime = datetime.now(ZoneInfo("Asia/Taipei")).strftime("%Y-%m-%d %H:%M:%S")
    export_columns = [
        "Requestor","user_id","ownerAlias","owner" ,"mt4_account" ,"server" ,"accountMT4Type_display","group",
        "countryCode","currency","balance","profit","margin","marginLevel","equity","credit",
        "leverage","enableReadonly","regulator","approvedTime","updateTime","comparisionTime"]

    TradingAccount_Result = (
        pd.concat(
            [
                df.assign(regulator=regulator)
                for regulator, df in result['data'].items()
            ],
            ignore_index=True,
        ).assign(
            Requestor       = requestor,
            server          = lambda x: x["dataSource"].apply(lambda d: d["name"]),
            countryCode     = lambda x: x["countryCode"].astype(str).map(country_map),
            enableReadonly  = lambda x: x["enableReadonly"].astype(str).map(enable_map),
            comparisionTime = suc_comparisionTime,
            empty_jobs      = lambda x: [result["empty_jobs"]] * len(x))
    )
    logger.info(f"Data transformation completed. " f"output_rows={len(TradingAccount_Result)}")



    ### step5 : Upload the processed data and execution logs. -> output_id, input_id ,reocrd_id 
    logger.extra["stage"] ,logger.extra["uid"] = f"upload_lark" ,uid
    logger.info(f"Starting data upload to Lark. " f"target_rows={len(TradingAccount_Result)}")

    result = TradingAccount_Result
    df_ouput  =  (result[export_columns].fillna("").astype(str).values.tolist())
    df_record = transformer_df(df=result ,requestor=requestor ,comparison_time=suc_comparisionTime ,return_message="Success")

    client.append_sheet(spreadsheet_token=sheet_token ,sheet_id= output_id ,datas = df_ouput ,row=1)
    logger.info("Output data uploaded successfully.")

    client.append_sheet(spreadsheet_token=sheet_token ,sheet_id= record_id ,datas = df_record ,row=1)
    logger.info("Execution record uploaded successfully.")

    client.delete_sheet(spreadsheet_token=sheet_token, sheet_id=input_id ,start_index=2)
    client.add_sheet(spreadsheet_token=sheet_token,sheet_id=input_id,length=1,major_dimension="ROWS")
    logger.info("Input sheet reset completed.")

    client.close()
    logger.info("Lark client closed. Pipeline execution finished successfully.")
