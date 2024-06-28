import logging
import time
import requests
import json
import time
from typing import Dict, Tuple, List, Optional
from webbot import Browser
import asyncio
from pyppeteer import launch
from pyppeteer.chromium_downloader import download_chromium, chromium_executable
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager

from base_api_client import BaseAPIClient
from utils.config import KP_URL, KP_SESSION_COOKIE, KP_CONNECTION_ID

logger = logging.getLogger(__name__)


class KPAPIClient(BaseAPIClient):
    _client_cache: dict = {}

    def __init__(self, username, password):
        super().__init__(KP_URL)
        self.username = username
        self.password = password
        self.session_cookie = None
        self.session = requests.Session()

    def close_session(self):
        self.session.close()
        logger.info("Session closed.")

    @classmethod
    def get_client(cls, username, password):
        key = (username, password)
        if key in cls._client_cache:
            return cls._client_cache[key]
        client = cls(username, password)
        cls._client_cache[key] = client
        return client

    def request_session_token(self):

        # Initialize the browser
        web = Browser()

        # Open the login page
        web.go_to(KP_CONNECTION_ID)

        # Wait for the page to load (you may need to adjust the time)
        time.sleep(3)

        # Find and fill in the login form fields
        web.type(self.username, id='inputUserName')  # Replace with the actual field name if different
        web.type(self.password, id='inputPassword')  # Replace with the actual field name if different

        # Click the login button (adjust the button name/text if necessary)
        web.click('Log På')  # Replace with the actual button name if different

        # Wait for the login to process (you may need to adjust the time)
        time.sleep(2)

        # Fetch cookies
        cookies = web.driver.get_cookies()

        # Print cookies
        for cookie in cookies:
            print(cookie)

    def login_with_requests(self):
        login_url = KP_CONNECTION_ID
        payload = {
            'username': self.username,
            'password': self.password
        }

        response = self.session.post(login_url, data=payload)
        if response.status_code == 200:
            print("Login successful with requests!")
            print(self.session.cookies.get_dict())
            print(self.session)

            cookies_in_new_format = []

            # Iterate over the original dictionary and convert to the new format
            for cookie_name, cookie_value in self.session.cookies.get_dict().items():
                cookie_dict = {
                    'name': cookie_name,
                    'value': cookie_value,
                    'domain': 'adgangsstyring.stoettesystemerne.dk'
                }
                cookies_in_new_format.append(cookie_dict)
            print(cookies_in_new_format)
            return cookies_in_new_format
        else:
            print("Login failed with requests:", response.status_code)
            return None

    def perform_rpa_with_selenium(self):
        # Set up Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")

        # Initialize WebDriver
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

        try:
            # Navigate to base URL
            driver.get(self.base_url)

        finally:
            # Add a sleep to observe the behavior (optional)
            time.sleep(60)

            # Quit the WebDriver at the end
            driver.quit()

    async def perform_rpa_with_pyppeteer(self):
        # Download a specific revision of Chromium
        revision = '884014'  # Example revision that should be available
        download_chromium(revision)
        executable_path = chromium_executable(revision)

        # Launch the browser with the specified revision
        browser = await launch(executablePath=executable_path, headless=False)
        page = await browser.newPage()
        # Define the login URL
        # login_url = 'https://adfs.randers.dk/adfs/ls/?SAMLRequest=nZJBS8NAEIX%2fSth7kyYmcbMkgWIRCnqp4sHbdnfaLiazdWcC9t%2bbRjR4s95mHvve%2bxi2Xg18xC28D0AcbdaNcBZAl%2fvKZCatilzeFjKHdFfmuqoKKGy6E9ELBHIeG5HFSxFtiAbYILFGHqVlli%2bW5SIrntNSpVJlMpZVlt9I%2bSqi9VjjUPPkPjKfSCWJtnuKg0Y7xsb2bdqTjhIR3ftgYEJsxF53BCL66DukRgwBldfkSKHugRQb9bR6fFAjkToFz974TrT1xBb%2bYtJEEC5cov3mIt13sbYHjQciPgeHh5jYAzPQmRh6CAgjcJ181bT1nUfrLiF0ZWW9GqwDNLAdDxScuaiz%2bA%2biH%2bs8%2fopOZtTpyfwL2k8%3d&RelayState=24bdd1d0-f19d-42c6-9224-3855ee057946&SigAlg=http%3a%2f%2fwww.w3.org%2f2001%2f04%2fxmldsig-more%23rsa-sha256&Signature=ecHPGDxh2AqQZNb7Y%2bRcD0QiFX47QwJwwXj6qyZRzBozXNvBqHlA7Xe8nJgDQzPhw45oaU2hbm%2fWQapm5rq%2fL9JOibADyjVKsc7Mw92E%2bsVq8THw3kF090iZ3FxAVnPpwFrHAC8JKLvNEva72oCAgJHZi91chNokdiG%2bwsXV2%2f0R%2biSxXXfKbgBefMs35r9JSVg87K%2f2P3xpDqPDHLCvwGIJ%2bNCkoa%2f%2bqf5VFuoOzD4jv0Yf6t8et1n9C5mRTN9aE5Pm3YedKHnU0uUVkRu2%2b4dTkoOkhjfANnyjYt8aNwWD0HFVHbWMn22vq6cxHfvrIntW4pWwaeJj4dK99136A1STpLMeM1nzsnqUjs7okAYtYHNqb3D0UnO8M97YTv3%2b%2bD%2bFfqNQsiRkihv8KX56N%2f2F6KGiepze7PtSgkiFoOnELmejBqUAOUqYxvYEfRPJXq0NC0M1A4n4jEWmR66V%2fOvDNPhj4A9wRIpk%2fIj7aIk32I%2bsCSQ39D2H8IouowB7'

        try:
            # Navigate to the login URL
            await page.goto(KP_CONNECTION_ID)

            # Wait for the username input to be available and type the username
            await page.waitForSelector('input[name="username"]')
            await page.type('input[name="userNameInput"]', self.username)

            # Wait for the password input to be available and type the password
            await page.waitForSelector('input[name="password"]')
            await page.type('input[name="passwordInput"]', self.password)

            # Wait for the login button to be available and click it
            await page.waitForSelector('input[name="submitButton"]')
            await page.click('input[name="submitButton"]')

            # Debugging: Print the new URL and page content after login
            print(f"New URL after login: {page.url()}")
            page_content = await page.content()
            print(page_content)

        except Exception as e:
            print(f'An error occurred: {e}')

        finally:
            # Close the browser
            await browser.close()

    def authenticate(self):
        if self.session_cookie:
            return self.session_cookie
        return self.request_session_token()

    def get_auth_headers(self):

        return {"Cookie": f"JSESSIONID={KP_SESSION_COOKIE}"}


class KPClient:
    def __init__(self, username, password):
        self.api_client = KPAPIClient.get_client(username, password)

    def close_session(self):
        self.api_client.session.close()
        logger.info("Session closed.")

    def fetch_token(self):
        client = self.api_client
        # Step 1: Login with session requests
        # session_cookies = client.login_with_requests()
        # Step 2: Perform RPA tasks with Selenium using the session cookies
        # asyncio.get_event_loop().run_until_complete(client.perform_rpa_with_pyppeteer())
        return client.perform_rpa_with_selenium()


    def search_person(self, cpr: str):
        path = "rest/api/search/person"
        payload = {
            "cpr": cpr,
            "sortDirection": "",
            "sortField": ""
        }
        return self.api_client.post(path, {}, json=payload)
