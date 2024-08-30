import re
import logging
from datetime import datetime, timezone, timedelta
from dateutil.parser import parse
from unidecode import unidecode

from nexus.nexus_client import NexusClient, NexusRequest, execute_nexus_flow
from utils.config import NEXUS_CLIENT_ID, NEXUS_CLIENT_SECRET, NEXUS_URL

logger = logging.getLogger(__name__)
nexus_client = NexusClient(NEXUS_CLIENT_ID, NEXUS_CLIENT_SECRET, NEXUS_URL)

afslutning_af_borger_dashboard_id = 6866
doede_borgere_med_aktive_forloeb_list_id = 5029
hours_elapsed_before_handling = 48

do_not_delete = ['54', '94', '95.3', '112', '114', '116', '118', '119']


def job():
    try:
        logger.info("Starting Nexus Flow Lukning job")
        if iterate_dead_list():
            logger.info("Successfully finished Nexus Flow Lukning job")
            return True
        else:
            logger.error("Failed to finish Nexus Flow Lukning job")
            return False
    except Exception as e:
        logger.error(f"Error in job: {e}")


def iterate_dead_list():
    try:
        home = nexus_client.home_resource()
        request1 = NexusRequest(input_response=home, link_href="preferences", method="GET")

        # Get available lists for client
        available_lists = execute_nexus_flow([request1])

        # Find the list of dead patients by id
        dead_list_preference = next((li for li in available_lists['CITIZEN_LIST'] if li['id'] == doede_borgere_med_aktive_forloeb_list_id), None)

        if dead_list_preference:
            request1 = NexusRequest(input_response=dead_list_preference, link_href="self", method="GET")

            request2 = NexusRequest(link_href="content", method="GET")

            dead_list_content = execute_nexus_flow([request1, request2])

            if len(dead_list_content['pages']) > 0:
                for page in dead_list_content['pages']:
                    request1 = NexusRequest(input_response=page, link_href="patientData", method="GET")
                    current_page = execute_nexus_flow([request1])
                    for entry in current_page:
                        if entry['id'] == 1:
                            # Check state is correct
                            if entry.get('patientState', {}).get('type', {}).get('id', '').upper() == 'DEAD':
                                request2 = NexusRequest(input_response=entry, link_href="self", method="GET")
                                patient = execute_nexus_flow([request2])
                                request3 = NexusRequest(input_response=patient, link_href="audit", method="GET")
                                patient_changes = execute_nexus_flow([request3])
                                # Find the the latest change to current state and get the datetime
                                time_set_dead_last = max([x for x in patient_changes['auditEntries'] if x['type'] == 'CHANGE' and next((y for y in x['changes'] if y.get('translation', {}).get('keyName', '').upper() == 'BORGERSTATUS' and y.get('translation', {}).get('newValue', '').upper() == 'DØD'), None)], key=lambda c: c["date"], default={}).get("date", None)
                                if time_set_dead_last:
                                    now = datetime.now(timezone.utc)
                                    if (now - parse(time_set_dead_last)) > timedelta(hours=hours_elapsed_before_handling):
                                        if execute_lukning(patient):
                                            logger.info(f"Patient {entry['id']} has been closed")
                                        else:
                                            logger.warn(f"Patient {entry['id']} could not be closed")
                                    else:
                                        logger.info(f"Patient {entry['id']} has changed state less than {hours_elapsed_before_handling} hours ago - skipping")
                                else:
                                    logger.warn(f"Patient {entry['id']} has no state changed to dead, cannot check time - skipping")
                            else:
                                logger.warn(f"Patient {entry['id']} is not in dead state - skipping")
                logger.info(f"Finished iterating list id: {doede_borgere_med_aktive_forloeb_list_id}")
                return True
            else:
                logger.info(f"List id: {doede_borgere_med_aktive_forloeb_list_id} is empty - nothing to do")
                return True
        else:
            logger.error(f"List id: {doede_borgere_med_aktive_forloeb_list_id} not found")
    except Exception as e:
        logger.error(f"Error iterating dead list: {e}")


def execute_lukning(patient=None):
    try:
        # Find patient by CPR
        # patient = nexus_client.fetch_patient_by_query(query=cpr)
        if not patient:
            logger.error("Patient not found.")
            return
        dashboard = nexus_client.fetch_dashboard(patient, afslutning_af_borger_dashboard_id)
        if not dashboard:
            logger.error("Dashboard not found.")
            return

        _cancel_events(patient)  # Afslut alle besøg fra kalenderen
        _set_conditions_inactive(patient)  # Tilstande afslutning af borgee
        _set_pathways_inactive(patient)  # "Alle borgers Handlingsanvisninger" + "Skemaer - afslutning af borger" Sætter alle til inaktive
        remove_fsiii_indsatser(patient)  # "Indsatser - FSIII" Afslutter indsatser - TODO: 'annuller' is still missing - fix
        # _remove_patient_grants([2298969])

    except Exception as e:
        logger.error(f"Error in job: {e}")


def _cancel_events(patient):
    try:
        borgerkalender = nexus_client.fetch_borgerkalender(patient)
        # Create a dictionary with stopDate as the current datetime
        current_datetime = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        stop_date_dict = {"stopDate": current_datetime}

        # Fetch events to stop
        request1 = NexusRequest(input_response=borgerkalender,
                                link_href="getEventsToStop",
                                method="GET",
                                params=stop_date_dict)

        # Execute events_list
        events_list = execute_nexus_flow([request1])

        # Save ids of upcoming events
        event_ids = [event['event']['id'] for event in events_list['events']]

        # If list is empty, stopEvents request will time out
        if not event_ids:
            logger.info("No events to cancel.")
            return

        # Cancel events request
        request1 = NexusRequest(input_response=events_list,
                                link_href="stopEvents",
                                method="POST",
                                payload=event_ids)

        # Execute cancel events
        response = execute_nexus_flow([request1])
        logger.info("Events cancelled")
        return response

    except Exception as e:
        logger.error(f"Error cancelling events: {e}")


def _set_conditions_inactive(patient):
    try:
        active_condition_id = 28748
        inactive_condition_id = 28747

        # Fetch patient conditions
        request1 = NexusRequest(input_response=patient,
                                link_href="patientConditions",
                                method="GET")

        # Execute patient conditions
        patient_conditions = execute_nexus_flow([request1])

        # Save ids of active conditions
        active_conditions = [item for item in patient_conditions if
                             item['id'] and item['state']['id'] == active_condition_id]
        active_conditions_ids = [item['id'] for item in active_conditions]
        logger.info("Active condition IDs: %s", active_conditions_ids)

        if not active_conditions_ids:
            logger.info("No active conditions found.")
            return

        # Convert list of ids to a comma-separated string
        condition_ids_str = ','.join(map(str, active_conditions_ids))
        params = {"conditionIds": condition_ids_str}

        # Create bulk prototype
        request1 = NexusRequest(input_response=patient,
                                link_href="conditionsBulkPrototype",
                                method="GET",
                                params=params)

        # Execute conditions bulk prototype
        conditions_bulk_prototype = execute_nexus_flow([request1])

        if conditions_bulk_prototype is None:
            logger.error("Failed to retrieve conditions bulk prototype.")
            return

        # Prepare payload with state set to inactive
        inactive_state = next(
            (state for state in conditions_bulk_prototype['state']['possibleValues']
             if state['id'] == inactive_condition_id), None)

        if inactive_state is None:
            logger.error("Inactive state not found.")
            return

        # Set state to inactive
        conditions_bulk_prototype['state']['value'] = inactive_state

        # Create new condition observation - observation state set to inactive
        request1 = NexusRequest(input_response=conditions_bulk_prototype,
                                link_href="create",
                                method="POST",
                                payload=conditions_bulk_prototype)

        # Execute condition observation - active conditions are set to inactive
        response = execute_nexus_flow([request1])
        logger.info("Conditions set to inactive")
        return response

    except Exception as e:
        logger.error(f"Error setting conditions inactive: {e}")


def _set_pathways_inactive(dashboard):
    try:
        pathway_collection_header_title = ["Alle borgers Handlingsanvisninger", "Skemaer - afslutning af borger"]
        set_pathway_inactive_action_id = [30504, 37102]
        exclude_pathway_names = ["Akutkald"]

        # Fetch the pathway collection matching the header title
        patient_pathway_collection = [item for item in dashboard['view']['widgets'] if
                                      item['headerTitle'] in pathway_collection_header_title]

        if not patient_pathway_collection:
            logger.error("No pathway collections matching the header titles found.")
            return False

        # Iterate over the pathway collection, and find pathway references
        for pathway in patient_pathway_collection:

            # Check if the pathway has patient activities
            if 'patientActivities' in pathway['_links']:
                # Patient activities
                request1 = NexusRequest(input_response=pathway,
                                        link_href="patientActivities",
                                        method="GET")
                patient_activities = execute_nexus_flow([request1])

                # Iterate over patient activities, and set status to inactive
                for activity in patient_activities:
                    # activity self
                    request1 = NexusRequest(input_response=activity,
                                            link_href="self",
                                            method="GET")
                    activity_self = execute_nexus_flow([request1])

                    request1 = NexusRequest(input_response=activity_self,
                                            link_href="availableActions",
                                            method="GET")

                    available_actions = execute_nexus_flow([request1])

                    # Fetch the inactive action object
                    inactive_action = next(item for item in available_actions
                                           if item['id'] in set_pathway_inactive_action_id)
                    request1 = NexusRequest(input_response=inactive_action,
                                            link_href="updateFormData",
                                            method="PUT", payload=activity_self)
                    execute_nexus_flow([request1])

            # Pathway reference
            request1 = NexusRequest(input_response=pathway,
                                    link_href="pathwayReferences",
                                    method="GET")
            pathway_references = execute_nexus_flow([request1])

            # Iterate over the pathway references, and set status to inactive
            for reference in pathway_references:
                # Skip pathway that should not be set inactive
                if reference['name'] in exclude_pathway_names:
                    logger.info(f"Skipping pathway: {reference['name']}")
                    continue
                # Fetch referenced object of the current pathway
                request2 = NexusRequest(input_response=reference,
                                        link_href="referencedObject",
                                        method="GET")
                pathway_reference = execute_nexus_flow([request1, request2])

                # Fetch available actions for the current pathway
                request1 = NexusRequest(input_response=pathway_reference,
                                        link_href="availableActions",
                                        method="GET")
                available_actions = execute_nexus_flow([request1])

                # Fetch the inactive action object
                inactive_action = next(item for item in available_actions if item['id'] in set_pathway_inactive_action_id)
                request1 = NexusRequest(input_response=inactive_action,
                                        link_href="updateFormData",
                                        method="PUT", payload=pathway_reference)
                execute_nexus_flow([request1])
        logger.info("Pathways set to inactive")
        return True

    except Exception as e:
        logger.error(f"Error setting pathways inactive: {e}")


def _remove_basket_grants(patient, dashboard):
    pathway_collection_header_title = ["Ikke-visiteret"]
    try:
        remove_basket_remove_action_id = 402
        borgerkalender = nexus_client.fetch_borgerkalender(patient)

        request1 = NexusRequest(input_response=borgerkalender,
                                link_href="basketGrants",
                                method="GET")
        basket_grants_search = execute_nexus_flow([request1])

        for basket_grants in basket_grants_search['pages']:
            request1 = NexusRequest(input_response=basket_grants,
                                    link_href="basketGrants",
                                    method="GET")
            basket_grants = execute_nexus_flow([request1])
            for basket_grant in basket_grants:
                basket_types = basket_grant['children']
                for basket_type in basket_types:
                    basket_areas = basket_type['children']
                    for basket_area in basket_areas:
                        grants = basket_area['children']
                        for grant in grants:
                            execute_action = next((item for item in grant['actions']
                                                  if item['id'] == remove_basket_remove_action_id), None)
                            if execute_action is None:
                                logger.error("Basket grant inactive action not found.")
                                return

                            request1 = NexusRequest(input_response=execute_action,
                                                    link_href="executeAction",
                                                    method="PUT", payload=[])
                            execute_nexus_flow([request1])

        basket_grants = next((item for item in dashboard['view']['widgets'] if
                             item['headerTitle'] in pathway_collection_header_title), None)

        request1 = NexusRequest(input_response=basket_grants,
                                link_href="pathwayReferences",
                                method="GET")
        pathway_references = execute_nexus_flow([request1])
        for basket_references in pathway_references:
            grant_references = basket_references['children']
            for grant_reference in grant_references:
                if not grant_reference['grantId']:
                    continue

                _remove_patient_grants([grant_reference['grantId']])

        logger.info("Basket grants removed")
        return True
    except Exception as e:
        logger.error(f"Error removing basket grants: {e}")


def _remove_patient_grants(grant_ids: list):
    try:
        # Hardcoded value to open the Afslut window for grants/tilstande
        grant_afslut_id = [418, 502]

        # Home resource
        home_res = nexus_client.home_resource()

        for id in grant_ids:
            # Get patient grant by id
            patient_grant = nexus_client.get_request(home_res["_links"]["patientGrantById"]["href"] + "/" + str(id))

            # Fetch afslut object by grant_afslut_id
            afslut_object = next(item for item in patient_grant["currentWorkflowTransitions"]
                                 if item["id"] in grant_afslut_id)

            # Open the afslut window
            afslut_window = NexusRequest(input_response=afslut_object,
                                         link_href="prepareEdit",
                                         method="GET")
            afslut_window_response = execute_nexus_flow([afslut_window])

            # Save the edit, thus removing the grant
            save_afslut_window = NexusRequest(input_response=afslut_window_response, link_href="save",
                                              method="POST",
                                              payload=afslut_window_response)
            execute_nexus_flow([save_afslut_window])
        logger.info("Grants removed")
        return True

    except Exception as e:
        logger.error(f"Error removing patient grants: {e}")


def remove_fsiii_indsatser(patient):
    pathway_collection_header_title = ["Indsatser - FSIII"]

    dashboard = nexus_client.fetch_dashboard(patient, afslutning_af_borger_dashboard_id)

    basket_grants = next((item for item in dashboard['view']['widgets'] if item['headerTitle'] in pathway_collection_header_title), None)
    if not basket_grants:
        logger.error('Unable to find {pathway_collection_header_title} in dashboard')
    list_of_indsatser_link = basket_grants.get('_links', {}).get('pathwayReferences', {}).get('href', None)
    indsatser = nexus_client.get_request(list_of_indsatser_link)

    for item in enumerate(indsatser[0].get("children", [])):
        referenced_object = nexus_client.get_request(item.get('_links', {}).get('referencedObject', {}).get('href', None))
        paragraph = next((x for x in referenced_object.get('currentElements', []) if x.get('type', None) == 'paragraph'), None)
        paragraph_no = re.sub('[§ ]', '', paragraph.get('paragraph', {}).get("section", None))
        paragraph_no = None if paragraph_no == 'Paragraf' else paragraph_no
        if paragraph_no in do_not_delete:
            logger.info(f"Skipping {item.get('name', None)} - paragraph number: {paragraph_no}")
        else:
            afslut_object = next((item for item in referenced_object.get('currentWorkflowTransitions', []) if unidecode(item.get('name', '')).lower() in ['afslut']), None)  # TODO: add 'annuller' to the list
            if afslut_object:
                afslut_window = NexusRequest(input_response=afslut_object, link_href="prepareEdit", method="GET")

                afslut_window_response = execute_nexus_flow([afslut_window])
                save_afslut_window = NexusRequest(input_response=afslut_window_response, link_href="save", method="POST", payload=afslut_window_response)
                execute_nexus_flow([save_afslut_window])
                logger.info(f"Closed {item.get('name', None)} - paragraph number: {paragraph_no}")
            else:
                logger.warn(f"Afslut object not found for {item.get('name', None)}")  # TODO: add 'annuller' to the list

    return True
