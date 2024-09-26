import json
import logging
from abc import ABC, abstractmethod
import requests

logger = logging.getLogger(__name__)


# Abstract base api client class
class BaseAPIClient(ABC):
    def __init__(self, base_url):
        self.base_url = base_url

    @abstractmethod
    def get_auth_headers(self):
        pass

    def _make_request(self, method, path, **kwargs):
        headers = self.get_auth_headers()

        if path.startswith("http://") or path.startswith("https://"):
            url = path
        else:
            url = f"{self.base_url}/{path}"

        try:
            response = method(url, headers=headers, **kwargs)
            response.raise_for_status()

            try:
                response_data = response.json()
                # if isinstance(response_data, list):
                #     return {"results": response_data}
                return response_data

            except json.JSONDecodeError:
                if not response.content:
                    return 'success'
                return response.content

        except requests.exceptions.RequestException as e:
            logger.error(e)
            # if response.content:
            #    logger.error(response.content)
            return None

    def get(self, path, **kwargs):
        return self._make_request(requests.get, path, **kwargs)

    def post(self, path, data=None, json=None, **kwargs):
        return self._make_request(requests.post, path, data=data, json=json, **kwargs)

    def post_upload(self, path, data=None, files=None):
        return self._make_request(requests.post, path, data=data, files=files)

    def put(self, path, data=None, json=None, **kwargs):
        return self._make_request(requests.put, path, data=data, json=json, **kwargs)

    def delete(self, path, **kwargs):
        return self._make_request(requests.delete, path, **kwargs)
