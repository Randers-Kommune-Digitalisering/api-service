from nexus_client import NEXUSClient, APIClient

# Create an instance of NEXUSClient
nexus_client = NEXUSClient()


class NexusRequest:
    def __init__(self, href: str, method: str, json_body: None):
        self.href = href
        self.method = method
        self.json_body = json_body

    def __repr__(self):
        return f"NexusRequest(href={self.href}, method={self.method}, json_body={self.json_body})"

    def execute(self):
        path = self.href

        if self.method == 'GET':
            nexus_client.get_request(path)
        elif self.method == 'POST':
            nexus_client.post_request(path)
        elif self.method == 'PUT':
            nexus_client.put_request(path)
        elif self.method == 'DELETE':
            nexus_client.delete_request(path)




    def process_response(response_json):
        """Processes the JSON response. Customize this based on what you need to do with the response."""
        print("Processing response...")
        # Implement your processing logic here
        print(response_json)

