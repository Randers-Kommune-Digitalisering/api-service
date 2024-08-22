import logging
import time
import requests
from typing import Dict, Tuple
from base_api_client import BaseAPIClient
from utils.config import SBSIP_URL

logger = logging.getLogger(__name__)


# Sbsys Api Client
class SbsysAPIClient(BaseAPIClient):
    _client_cache: Dict[Tuple[str, str, str, str], 'SbsysAPIClient'] = {}

    def __init__(self, client_id, client_secret, username, password, url):
        super().__init__(url)
        self.client_id = client_id
        self.client_secret = client_secret
        self.username = username
        self.password = password
        self.access_token = None
        self.access_token_expiry = None
        self.refresh_token = None
        self.refresh_token_expiry = None

    @classmethod
    def get_client(cls, client_id, client_secret, username, password, url):
        key = (client_id, client_secret, username, password)
        if key in cls._client_cache:
            return cls._client_cache[key]
        client = cls(client_id, client_secret, username, password, url)
        cls._client_cache[key] = client
        return client

    def request_access_token(self):
        token_url = f"{SBSIP_URL}/auth/realms/sbsip/protocol/openid-connect/token"
        payload = {
            "grant_type": "password",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": self.username,
            "password": self.password
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        try:
            if not token_url.startswith("https://"):
                token_url = "https://" + token_url
            response = requests.post(token_url, headers=headers, data=payload, timeout=20)
            response.raise_for_status()
            data = response.json()
            self.access_token = data['access_token']
            self.access_token_expiry = time.time() + data['expires_in']
            return self.access_token
        except requests.exceptions.RequestException as e:
            logger.error(e)
            return None

    def authenticate(self):
        if self.access_token and self.access_token_expiry and time.time() < self.access_token_expiry:
            return self.access_token
        else:
            return self.request_access_token()

    def get_access_token(self):
        return self.authenticate()

    def get_auth_headers(self):
        token = "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICIyZlR0cW5Hamo3M082bElzUmZDdlp4WHYtNjVva0I3WFZDNERRT2JnT3ZNIn0.eyJqdGkiOiIwOGRiNGE5ZC01MGE3LTQwNWUtYjk5Zi03M2RiZjRlNTJjNmQiLCJleHAiOjE3MjQzOTM5NTYsIm5iZiI6MCwiaWF0IjoxNzI0MzY1MTU2LCJpc3MiOiJodHRwczovL3Nic2lwLXdlYi1kcmlmdDAxLnJhbmRlcnMuZGs6ODU0My9hdXRoL3JlYWxtcy9zYnNpcCIsImF1ZCI6InJhbmRlcnMtdWR2aWtsaW5nLWtsaWVudCIsInN1YiI6IjFkODFiYWVhLWZmODMtNGZjMC04YjNhLWIzMjhmYjIyMmE3NiIsInR5cCI6IkJlYXJlciIsImF6cCI6InJhbmRlcnMtdWR2aWtsaW5nLWtsaWVudCIsImF1dGhfdGltZSI6MCwic2Vzc2lvbl9zdGF0ZSI6IjVlZGExNzUzLWI1NjgtNDE0MC04YjA5LTMyNDdjYzNkZDk0MyIsImFjciI6IjEiLCJjbGllbnRfc2Vzc2lvbiI6IjE5MTg5M2I2LTMxNzQtNDljZS1iM2EwLWY0MTk0MDRjZmNhNSIsImFsbG93ZWQtb3JpZ2lucyI6W10sInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJjb252ZXJnZW5zLXNic2lwLW1vZHRhZ2VybW9kdWwtZGlnaXRhbHBvc3QtbWVtb35vdXQtY2hhbm5lbC11c2VyIiwiY29udmVyZ2Vucy1zYnNpcC1wdWJsaWNkYXRhfmFkbWluIiwicHVibGljZGF0YX5jdnIiLCJwdWJsaWNkYXRhfnN5Z2VzaWtyaW5nIiwidW1hX2F1dGhvcml6YXRpb24iLCJwdWJsaWNkYXRhfmRpZ2l0YWxwb3N0Il19LCJyZXNvdXJjZV9hY2Nlc3MiOnsiYWNjb3VudCI6eyJyb2xlcyI6WyJtYW5hZ2UtYWNjb3VudCIsIm1hbmFnZS1hY2NvdW50LWxpbmtzIiwidmlldy1wcm9maWxlIl19fSwiYXVkIjoic2JzeXNhcGkucmFuZGVycy5kazo0NDMiLCJuYW1lIjoiIiwicHJlZmVycmVkX3VzZXJuYW1lIjoia29yc2VsIn0.ARty8L05eAg7twYaETYHwI57UkPPrMzKOkL2AAnXMehW_e2js6aUhcHD6U6MkCeBkgZ43awpOoLp4-4xnjhhZS0nbUPge_Ej9UrHCtPpS6pyojAF0R41I8IZVsawkzr_yTUfRRGs2Izp_wp3IcxfVMgzCwVGEskc4gI_DDuGw0cxcFmf9oI2JJl2ySWVpRRktAx7c9UDZSKZItXHy9_HJzpEEunginaguk9kEGWrn2EEhUKaT93Frl4AAlwbJn2-3zND_xh66c6cpQyajbsPc8wOMQ-zkDNx7008wIdM9EVHzuy-HgwkmQMX25ckIvyryIzeEglEQRfsTHTmN9T3rg"
        return {"Content-Type": "application/json",
                "Authorization": f"Bearer {token}"}


class SbsysClient:
    def __init__(self, client_id, client_secret, username, password, url):
        self.api_client = SbsysAPIClient.get_client(client_id, client_secret, username, password, url)

    def sag_search(self, payload):
        path = "api/sag/search"
        return self.api_client.post(path=path, json=payload)

    def fetch_documents(self, sag_id):
        path = f"api/sag/{sag_id}/dokumenter"
        return self.api_client.get(path=path)

    def fetch_file(self, file_id):
        path = f"/api/fil/{file_id}"
        return self.api_client.get(path=path)

    def get_request(self, path):
        return self.api_client.get(path)

    def post_request(self, path, data=None, json=None):
        return self.api_client.post(path, data, json)

    def put_request(self, path, data=None, json=None):
        return self.api_client.put(path, data, json)

    def delete_request(self, path):
        return self.api_client.delete(path)
