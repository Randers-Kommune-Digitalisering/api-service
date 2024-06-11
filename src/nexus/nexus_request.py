from typing import List, Optional
from nexus.nexus_client import NEXUSClient


# Create an instance of NEXUSClient
nexus_client = NEXUSClient()


class NexusRequest:
    def __init__(self, method: str, link_href: str = None, href_custom: list = None,
                 input_response: Optional[dict] = None, json_body: Optional[dict] = None,
                 params: Optional[dict] = None):
        self.input_response = input_response
        self.link_href = link_href
        self.method = method
        self.json_body = json_body
        self.href_custom = href_custom
        self.params = params

    def __repr__(self):
        return f"NexusRequest(href={self.link_href}, method={self.method}, json_body={self.json_body})"

    def execute(self, input_response):
        final_url = None

        # Parse the key from the constructor's input response using link_href
        if self.input_response and '_links' in self.input_response and self.link_href in self.input_response['_links']:
            final_url = self.input_response['_links'][self.link_href]['href']

        # Parse the key from the constructor's input response using href_custom
        elif self.input_response and self.href_custom:
            final_url = self._get_nested_value(self.input_response, self.href_custom)
            print("Extracted URL from href_custom:", final_url)

        # Parse the key from the formal parameter input response using link_href
        elif input_response and '_links' in input_response and self.link_href in input_response['_links']:
            final_url = input_response['_links'][self.link_href]['href']

        # Parse the key from the formal parameter input response using href_custom
        elif input_response and self.href_custom:
            final_url = self._get_nested_value(input_response, self.href_custom)
            print("Extracted URL from href_custom:", final_url)

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
            response = nexus_client.post_request(final_url, data=self.json_body)
        elif self.method == 'PUT':
            response = nexus_client.put_request(final_url, data=self.json_body)
        elif self.method == 'DELETE':
            response = nexus_client.delete_request(final_url)
        else:
            raise ValueError(f"Unsupported method: {self.method}")

        return response

    def _get_nested_value(self, data, keys):
        """Recursively get nested value from a dictionary using a list of keys."""
        for key in keys:
            if isinstance(data, dict) and key in data:
                data = data[key]
            else:
                return None
        return data

    def process_response(self, response_json, nexus_request):
        """Processes the JSON response. Customize this based on what you need to do with the response."""
        # print("Processing " +  nexus_request.link_href)


def execute_nexus_flow(list_of_requests: List[NexusRequest]):
    cur_response = None
    for request in list_of_requests:
        response = request.execute(cur_response)
        request.process_response(response, request)
        cur_response = response
    return cur_response
