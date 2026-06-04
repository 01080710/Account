from larkapi import (LarkSheetClient, raise_validation_error)
from general  import run_admin_jobs
from record import transformer_df
from payload  import payload_type
from datetime import datetime
from zoneinfo import ZoneInfo
from logger import get_logger
import pandas as pd
import asyncio
import mapping


app_id ,app_secret    = "cli_a86751faa8f9d029" ,"TjZ5cprV3v3Y6Afj3UcZtea1qayrzpVn"
sheet_token ,input_id ,output_id , record_id  = "Y4kHsx8L7herZXtbQgdlIsjZgOd" ,"Ljf7WY" ,"dfhASp" ,"MXFdf3"
logger = get_logger(service="Account Async",logger_name=f'upload data to lark', stage='start')
client = LarkSheetClient(app_id=app_id ,app_secret=app_secret ,logger=logger)



### Step0 : Determine today's data or not.
df2 = client.query_sheet(spreadsheet_token=sheet_token, sheet_id=output_id)
if len(df2) > 1:
    df2 = pd.DataFrame(df2[1:], columns=df2[0])
    df2["comparisionTime"] = pd.to_datetime(df2["comparisionTime"], errors="coerce")

    mode_time = df2["comparisionTime"].mode().iloc[0]  # 取得眾數日期
    today = datetime.now().date()                      # 今天日期
    if mode_time.date() < today:
        client.delete_sheet(
            spreadsheet_token=sheet_token,
            sheet_id=output_id,
            start_index=2
        )
    
### Step1 : Getting Mapping List & Determine continue run or not.
df = client.query_sheet(spreadsheet_token=sheet_token,sheet_id=input_id)
df = pd.DataFrame(df[1:], columns = df[0])
requestor_ok = ('Requestor' in df.columns and df['Requestor'].notna().any())
data_ok = (not df.drop(columns=['Requestor']).isna().all().all())

comparisionTime = datetime.now(ZoneInfo("Asia/Taipei")).strftime("%Y-%m-%d %H:%M:%S")
if not requestor_ok and not data_ok: # Flase + False
    error_message = "Input validation failed: 'Requestor' 欄位未填寫，且未提供任何 'Account' 或 'UserId' 查詢資料。"
    raise_validation_error(client ,sheet_token ,record_id ,comparisionTime ,error_message)
    
if not requestor_ok:                 # Flase + True
    error_message = "Input validation failed: 'Requestor' 欄位為必填欄位。"
    raise_validation_error(client, sheet_token, record_id, comparisionTime ,error_message)

if not data_ok:                      # True + False
    error_message = "Input validation failed: 未提供任何查詢資料，請至少填寫一個 'Account' 或 'UserId'。"
    raise_validation_error(client, sheet_token, record_id, comparisionTime, error_message, requestor=df.at[0, 'Requestor'])



### step2 : Checking Range of Account Crawler (It can run.)
url_map ,country_map ,enable_map  = mapping.url_map ,mapping.country_map ,mapping.enable_map
row0 = df.iloc[0, 1:]
valid_column = row0[row0.notna()].index.tolist()[0]
Ids = df[valid_column].dropna().astype(str).unique().tolist()
requestor = df.at[0, 'Requestor']
account_type ,column_type = ['RebateAccount', 'TradingAccount'] ,['userId', 'Account'] 
Account = next((x for x in account_type if x in valid_column), None)
column  = next(('UserId' if x == 'userId' else 'Account' for x in column_type if x in valid_column),None)
# print(requestor ,Account ,column)



### step3 : Start to run crawler 
jobs = payload_type(Ids ,report_type=url_map[Account] ,column_type=column) # column = 'UserId' or 'Account'
result = asyncio.run(run_admin_jobs(BRANDS = ["VFSC" ,"VFSC2"], jobs = jobs))



### step4 : Data Cleaning and column reshaping
comparisionTime1 = datetime.now(ZoneInfo("Asia/Taipei")).strftime("%Y-%m-%d %H:%M:%S")
export_columns = [
    "Requestor","user_id","ownerAlias","owner" ,"mt4_account" ,"server" ,"accountMT4Type_display","group",
    "countryCode","currency","balance","profit","margin","marginLevel","equity","credit",
    "leverage","enableReadonly","regulator","approvedTime","updateTime","comparisionTime"]

TradingAccount_Result = (
    pd.concat(
        [
            df.assign(regulator=regulator)
            for regulator, df in result.items()
        ],
        ignore_index=True,
    ).assign(
        Requestor       = requestor,
        server          = lambda x: x["dataSource"].apply(lambda d: d["name"]),
        countryCode     = lambda x: x["countryCode"].astype(str).map(country_map),
        enableReadonly  = lambda x: x["enableReadonly"].astype(str).map(enable_map),
        comparisionTime = comparisionTime1)
)


### step5 : Data and Log Uploading 
result = TradingAccount_Result[export_columns] 
df_ouput  =  (result.fillna("").astype(str).values.tolist())
df_record = transformer_df(df=result ,requestor=requestor ,comparison_time=comparisionTime1 ,return_message="Success")
client.append_sheet(spreadsheet_token=sheet_token ,sheet_id= output_id ,datas = df_ouput ,row=1)
client.append_sheet(spreadsheet_token=sheet_token ,sheet_id= record_id ,datas = df_record ,row=1)
client.delete_sheet(spreadsheet_token=sheet_token, sheet_id=input_id ,start_index=2)
client.close()

