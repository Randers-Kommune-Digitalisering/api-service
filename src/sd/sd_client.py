import logging
import time
import requests
import xmltodict
import json
from bs4 import BeautifulSoup
from requests.auth import HTTPBasicAuth
from typing import Dict, Tuple, Optional
from base_api_client import BaseAPIClient


logger = logging.getLogger(__name__)


# Sbsys Api Client
class SDAPIClient(BaseAPIClient):
    _client_cache: Dict[Tuple[str, str], 'SDAPIClient'] = {}

    def __init__(self, username, password, url):
        super().__init__(url)
        self.username = username
        self.password = password

    @classmethod
    def get_client(cls, username, password, url):
        key = (username, password)
        if key in cls._client_cache:
            return cls._client_cache[key]
        client = cls(username, password, url)
        cls._client_cache[key] = client
        return client

    def authenticate(self):
        return HTTPBasicAuth(self.username, self.password)

    def get_auth_headers(self):
        return {"Content-Type": "application/xml"}

    def _make_request(self, method, path, **kwargs):
        # Override _make_request to handle specific behavior for SDAPIClient
        try:
            response = super()._make_request(method, path, **kwargs)
            # Parse the HTML response to understand the closure

            soup = BeautifulSoup(response, 'html.parser')
            if not soup:
                logger.info("Received a non-HTML response that cannot be parsed for closure details.")
            else:
                title = soup.title.string if soup.title else 'No title'
                message = soup.find(id='js_txt').text if soup.find(id='js_txt') else 'No specific message found.'

                logger.info(f"API is closed. Title: {title}, Message: {message}")
            return None

        except requests.RequestException as e:
            logger.error(f"An error occurred while making the request: {e}")
            return None


class SDClient:
    def __init__(self, username, password, url):
        self.api_client = SDAPIClient.get_client(username, password, url)
        self.auth = self.api_client.authenticate()

    def get_request(self, path: str, params: Optional[Dict[str, str]] = None):
        response = self.api_client.get(path, auth=self.auth, params=params)
        if not response:
            return None
        if response.status_code == 200:
            json_data = self.xml_to_json(response.content)
            return json_data
        logger.error(f"Failed GET request with status code {response.status_code}: {response.text}")
        return None

    def post_request(self, path: str, data=None, json=None, params: Optional[Dict[str, str]] = None):
        response = self.api_client.post(path, data=data, json=json, auth=self.auth, params=params)
        if not response:
            return None
        if response.status_code == 200:
            json_data = self.xml_to_json(response.content)
            return json_data
        logger.error(f"Failed POST request with status code {response.status_code}: {response.text}")
        return None

    def put_request(self, path: str, data=None, json=None, params: Optional[Dict[str, str]] = None):
        response = self.api_client.put(path, data=data, json=json, auth=self.auth, params=params)
        if not response:
            return None
        if response.status_code == 200:
            json_data = self.xml_to_json(response.content)
            return json_data
        logger.error(f"Failed PUT request with status code {response.status_code}: {response.text}")
        return None

    def delete_request(self, path: str, params: Optional[Dict[str, str]] = None):
        response = self.api_client.delete(path, auth=self.auth, params=params)
        if not response:
            return None
        if response.status_code == 200:
            json_data = self.xml_to_json(response.content)
            return json_data
        logger.error(f"Failed DELETE request with status code {response.status_code}: {response.text}")
        return None

    def xml_to_json(self, xml_data):
        try:
            # Parse the XML data into a dictionary
            dict_data = xmltodict.parse(xml_data)
            # Convert the dictionary to a JSON string
            json_data = json.dumps(dict_data, indent=4)
            return json_data
        except Exception as e:
            logger.error(f"An error occurred while converting XML to JSON: {e}")
            return None
