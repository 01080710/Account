import requests

class LarkSheetClient:
    BASE_URL = "https://open.larksuite.com/open-apis"

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        logger
    ):
        self.logger = logger
        self.app_id = app_id
        self.app_secret = app_secret
        self.access_token = self._get_access_token()

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json; charset=utf-8"
        })

        self.logger.info("LarkSheetClient initialized successfully")



    def _get_access_token(self):

        self.logger.info("Requesting Lark Access Token")
        url = (
            f"{self.BASE_URL}"
            "/auth/v3/app_access_token/internal"
        )

        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }

        resp = requests.post(url, json=payload)
        resp.raise_for_status()
        self.logger.info("Lark Access Token acquired")

        return resp.json()["tenant_access_token"]



    def query_sheet(
        self,
        spreadsheet_token: str,
        sheet_id: str
    ):
        try:
            url = (
                f"{self.BASE_URL}"
                f"/sheets/v2/spreadsheets/{spreadsheet_token}/values_batch_get"
            )
            self.logger.info(
                f"Query sheet started "
                f"(sheet_id={sheet_id})"
            )
            resp = self.session.get(url ,params={
                                            "ranges": sheet_id,
                                            "valueRenderOption": "ToString",
                                            "dateTimeRenderOption": "FormattedString"
                                        }
                                    )

            resp.raise_for_status()
            data = resp.json()
            values = (data.get("data", {}).get("valueRanges", [{}])[0].get("values", []))

            self.logger.info(
                f"Query sheet success "
                f"(rows={len(values)})"
            )

            return values
        
        except Exception as e:
            self.logger.exception(
                f"Query sheet failed "
                f"(sheet_id={sheet_id})"
            )
            raise
    
    
    
    def add_sheet(
        self,
        spreadsheet_token: str,
        sheet_id: str,
        length: int,
        major_dimension: str = "ROWS"
    ):
        try:
            url = (
                f"{self.BASE_URL}"
                f"/sheets/v2/spreadsheets/{spreadsheet_token}/dimension_range"
            )
            self.logger.info(
                f"Add dimension started "
                f"(sheet_id={sheet_id}, "
                f"dimension={major_dimension}, "
                f"length={length})"
            )
            
            payload = {
                "dimension": {
                    "sheetId": sheet_id,
                    "majorDimension": major_dimension,
                    "length": length
                }
            }
            
            resp = self.session.post(url, json=payload)

            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                raise Exception(data.get("msg"))

            add_count = data.get("data", {}).get("addCount", 0)

            self.logger.info(
                f"Add dimension success "
                f"(sheet_id={sheet_id}, added={add_count})"
            )

            return add_count
        
        except Exception:
            self.logger.exception(
                f"Add dimension failed "
                f"(sheet_id={sheet_id})"
            )
            raise



    def append_sheet(
        self,
        spreadsheet_token: str,
        sheet_id: str,
        datas,
        row: int = 2
    ):
        try :
            
            append_url = (
                f"{self.BASE_URL}"
                f"/sheets/v2/spreadsheets/{spreadsheet_token}/values_append"
            )

            query_url = (
                f"{self.BASE_URL}"
                f"/sheets/v2/spreadsheets/{spreadsheet_token}/values_batch_get"
            )

            row_count = len(datas)
            col_count = len(datas[0]) if datas else 0
            self.logger.info(
                f"Append started "
                f"(sheet_id={sheet_id}, rows={row_count})"
            )
            def col_to_letter(n):
                result = ""
                while n > 0:
                    n, rem = divmod(n - 1, 26)
                    result = chr(65 + rem) + result

                return result

            end_col = col_to_letter(col_count)

            range_str = (
                f"{sheet_id}"
                f"!A{row}:{end_col}{row + row_count}"
            )

            payload = {
                "valueRange": {
                    "range": range_str,
                    "values": datas
                }
            }

            resp = self.session.post(append_url, json=payload)
            data = resp.json()

            if resp.status_code != 200:
                raise Exception(resp.text)

            if data.get("code", 0) != 0:
                raise Exception(
                    f"Lark API Error: "
                    f"{data.get('msg')}"
                )

            updated_range = (
                data["data"]["updates"]["updatedRange"]
            )

            verify_resp = self.session.get(query_url, params={
                                                        "ranges": updated_range,
                                                        "valueRenderOption": "ToString",
                                                        "dateTimeRenderOption": "FormattedString"
                                                    }
                                                )

            verify_data = verify_resp.json()
            self.logger.info(
                f"Append success "
                f"(sheet_id={sheet_id})"
            )
            return (verify_data.get("data", {}).get("valueRanges", [{}])[0].get("values", []))
        
        except Exception:
            self.logger.exception(
                f"Append failed "
                f"(sheet_id={sheet_id})"
            )
            raise


    def delete_sheet(
        self,
        spreadsheet_token: str,
        sheet_id: str,
        start_index: int,
        major_dimension="ROWS"
    ):
        try :
            values = self.query_sheet(
                spreadsheet_token,
                sheet_id
            )

            end_index = len(values)

            self.logger.info(
                f"Delete started "
                f"(sheet_id={sheet_id}, start_index={start_index})"
            )
            url = (
                f"{self.BASE_URL}"
                f"/sheets/v2/spreadsheets/{spreadsheet_token}/dimension_range"
            )

            payload = {
                "dimension": {
                    "sheetId": sheet_id,
                    "majorDimension": major_dimension,
                    "startIndex": start_index,
                    "endIndex": end_index
                }
            }

            resp = self.session.delete(url, json=payload)
            data = resp.json()

            if data.get("code") != 0:
                raise Exception(data.get("msg"))

            del_count = data["data"].get("delCount")

            self.logger.info(
                f"Delete success "
                f"(sheet_id={sheet_id}, deleted={del_count})"
            )
            return del_count 
        
        except Exception:
            self.logger.exception(
                f"Delete failed "
                f"(sheet_id={sheet_id})"
            )
            raise


    def close(self):
        self.session.close()
        
        
def raise_validation_error(
    client,
    sheet_token,
    record_id,
    comparison_time,
    error_message,
    requestor="-"
):
    client.logger.warning(
        f"Validation Error: {error_message}"
    )
    row_data = (
          [requestor]
        + [comparison_time]
        + ["-"] * 17
        + [error_message]
    )

    client.append_sheet(
        spreadsheet_token=sheet_token,
        sheet_id=record_id,
        datas=[row_data],
        row=1
    )

    raise ValueError(error_message)