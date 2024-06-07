import logging

from nexus_request import NexusRequest, execute_nexus_flow
from nexus_client import NEXUSClient

logger = logging.getLogger(__name__)
nexus_client = NEXUSClient()

active_org_list = []


def update_nexus_organisation_list():
    global active_org_list

    # Get all organisations as list of tuples - [0] being id, [1] being uuid
    active_org_list = _fetch_all_active_organisations()
    # logger.info(active_org_list)


def execute_brugerauth(primary_identifier: str, input_organisation_uuid_list: list):
    professional = _fetch_professional(primary_identifier)
    if not professional:
        return

    # Get all assigned organisations for professional as list of tuples - [0] being id, [1] being uuid
    professional_org_list = _fetch_professional_org_syncIds(professional)
    logger.info("Professional current organisation:")
    logger.info(professional_org_list)

    # uuids from active_org_list not found in input_organisation_uuid_list
    unassigned_organisation_ids = [item[0] for item in active_org_list if item[1] in input_organisation_uuid_list]

    if len(unassigned_organisation_ids) == 0:
        return

    # Filter out IDs present in professional_org_list
    unassigned_organisation_ids = [org_id for org_id in unassigned_organisation_ids if org_id not in [item[0] for item in professional_org_list]]
    if len(unassigned_organisation_ids) == 0:
        return

    # Remove duplicates
    unassigned_organisation_ids = list(set(unassigned_organisation_ids))
    logger.info("Professional unassigned organisation:")
    logger.info(unassigned_organisation_ids)

    # Update the organisations for the professional
    result = _update_professional_organisations(professional, unassigned_organisation_ids)
    if result:
        logger.info("success " + result)


def _fetch_professional(primary_identifier):
    # Find professional by query
    if len(nexus_client.find_professional_by_query(primary_identifier)) > 0:
        return nexus_client.find_professional_by_query(primary_identifier)[0]


def _update_professional_organisations(professional, organisation_id_list):
    # Proffesional self
    request1 = NexusRequest(input_response=professional, link_href="self", method="GET")

    # json body with the list of organisation ids that should be added to the professional
    json_body = {
        "added": organisation_id_list,
        "removed": []
    }

    # Proffesional organisations
    request2 = NexusRequest(link_href="updateOrganizations", method="POST", json_body=json_body)

    # Create a list of NexusRequest objects
    professional_org_change_request_list = [
        request1,
        request2
    ]

    # Get all assigned organisations for professional
    professional_org_change_list = execute_nexus_flow(professional_org_change_request_list)
    return professional_org_change_list


def _fetch_professional_org_syncIds(professional):
    # Proffesional self
    request1 = NexusRequest(input_response=professional, link_href="self", method="GET")

    # Proffesional organisations
    request2 = NexusRequest(link_href="organizations", method="GET")

    # Create a list of NexusRequest objects
    professional_org_request_list = [
        request1,
        request2
    ]

    # Get all assigned organisations for professional
    professional_org_list = execute_nexus_flow(professional_org_request_list)
    return _collect_syncIds_from_list_or_org(professional_org_list)


def _fetch_all_active_organisations():
    # Home resource
    home_resource = nexus_client.home_resource()

    # Active organisations
    request1 = NexusRequest(input_response=home_resource, link_href="activeOrganizationsTree", method="GET")

    # Create a list of NexusRequest objects
    active_org_request_list = [
        request1
    ]

    all_active_organisations = execute_nexus_flow(active_org_request_list)
    return _collect_syncIds_from_list_or_org(all_active_organisations)


def _collect_syncIds_from_list_or_org(org_input):
    # Collect syncIds from a list of organizations or a single organization.

    if not isinstance(org_input, list):
        org_input = [org_input]  # Wrap the single organization in a list

    return _collect_syncIds_from_list(org_input)


def _collect_syncIds_from_list(org_list: list):
    # Collect syncIds from a list of organizations.

    sync_ids = []
    for org in org_list:
        sync_ids.extend(_collect_syncIds_and_ids_from_org(org))
    return sync_ids


def _collect_syncIds_and_ids_from_org(org: object):
    # Recursively collects syncIds and ids from an organization and its children.
    sync_ids_and_ids = []
    if isinstance(org, dict):
        if 'syncId' in org and org['syncId'] is not None:
            sync_ids_and_ids.append((org['id'], org['syncId']))
        for child in org.get('children', []):
            sync_ids_and_ids.extend(_collect_syncIds_and_ids_from_org(child))
    else:
        logger.info(f"Unexpected type for org: {type(org)}")
    return sync_ids_and_ids


# Example usage
# if __name__ == "__main__":
#    update_nexus_organisation_list()
#    execute_brugerauth("dqb1029", ['bb29e529-06a8-47e7-abe7-8fab6824dbf9'])
