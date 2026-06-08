from pathlib import Path
import hashlib 
import pyotp 
import aiohttp 
import asyncio


# Login
async def login_and_get_token(
    account: str,
    password: str,
    setup_key: str,
    max_retry: int = 5,
) -> dict :

    headers = {
        "user-agent": "Mozilla/5.0",
    }

    password_hash = hashlib.md5(password.encode()).hexdigest()
    timeout = aiohttp.ClientTimeout(
        total=30,
        connect=10,
    )

    last_error = None
    async with aiohttp.ClientSession(
        headers=headers,
        timeout=timeout,
    ) as session:

        for attempt in range(1, max_retry + 1):

            try:

                # TOTP
                totp = pyotp.TOTP(setup_key)
                totp_code = totp.now()

                async with session.post(
                    "https://admin.vantagemarkets.com/login/to_login",
                    data={
                        "userName_login": account,
                        "password_login": password_hash,
                        "twoFactorType": "googleAuth",
                        "googleAuthTotp": totp_code,
                    },
                    allow_redirects=True,
                ) as response:

                    # HTTP status
                    if response.status != 200:
                        last_error = f"HTTP {response.status}"
                        await asyncio.sleep(2)
                        continue

                    # redirected back to login
                    if "login" in str(response.url).lower():
                        last_error = "被導回 login 頁面（可能帳密/TOTP/風控）"
                        await asyncio.sleep(2)
                        continue

                    # print("✅ Login success")

                    cookies = {
                        cookie.key: cookie.value
                        for cookie in session.cookie_jar
                    }

                    return cookies

            except aiohttp.ClientError as e:
                last_error = f"登入請求失敗: {e}"
                await asyncio.sleep(2)

            except asyncio.TimeoutError:
                last_error = "Request timeout"
                await asyncio.sleep(2)

        raise RuntimeError(
            f"❌ 登入失敗（已重試 {max_retry} 次）：{last_error}"
        )

# Env
def load_env_file(path):
    env = {}
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            key, value = line.split('=', 1)
            env[key.strip()] = value.strip()
    return env



is_docker = (Path("/.dockerenv").exists() or Path("/run/.containerenv").exists())
credentials = load_env_file(r"/run/secrets/credentials.env" if is_docker else r"C:/Users/peter.chang/credentials.env")
async def get_cookies_async():
    return await login_and_get_token(
        account  = credentials.get('crm_account1',''),
        password = credentials.get('crm_password1',''),
        setup_key= credentials.get('crm_setup_key1','')
    )

