from datetime import datetime, timedelta
from login import get_cookies_async
from bs4 import BeautifulSoup
import pandas as pd
import calendar 
import aiohttp 
import asyncio
import math


def generate_month_ranges(
    start_year,
    start_month,
    start_day,
    end_year,
    end_month,
    end_day,
):

    ranges = []
    current = datetime(start_year, start_month, 1)
    while current <= datetime(end_year, end_month, 1):
        year = current.year
        month = current.month
        last_day = calendar.monthrange(year, month)[1]

        # start day
        if year == start_year and month == start_month:
            start_day_use = start_day
        else:
            start_day_use = 1

        # end day
        if year == end_year and month == end_month:
            end_day_use = end_day
        else:
            end_day_use = last_day

        start_local = datetime(year ,month ,start_day_use ,0 ,0 ,0)
        end_local   = datetime(year ,month ,end_day_use ,23 ,59 ,59)
        start_utc = start_local - timedelta(hours=8)
        end_utc = end_local - timedelta(hours=8)

        ranges.append({
            "year": year,
            "month": month,
            "startDate": start_local.strftime("%Y-%m-%d %H:%M:%S"),
            "endDate": end_local.strftime("%Y-%m-%d %H:%M:%S"),
            "applicationTime": [
                start_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                end_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            ]
        })

        # next month
        if month == 12:
            current = datetime(year + 1, 1, 1)
        else:
            current = datetime(year, month + 1, 1)

    return ranges


# Parse regulator
def get_current_regulator(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    label = soup.find(id="regulation_label")
    if not label:
        return None
    return label.get_text(strip=True)


# Wait regulator switched
async def wait_regulator_switched(
    session: aiohttp.ClientSession,
    expected_regulator: str,
    timeout : float = 6.0,
    interval: float = 0.3,
):

    start = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start < timeout:
        try:
            async with session.get(
                "https://admin.vantagemarkets.com/admin/main"
            ) as resp:

                html = await resp.text()
                current = get_current_regulator(html)
                # print(f"1. current regulator = {current}")

                if current and expected_regulator in current:
                    # print(f"2. regulator switched to {current}")
                    return
        except Exception as e:
            # print(f"polling error: {e}")
            pass
        await asyncio.sleep(interval)
    raise TimeoutError(
        f"Regulator switch timeout: {expected_regulator}"
    )


async def switch_regulator(
    session: aiohttp.ClientSession,
    brand: str,
):
    headers = {
        "accept": "*/*",
        "accept-language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "origin": "https://admin.vantagemarkets.com",
        "referer": "https://admin.vantagemarkets.com/admin/main",
        "user-agent": "Mozilla/5.0",
        "x-requested-with": "XMLHttpRequest",
    }

    async with session.post(
        "https://admin.vantagemarkets.com/admin/switch-regulator",
        params={"regulator": brand},
        headers=headers,
    ) as resp:
        text = await resp.text()
        # print("switch response:", text.strip()[:200])

        if resp.status != 200:
            raise RuntimeError(f"switch regulator failed: HTTP {resp.status}")

    await wait_regulator_switched(session, brand)


RETRY_STATUS = {429, 500, 502, 503, 504}
async def post_json_with_retry(
    session: aiohttp.ClientSession,
    url: str,
    json_data: dict | None = None,
    params: dict | None = None,
    headers: dict | None = None,
    max_retry: int = 10,
    base_sleep: float = 1.5,
):
    last_error = None
    for attempt in range(1, max_retry + 1):
        try:
            async with session.post(
                url,
                json=json_data,
                params=params,
                headers=headers,
            ) as resp:

                text = await resp.text()
                if resp.status == 401:
                    raise PermissionError("Cookie expired")

                if resp.status in RETRY_STATUS:
                    last_error = f"HTTP {resp.status}: {text[:300]}"
                    await asyncio.sleep(base_sleep * attempt)
                    continue # 若偵測到該錯誤狀態直接跳出

                if resp.status != 200:
                    raise RuntimeError(
                        f"HTTP {resp.status}: {text[:500]}"
                    )

                try:
                    return await resp.json()
                except Exception:
                    raise RuntimeError(f"JSON parse failed: {text[:500]}")

        except PermissionError:
            raise

        except Exception as e:
            last_error = str(e)
            await asyncio.sleep(base_sleep * attempt)

    raise RuntimeError(
        f"Request failed after {max_retry} retries: {last_error}"
    )
    

async def fetch_one_page(
        session: aiohttp.ClientSession,
        job: dict,
        page_no: int,
        limit: int,
        sem: asyncio.Semaphore,
    ):
    async with sem:
        payload_kwargs = job.get("payload_kwargs", {})

        json_data = job["build_payload"](
            page_no=page_no,
            limit=limit,
            **payload_kwargs,
        )

        result = await post_json_with_retry(
            session=session,
            url=job["url"],
            json_data=json_data,
        )

        rows_key = job.get("rows_key", "rows")
        total_key = job.get("total_key", "total")
        rows = result.get(rows_key, [])
        total = result.get(total_key, 0)
        # print(f"{job['name']} page {page_no} 完成，筆數：{len(rows)}")

        return {
            "page_no": page_no,
            "rows": rows,
            "total": total,
        }


async def fetch_job(
    session: aiohttp.ClientSession,
    job: dict,
    global_sem: asyncio.Semaphore,
    logger: None
):

    limit = job.get("limit", 100)
    first_page = await fetch_one_page(
        session=session,
        job=job,
        page_no=1,
        limit=limit,
        sem=global_sem,
    )

    total = first_page["total"]
    all_rows = first_page["rows"]
    total_pages = (1 if total == 0 or not all_rows  else math.ceil(total / limit))

    if total_pages > 1:
        tasks = [
            fetch_one_page(
                session=session,
                job=job,
                page_no=page_no,
                limit=limit,
                sem=global_sem,
            )
            for page_no in range(2, total_pages + 1)
        ]

        results = await asyncio.gather(*tasks)

        results.sort(
            key=lambda x: x["page_no"]
        )

        for item in results:
            all_rows.extend(item["rows"])

    df = pd.DataFrame(all_rows)
    
    if df.empty:
        pass
    else:
        df["brand"] = job["brand"]
        df["job_name"] = job["job_name"]

    return {
        "df": df,
        "job": job,
    }


async def run_admin_jobs(
    BRANDS,
    jobs: list[dict],
    logger=None,
):
    if logger:
        logger.info(
            f"Starting admin crawler. "
            f"brands={BRANDS}, "
            f"total_jobs={len(jobs)}"
        )
    cookies = await get_cookies_async()
    timeout = aiohttp.ClientTimeout(
        total=60,
        connect=10,
    )

    all_results = {}

    # 統計哪些 job 在任一 brand 有資料
    job_has_data = {
        job["name"]: False
        for job in jobs
    }

    # 全域 request concurrency
    global_sem = asyncio.Semaphore(20)
    async with aiohttp.ClientSession(
        cookies=cookies,
        timeout=timeout,
    ) as session:

        for brand in BRANDS:

            if logger:
                logger.info(f"Switching regulator. brand={brand}")

            await switch_regulator(session, brand)

            if logger:
                logger.info(
                    f"Regulator switched successfully. "
                    f"brand={brand}"
                )
                
            brand_jobs = []
            for job in jobs:
                job_copy = job.copy()
                job_copy["brand"] = brand
                job_copy["job_name"] = job["name"]
                brand_jobs.append(job_copy)

            if logger:
                logger.info(
                    f"Brand jobs prepared. "
                    f"brand={brand}, "
                    f"job_count={len(brand_jobs)}"
                )
            tasks = [
                fetch_job(
                    session=session,
                    job=job,
                    global_sem=global_sem,
                    logger=logger
                )
                for job in brand_jobs
            ]

            results = await asyncio.gather(*tasks)

            dfs = []
            total_rows = 0
            for r in results:
                df = r["df"]
                if not df.empty:
                    dfs.append(df)
                    total_rows += len(df)
                    job_has_data[r["job"]["job_name"]] = True
            if dfs:
                all_results[brand] = pd.concat(dfs, ignore_index=True,)
                if logger:
                    logger.info(
                        f"Brand execution completed. "
                        f"brand={brand}, "
                        f"rows={total_rows}"
                    )
            else:
                all_results[brand] = pd.DataFrame()
                if logger:
                    logger.warning(
                        f"No data returned. "
                        f"brand={brand}"
                    )

    empty_jobs = [
        job_name
        for job_name, has_data
        in job_has_data.items()
        if not has_data
    ]

    if empty_jobs and logger:
        logger.warning(
            f"Jobs returned no data across all brands. "
            f"empty_jobs={empty_jobs}"
        )

    return {
        "data": all_results,
        "empty_jobs": empty_jobs,
    }