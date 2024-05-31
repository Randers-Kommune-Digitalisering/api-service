from nexus_request import NexusRequest, execute_flow
from nexus_client import NEXUSClient

nexus_client = NEXUSClient()


def build_flow(primary_identifier):
    # Create individual NexusRequest objects
    # Find professional by query
    initial_response = nexus_client.find_professional_by_query(primary_identifier)
    request1 = NexusRequest(input_response=initial_response[0], link_href="self", method="GET")
    request2 = NexusRequest(link_href="organizations", method="GET")

    # Create a list of NexusRequest objects
    requests_list = [
        request1,
        request2
    ]

    print(execute_flow(requests_list))
