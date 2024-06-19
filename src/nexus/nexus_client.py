import logging
import time
import requests
import json


from utils.config import NEXUS_URL, NEXUS_CLIENT_ID, NEXUS_CLIENT_SECRET

logger = logging.getLogger(__name__)


# Håndtering af http request
class APIClient:
    def __init__(self, nexus_url, client_id, client_secret):
        self.nexus_url = nexus_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.access_token_expiry = None
        self.refresh_token = None
        self.refresh_token_expiry = None

    def request_access_token(self):
        # Request a new access token using client credentials
        nexus_url = f"{self.nexus_url}/authx/realms/randers/protocol/openid-connect/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        try:
            response = requests.post(nexus_url, headers=headers, data=payload)
            response.raise_for_status()
            data = response.json()
            self.access_token = data['access_token']
            self.access_token_expiry = time.time() + data['expires_in']
            self.refresh_token = data.get('refresh_token')
            self.refresh_token_expiry = time.time() + data.get('refresh_expires_in', 0)
            return self.access_token
        except requests.exceptions.RequestException as e:
            logger.error(e)
            return None

    def refresh_access_token(self):
        # Refresh the access token using the refresh token

        nexus_url = f"{self.nexus_url}/authx/realms/randers/protocol/openid-connect/token"
        payload = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        try:
            response = requests.post(nexus_url, headers=headers, data=payload)
            response.raise_for_status()
            data = response.json()
            self.access_token = data['access_token']
            self.access_token_expiry = time.time() + data['expires_in']
            self.refresh_token = data.get('refresh_token')
            self.refresh_token_expiry = time.time() + data.get('refresh_expires_in', 0)
            return self.access_token
        except requests.exceptions.RequestException as e:
            logger.error(e)
            return None

    def authenticate(self):
        # If access token is valid, return it
        if self.access_token and self.access_token_expiry and time.time() < self.access_token_expiry:
            return self.access_token
        # If refresh token is valid, try to refresh the access token
        elif self.refresh_token and self.refresh_token_expiry and time.time() < self.refresh_token_expiry:
            return self.refresh_access_token()
        # Otherwise, request a new access token using client credentials
        else:
            return self.request_access_token()

    def get_access_token(self):
        # Get a valid access token, refreshing or re-authenticating if necessary
        return self.authenticate()

    def _make_request(self, method, path, **kwargs):
        token = self.get_access_token()
        # Check if the path is a full URL
        if path.startswith("http://") or path.startswith("https://"):
            url = path
        else:
            url = f"{self.nexus_url}/{path}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            response = method(url, headers=headers, **kwargs)
            response.raise_for_status()

            try:
                return response.json()
            except json.JSONDecodeError:
                # If the response is empty, return 'success'
                if not response.content:
                    return 'success'
                # If the response is not JSON, return the response content directly
                return response.content

        except requests.exceptions.RequestException as e:
            logger.error(e)
            if response.content:
                logger.error(response.content)
            return None

    def get(self, path):
        return self._make_request(requests.get, path)

    def post(self, path, data=None, json=None):
        return self._make_request(requests.post, path, data=data, json=json)

    def put(self, path, data=None, json=None):
        return self._make_request(requests.put, path, data=data, json=json)

    def delete(self, path):
        return self._make_request(requests.delete, path)


# Nexus client requests
class NEXUSClient:
    def __init__(self):
        self.api_client = APIClient(NEXUS_URL, NEXUS_CLIENT_ID, NEXUS_CLIENT_SECRET)

    def home_resource(self):
        path = "api/core/mobile/randers/v2/"
        return self.api_client.get(path)

    def find_professional_by_query(self, query):
        path = "api/core/mobile/randers/v2/professionals/?query=" + query
        return self.api_client.get(path)

    def get_request(self, path):
        return self.api_client.get(path)

    def post_request(self, path, data=None, json=None):
        return self.api_client.post(path, data=data, json=json)

    def put_request(self, path, data=None, json=None):
        return self.api_client.put(path, data=data, json=json)

    def delete_request(self, path):
        return self.api_client.delete(path)
