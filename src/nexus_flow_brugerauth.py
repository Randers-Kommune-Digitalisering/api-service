from nexus_request import NexusRequest, execute_nexus_flow
from nexus_client import NEXUSClient

nexus_client = NEXUSClient()

def execute_brugerauth(primary_identifier):
    professional_org_list = _fetch_professional_org_syncIds(primary_identifier)
    # active_org_list = _fetch_all_active_organisations()
    print(professional_org_list)


def _fetch_professional_org_syncIds(primary_identifier):
    # Find professional by query
    professional = nexus_client.find_professional_by_query(primary_identifier)

    # Proffesional self
    request1 = NexusRequest(input_response=professional[0], link_href="self", method="GET")

    # Proffesional organisations
    request2 = NexusRequest(link_href="organizations", method="GET")

    # Create a list of NexusRequest objects
    professional_org_request_list = [
        request1,
        request2
    ]

    # Get all assigned organisations for professional
    professional_org_list = execute_nexus_flow(professional_org_request_list)
    return _collect_syncIds_from_list(professional_org_list)


def _fetch_all_active_organisations():
    # Home resource
    home_resource = nexus_client.home_resource()

    # Active organisations
    request1 = NexusRequest(input_response=home_resource, link_href="activeOrganizationsTree", method="GET")

    # Create a list of NexusRequest objects
    active_org_request_list = [
        request1
    ]

    return _collect_syncIds_from_list(execute_nexus_flow(active_org_request_list))


def _collect_syncIds_from_list(org_list: list):
    # Collect syncIds from a list of organisations
    sync_ids = []
    for org in org_list:
        sync_ids.extend(_collect_syncIds_from_org(org))
    return sync_ids


def _collect_syncIds_from_org(org: object):
    # Recursively collects syncIds from an organization and its children
    sync_ids = []
    if 'syncId' in org and org['syncId'] is not None:
        sync_ids.append(org['syncId'])
    for child in org['children']:
        sync_ids.extend(_collect_syncIds_from_org(child))
    return sync_ids


# Example usage
if __name__ == "__main__":
    execute_brugerauth("dqb1029")
