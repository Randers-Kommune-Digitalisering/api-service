from typing import List, Optional
from nexus.nexus_client import NEXUSClient


# Create an instance of NEXUSClient
nexus_client = NEXUSClient()


class NexusRequest:
    def __init__(self, link_href: str, method: str, input_response: Optional[dict] = None, json_body: Optional[dict] = None):
        self.input_response = input_response
        self.link_href = link_href
        self.method = method
        self.json_body = json_body

    def __repr__(self):
        return f"NexusRequest(href={self.link_href}, method={self.method}, json_body={self.json_body})"

    def execute(self, input_response):

        # Parse the key from the constructors input response
        if self.input_response and '_links' in self.input_response and self.link_href in self.input_response['_links']:
            final_url = self.input_response['_links'][self.link_href]['href']

        # Parse the key from the formal parameter input response
        elif input_response and '_links' in input_response and self.link_href in input_response['_links']:
            final_url = input_response['_links'][self.link_href]['href']

        else:
            raise ValueError(f"Link '{self.link_href}' not found in the response")

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

    def process_response(self, response_json):
        """Processes the JSON response. Customize this based on what you need to do with the response."""
        # print("Processing " +  + " response...")


def execute_nexus_flow(list_of_requests: List[NexusRequest]):
    cur_response = None
    for request in list_of_requests:
        response = request.execute(cur_response)
        request.process_response(response)
        cur_response = response
    return cur_response
