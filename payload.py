def payload_type(search_values: list,
                 report_type: str = "TradingAccount",
                 column_type: str = "UserId"):
    
    from copy import deepcopy
    ACCOUNT_PAYLOAD  = {
        'skipCount': False,
        'pagination': {'limit': 100,'pageNo': 1,'offset': 0},
        'parameters': {
            'mt4DatasourceId': {'filterType': 'SELECT','input': None},
            'userId': {'fuzzy': False,'filterType': 'INPUT','input': ''},
            'owner': {'filterType': 'CUSTOM','input': ''},
            'clientNameIpt': {'fuzzy': True,'filterType': 'INPUT','input': ''},
            'clientNameEn': {'fuzzy': True,'filterType': 'INPUT','input': ''},
            'cpa': {'filterType': 'INPUT','input': ''},
            'tb_user_extends.opNote': {'filterType': 'INPUT','input': '' },
            'mamNumber': {'filterType': 'INPUT','input': ''},
            'tb_user.phoneNum': {'filterType': 'INPUT','input': ''},
            'tb_user.email': {'filterType': 'INPUT','input': ''},
            'tb_user.countryCode': {'filterType': 'SELECT','input': None},
            'mt4Account': {'fuzzy': False,'filterType': 'INPUT','input': ''},
            'mt4AccountType': {'filterType': 'SELECT','input': None},
            'mt4Group': {'filterType': 'INPUT','input': ''},
            'applyCurrency': {'filterType': 'SELECT','input': None},
            'approvedTime': {'filterType': 'DATEPICKER','input': {}},
            'updateTime': {'filterType': 'DATEPICKER','input': {}},
            'campaignSource': {'filterType': 'INPUT','input': ''},
            'tb_user_extends.webSource': {'filterType': 'SELECT','input': None},
            'depositStatus': {'filterType': 'SELECT','input': ''},
            'labelType': {'filterType': 'SELECT','input': None},
            'is_archive': {'filterType': 'SELECT','input': ''},  # Account Activity => Normal = '0' ; Archieve = '1,2' ; Full = ''
            'markUserType': {'filterType': 'SELECT','input': ''},
            'directLevel': {'filterType': 'CUSTOM','input': '5'},
            'user_id': {'filterType': 'CUSTOM','input': ''},
            'org_id': {'filterType': 'CUSTOM','input': ''},
            'real_name': {'filterType': 'CUSTOM','input': '' },
            'license': {'filterType': 'CUSTOM','input': '' },
        },
    }

    def build_account_payload(
        page_no: int,
        limit: int,
        userId: str = "",
        mt4Account: str = "",
        payload_template: dict = ACCOUNT_PAYLOAD,
    ):
        payload = deepcopy(payload_template)
        payload["pagination"]["pageNo"] = page_no
        payload["pagination"]["limit"] = limit
        payload["pagination"]["offset"] = (
            (page_no - 1) * limit
        )
        payload["parameters"]["userId"]["input"] = userId
        payload["parameters"]["mt4Account"]["input"] = mt4Account
        return payload

    if column_type == "UserId":
        search_values = search_values
        payload_key = "userId"
        prefix = "user"
    elif column_type == 'Account':
        search_values = search_values
        payload_key = "mt4Account"
        prefix = "account"
    else:
        raise ValueError(f"Unsupported column_type: {column_type}")

    jobs = [
        {
            "name":  f"{prefix}_{value}",
            "url": report_type,
            "build_payload": build_account_payload,
            "payload_kwargs": {
                payload_key: value,
            },
            "rows_key": "rows",
            "total_key": "total",
            "limit": 100,
            "page_concurrency": 10,
        }
        for value in search_values
    ]
    
    return jobs