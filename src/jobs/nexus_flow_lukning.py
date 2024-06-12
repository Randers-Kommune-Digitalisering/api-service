import logging
from datetime import datetime

from nexus.nexus_request import NexusRequest, execute_nexus_flow
from nexus.nexus_client import NEXUSClient

logger = logging.getLogger(__name__)
nexus_client = NEXUSClient()


def execute_lukning(cpr: str):
    try:
        # Find patient by CPR
        patient = _fetch_patient_by_query(query=cpr)
        if not patient:
            return

        cancel_visits(patient)

    except Exception as e:
        logger.error(f"Error in job: {e}")


def _fetch_patient_by_query(query):
    patient_search = nexus_client.find_patient_by_query(query=query)
    patient_link = patient_search['pages'][0]['_links']['patientData']['href']

    patient_response = nexus_client.get_request(path=patient_link)
    request1 = NexusRequest(input_response=patient_response[0], link_href="self", method="GET")
    return execute_nexus_flow([request1])


def cancel_visits(patient):

    # Patient preferences
    request1 = NexusRequest(input_response=patient, link_href="patientPreferences", method="GET")

    # Execute Patient preferences
    patient_preferences = execute_nexus_flow([request1])

    # Retrieve list of CITIZEN_CALENDAR
    citizen_calender_list = patient_preferences['CITIZEN_CALENDAR']

    # Find the object with name "Borgerkalender"
    borgerkalender = next((item for item in citizen_calender_list if item.get('name') == 'Borgerkalender'), None)

    # Get CITIZEN_CALENDAR self
    request1 = NexusRequest(input_response=borgerkalender, link_href="self", method="GET")

    # Create a dictionary with stopDate as the current datetime
    current_datetime = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    stop_date_dict = {"stopDate": current_datetime}

    # Get events to stop
    request2 = NexusRequest(link_href="getEventsToStop", method="GET", params=stop_date_dict)

    # Execute events_list
    events_list = execute_nexus_flow([request1, request2])

    # Save ids of upcoming events
    event_ids = [event['event']['id'] for event in events_list['events']]

    # If list is empty, stopEvents request will timeout
    if not event_ids:
        return

    # Stop events request
    request1 = NexusRequest(input_response=events_list, link_href="stopEvents", method="POST", json_body=event_ids)


if __name__ == '__main__':
    execute_lukning("111131-1112")
