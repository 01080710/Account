import pandas as pd

def transformer_df(df: pd.DataFrame ,requestor:str, comparison_time: str ,return_message: str) :

    manual_seconds_per_account = 20   # 假設人工處理一個帳戶平均需要 20 秒
    hourly_cost = 200                 # 假設每小時人力成本 500 元
    total_accounts = len(df)
    total_users = df["user_id"].nunique()
    total_users_list  = (df["user_id"].dropna().astype(str).unique().tolist())
    total_missing = len(df["empty_jobs"].iloc[0])
    total_missing_list  = df["empty_jobs"].iloc[0]
    countries_covered = (df["countryCode"].dropna().nunique())
    servers_covered = (df["server"].dropna().nunique())
    regulators_covered = (df["regulator"].dropna().nunique())
    account_types_covered = (df["accountMT4Type_display"].dropna().nunique())
    earliest_update_time = df["updateTime"].min()
    latest_update_time   = df["updateTime"].max()
    total_balance = (df["balance"].fillna(0).sum() if "balance" in df.columns else None)
    total_equity = (df["equity"].fillna(0).sum()   if "equity" in df.columns else None)
    total_credit = (df["credit"].fillna(0).sum()   if "credit" in df.columns else None)
    estimated_hours_saved = round(total_accounts * manual_seconds_per_account / 3600, 2)
    estimated_value_twd   = round(estimated_hours_saved * hourly_cost, 0)
    
    summary_df = pd.DataFrame([{
        # 基本資訊
        "requestor": requestor,
        "comparison_time": comparison_time,

        # 使用量
        "total_users": total_users,
        "total_users_list " : total_users_list ,
        "total_accounts": total_accounts,
        "total_missing" : total_missing,
        "total_missing_list" : total_missing_list,

        # 覆蓋範圍
        "countries_covered": countries_covered,
        "servers_covered": servers_covered,
        "regulators_covered": regulators_covered,
        "account_types_covered": account_types_covered,

        # 財務規模
        "total_balance": total_balance,
        "total_equity": total_equity,
        "total_credit": total_credit,

        # 資料範圍
        "earliest_update_time": earliest_update_time,
        "latest_update_time": latest_update_time,

        # 量化指標
        "manual_seconds_per_account": manual_seconds_per_account,
        "estimated_hours_saved": estimated_hours_saved,
        "estimated_twd_saved": estimated_value_twd,
        "return_msg" : return_message,
    }])

    return summary_df.fillna("").astype(str).values.tolist()
