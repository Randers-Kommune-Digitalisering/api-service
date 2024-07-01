import logging
import time
import requests
from typing import Dict, Tuple, List, Optional
from base_api_client import BaseAPIClient
from utils.config import NEXUS_URL, NEXUS_CLIENT_ID, NEXUS_CLIENT_SECRET

logger = logging.getLogger(__name__)


# Nexus api client
class NexusAPIClient(BaseAPIClient):
    _client_cache: Dict[Tuple[str, str], 'NexusAPIClient'] = {}

    def __init__(self, client_id, client_secret):
        super().__init__(NEXUS_URL)
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.access_token_expiry = None
        self.refresh_token = None
        self.refresh_token_expiry = None

    @classmethod
    def get_client(cls, client_id, client_secret):
        key = (client_id, client_secret)
        if key in cls._client_cache:
            return cls._client_cache[key]
        client = cls(client_id, client_secret)
        cls._client_cache[key] = client
        return client

    def request_access_token(self):
        token_url = f"{self.base_url}/authx/realms/randers/protocol/openid-connect/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        try:
            response = requests.post(token_url, headers=headers, data=payload)
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
        token_url = f"{self.base_url}/authx/realms/randers/protocol/openid-connect/token"
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
            response = requests.post(token_url, headers=headers, data=payload)
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
        if self.access_token and self.access_token_expiry and time.time() < self.access_token_expiry:
            return self.access_token
        elif self.refresh_token and self.refresh_token_expiry and time.time() < self.refresh_token_expiry:
            return self.refresh_access_token()
        else:
            return self.request_access_token()

    def get_access_token(self):
        return self.authenticate()

    def get_auth_headers(self):
        token = self.get_access_token()
        return {"Authorization": f"Bearer {token}"}


# Nexus client
class NexusClient:
    def __init__(self, client_id, client_secret):
        self.api_client = NexusAPIClient.get_client(client_id, client_secret)

    def home_resource(self):
        path = "api/core/mobile/randers/v2/"
        return self.get_request(path)

    def find_professional_by_query(self, query):
        path = "api/core/mobile/randers/v2/professionals/?query=" + query
        return self.get_request(path)

    def find_patient_by_query(self, query):
        path = "api/core/mobile/randers/v2/patients/?query=" + query
        return self.api_client.get(path)

    def fetch_patient_by_query(self, query):
        try:
            patient_search = self.find_patient_by_query(query=query)
            if not patient_search['pages']:
                logger.info(f"No patients found for query: {query}")
                return None

            patient_link = patient_search['pages'][0]['_links']['patientData']['href']
            patient_response = self.get_request(path=patient_link)

            if not patient_response:
                logger.info(f"No patient data found at link: {patient_link}")
                return None

            self_path = patient_response[0]['_links']['self']['href']
            patient_self_response = self.get_request(self_path)

            return patient_self_response
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None
        except KeyError as e:
            logger.error(f"Unexpected response structure: {e}")
            return None

    def fetch_borgerkalender(self, patient):
        # Fetch patient preferences
        request1 = NexusRequest(input_response=patient,
                                link_href="patientPreferences",
                                method="GET")

        # Execute Patient preferences
        patient_preferences = execute_nexus_flow([request1])

        # Fetch patient list of CITIZEN_CALENDAR
        citizen_calender_list = patient_preferences['CITIZEN_CALENDAR']

        # Find the object with name "Borgerkalender"
        borgerkalender = next((item for item in citizen_calender_list
                               if item.get('name') == 'Borgerkalender'), None)

        # Fetch CITIZEN_CALENDAR self
        request1 = NexusRequest(input_response=borgerkalender,
                                link_href="self",
                                method="GET")
        return execute_nexus_flow([request1])

    def get_request(self, path):
        return self.api_client.get(path)

    def post_request(self, path, data=None, json=None):
        return self.api_client.post(path,data, json)

    def put_request(self, path, data=None, json=None):
        return self.api_client.put(path, data, json)

    def delete_request(self, path):
        return self.api_client.delete(path)


# Create an instance of NEXUSClient
nexus_client = NexusClient(NEXUS_CLIENT_ID, NEXUS_CLIENT_SECRET)


class NexusRequest:
    def __init__(self, method: str, link_href: str = None, link_full: list = None,
                 input_response: Optional[dict] = None, payload: Optional[dict] = None,
                 params: Optional[dict] = None):
        self.input_response = input_response
        self.link_href = link_href
        self.method = method
        self.payload = payload
        self.link_full = link_full
        self.params = params

    def __repr__(self):
        return f"NexusRequest(href={self.link_href}, method={self.method}, json_body={self.payload})"

    def execute(self, input_response):
        final_url = None

        # Parse the key from the constructor's input response using link_href
        if self.input_response and '_links' in self.input_response and self.link_href in self.input_response['_links']:
            final_url = self.input_response['_links'][self.link_href]['href']

        # Parse the key from the constructor's input response using link_full
        elif self.input_response and self.link_full:
            final_url = self._get_nested_value(self.input_response, self.link_full)
            print("Extracted URL from link_full:", final_url)

        # Parse the key from the formal parameter input response using link_href
        elif input_response and '_links' in input_response and self.link_href in input_response['_links']:
            final_url = input_response['_links'][self.link_href]['href']

        # Parse the key from the formal parameter input response using link_full
        elif input_response and self.link_full:
            final_url = self._get_nested_value(input_response, self.link_full)
            print("Extracted URL from link_full:", final_url)

        if not final_url:
            raise ValueError(f"Link '{self.link_href}' not found in the response")

        if not isinstance(final_url, str):
            raise ValueError(f"Final URL is not a string: {final_url}")

        # Handle URL parameters
        if self.params:
            final_url += '?' + '&'.join([f"{key}={value}" for key, value in self.params.items()])

        if self.method == 'GET':
            response = nexus_client.get_request(final_url)
        elif self.method == 'POST':
            response = nexus_client.post_request(final_url, json=self.payload)
        elif self.method == 'PUT':
            response = nexus_client.put_request(final_url, json=self.payload)
        elif self.method == 'DELETE':
            response = nexus_client.delete_request(final_url)
        else:
            raise ValueError(f"Unsupported method: {self.method}")

        return response

    def _get_nested_value(self, data, keys):
        # Recursively get nested value from a dictionary using a list of keys.
        for key in keys:
            if isinstance(data, dict) and key in data:
                data = data[key]
            else:
                return None
        return data

    def process_response(self, response_json, nexus_request):
        return
        # print("Processing " +  nexus_request.link_href)


def execute_nexus_flow(list_of_requests: List[NexusRequest]):
    cur_response = None
    for request in list_of_requests:
        response = request.execute(cur_response)
        request.process_response(response, request)
        cur_response = response
    return cur_response
