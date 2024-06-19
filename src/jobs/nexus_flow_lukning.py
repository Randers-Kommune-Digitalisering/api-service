import logging
from datetime import datetime

from nexus.nexus_request import NexusRequest, execute_nexus_flow
from nexus.nexus_client import NEXUSClient

logger = logging.getLogger(__name__)
nexus_client = NEXUSClient()


def execute_lukning(cpr: str):
    try:
        # Find patient by CPR
        patient = nexus_client.fetch_patient_by_query(query=cpr)
        if not patient:
            return

        # _cancel_events(patient)
        _set_conditions_inactive(patient)
        # _set_pathways_inactive(patient)
        #
        # _remove_patient_grants([2298969])

    except Exception as e:
        logger.error(f"Error in job: {e}")


def _cancel_events(patient):
    # Fetch patient preferences
    request1 = NexusRequest(input_response=patient, link_href="patientPreferences", method="GET")

    # Execute Patient preferences
    patient_preferences = execute_nexus_flow([request1])

    # Fetch patient list of CITIZEN_CALENDAR
    citizen_calender_list = patient_preferences['CITIZEN_CALENDAR']

    # Find the object with name "Borgerkalender"
    borgerkalender = next((item for item in citizen_calender_list if item.get('name') == 'Borgerkalender'), None)

    # Fetch CITIZEN_CALENDAR self
    request1 = NexusRequest(input_response=borgerkalender, link_href="self", method="GET")

    # Create a dictionary with stopDate as the current datetime
    current_datetime = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    stop_date_dict = {"stopDate": current_datetime}

    # Fetch events to stop
    request2 = NexusRequest(link_href="getEventsToStop", method="GET", params=stop_date_dict)

    # Execute events_list
    events_list = execute_nexus_flow([request1, request2])

    # Save ids of upcoming events
    event_ids = [event['event']['id'] for event in events_list['events']]

    # If list is empty, stopEvents request will time out
    if not event_ids:
        return

    # Cancel events request
    request1 = NexusRequest(input_response=events_list, link_href="stopEvents", method="POST", json_body=event_ids)

    # Execute cancel events
    execute_nexus_flow([request1])


def _set_conditions_inactive(patient):
    active_condition_id = 28748
    inactive_condition_id = 28747
    # not_relevant_condition_id = 33628

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
    print("Active condition IDs:", active_conditions_ids)

    if not active_conditions_ids:
        print("No active conditions found.")
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
        print("Failed to retrieve conditions bulk prototype.")
        return

    # Prepare payload with state set to inactive
    inactive_state = next(
        (state for state in conditions_bulk_prototype['state']['possibleValues']
         if state['id'] == inactive_condition_id), None)

    if inactive_state is None:
        print("Inactive state not found.")
        return

    # Set state to inactive
    conditions_bulk_prototype['state']['value'] = inactive_state

    # Create new condition observation - observation state set to inactive
    request1 = NexusRequest(input_response=conditions_bulk_prototype,
                            link_href="create",
                            method="POST",
                            json_body=conditions_bulk_prototype)

    # Execute condition observation - active conditions are set to inactive
    execute_nexus_flow([request1])


def _set_pathway_inactive(pathway_id):

    return


def _remove_patient_grants(grant_id):
    # Hardcoded value to open the Afslut window for grants/tilstande
    grant_afslut_id = 418

    # Home resource
    home_res = nexus_client.home_resource()

    for id in grant_id:
        # Get patient grant by id
        patient_grant = nexus_client.get_request(home_res["_links"]["patientGrantById"]["href"] + "/" + str(id))

        # Fetch afslut object by grant_afslut_id
        afslut_object = next(item for item in patient_grant["currentWorkflowTransitions"]
                             if item["id"] == grant_afslut_id)

        # Open the afslut window
        afslut_window = NexusRequest(input_response=afslut_object,
                                     link_href="prepareEdit",
                                     method="GET")
        afslut_window_response = execute_nexus_flow([afslut_window])


        # Save the edit, thus removing the grant
        save_afslut_window = NexusRequest(input_response=afslut_window_response,link_href="save",
                                     method="POST",
                                     json_body=afslut_window_response)

        remove_patient_grants_flow = [save_afslut_window]

        execute_nexus_flow(remove_patient_grants_flow)


if __name__ == '__main__':
    execute_lukning("111131-1112")
