import logging
import requests
import json
from typing import Dict, Tuple

from requests.auth import HTTPBasicAuth
from base_api_client import BaseAPIClient
from utils.config import KP_URL, BROWSERLESS_CLIENT_ID, BROWSERLESS_CLIENT_SECRET

logger = logging.getLogger(__name__)


class KPAPIClient(BaseAPIClient):
    _client_cache: Dict[Tuple[str, str], 'KPAPIClient'] = {}

    def __init__(self, username, password):
        super().__init__(KP_URL)
        self.username = username
        self.password = password
        self.session_cookie = None
        self.auth_attempted = False

    @classmethod
    def get_client(cls, username, password):
        key = (username, password)
        if key in cls._client_cache:
            return cls._client_cache[key]
        client = cls(username, password)
        cls._client_cache[key] = client
        return client

    def request_session_token(self):
        login_url = self.base_url
        url = "https://browserless.prototypes.randers.dk/function"
        headers = {
            "Content-Type": "application/javascript",

        }
        data = """
        module.exports = async ({page}) => {
          // Go to the specific URL
          await page.goto('""" + f"{login_url}" + """', { waitUntil: 'networkidle2' });

          // Log in console when loaded
          console.log("Page loaded");

          // Wait for the dropdown to be available
          await page.waitForSelector('#SelectedAuthenticationUrl');

          // Find the option element with the specified text
          const option = (await page.$x(
            '//*[@id = "SelectedAuthenticationUrl"]/option[contains(text(), "Randers Kommune")]'
          ))[0];

          // Check if the option was found
          if (option) {
            // Get the value attribute of the option
            const valueHandle = await option.getProperty('value');
            const value = await valueHandle.jsonValue(); // Ensure value is a string

            // Select the option by its value
            await page.select('#SelectedAuthenticationUrl', value);

            // Wait for some time after selection
            await page.waitForTimeout(2000); // Adjust the timeout as necessary

            // Click the button with class "button"
            await page.click('input.button'); // Since it's an input with class "button"

            // Log a message indicating the button was clicked
            console.log("Button clicked and navigation completed");

            // Wait for the username input field to be available
            await page.waitForSelector('#userNameInput');

            // Type the username
            await page.type('#userNameInput', '""" + f"{self.username}" + """'); // Replace with your actual username

            // Wait for the password input field to be available
            await page.waitForSelector('#passwordInput');

            // Type the password
            await page.type('#passwordInput', '""" + f"{self.password}" + """'); // Replace with your actual password

            // Click the submit button
            await page.click('#submitButton');

            // Log a message indicating the login was attempted
            console.log("Login attempted");

            // Wait for some time after selection
            await page.waitForTimeout(2000); // Adjust the timeout as necessary

            // Retrieve cookies after the login
            const cookies = await page.cookies();

            // Print the cookies
            console.log('Cookies after login:', cookies);
            return {
              data: {
                cookies
              },
              type: 'application/json'
            };
          } else {
            console.error('Option not found');
          }
        }
        """
        response = requests.post(url, headers=headers, data=data, auth=HTTPBasicAuth(username=BROWSERLESS_CLIENT_ID,
                                                                                     password=BROWSERLESS_CLIENT_SECRET))
        # Parse the JSON response
        data = json.loads(response.content)

        # Initialize session_cookie
        session_cookie = None

        # Loop through the cookies to find the JSESSIONID
        for cookie in data['cookies']:
            if cookie['name'] == 'JSESSIONID':
                session_cookie = cookie['value']
                break
        self.session_cookie = session_cookie
        return session_cookie

    def authenticate(self):
        if self.session_cookie:
            return self.session_cookie
        return self.request_session_token()

    def get_auth_headers(self):
        session_cookie = self.authenticate()
        headers = {"Cookie": f"JSESSIONID={session_cookie}"}
        return headers

    def _make_request(self, method, path, **kwargs):
        # Override _make_request to handle specific behavior for KPAPIClient
        try:
            response = super()._make_request(method, path, **kwargs)
            headers = response.get('Headers', {})
            if headers:
                content_type = headers.get('Content-Type', '')

                if 'text/html' in content_type.lower():
                    if not self.auth_attempted:
                        logger.info("Received 401 Unauthorized, attempting to fetch new session token...")
                        self.authenticate()  # Attempt to fetch new session token
                        headers = self.get_headers()  # Update headers with new session token
                        self.auth_attempted = True
                        return method(path, headers=headers, **kwargs)  # Retry the request

                    if self.auth_attempted:
                        self.auth_attempted = False
                        logger.warning("Fetching new session token failed")
            return response
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401 and self.auth_attempted is False:
                logger.info("Received 401 Unauthorized, attempting to fetch new session token...")
                self.authenticate()  # Attempt to fetch new session token
                headers = self.get_auth_headers()  # Update headers with new session token
                self.auth_attempted = True
                return method(path, headers=headers, **kwargs)  # Retry the request
            elif e.response.status_code == 401 and self.auth_attempted is True:
                self.auth_attempted = False
                logger.warning("Fetching new session token failed")
                return None


class KPClient:
    def __init__(self, username, password):
        self.api_client = KPAPIClient.get_client(username, password)

    def fetch_token(self):
        client = self.api_client
        # Step 1: Login with session requests
        # session_cookies = client.login_with_requests()
        # Step 2: Perform RPA tasks with Selenium using the session cookies
        # asyncio.get_event_loop().run_until_complete(client.perform_rpa_with_pyppeteer())
        return client.request_session_token()

    def search_person(self, cpr: str):
        path = "rest/api/search/person"
        payload = {
            "cpr": cpr,
            "sortDirection": "",
            "sortField": ""
        }
        return self.api_client.post(path, json=payload)

    def get_person(self, id: str):
        path = f"rest/api/person/overview/{id}"
        return self.api_client.get(path)

    def get_pension(self, id: str):
        path = f"rest/api/person/overview/{id}/pensionsoplysninger"
        return self.api_client.get(path)

    def get_cases(self, id: str):
        path = f"rest/api/person/overview/{id}/sager?types=aktiv"
        return self.api_client.get(path)

    def get_personal_supplement(self, id: str):
        path = f"rest/api/person/history/{id}/personligTillaegsprocent"
        response = self.api_client.get(path)
        return response

    def get_health_supplement(self, id: str):
        path = f"rest/api/person/history/{id}/helbredstillaegsprocent"
        response = self.api_client.get(path)
        return response
