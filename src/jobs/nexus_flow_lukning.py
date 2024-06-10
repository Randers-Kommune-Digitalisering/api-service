import logging

from nexus.nexus_request import NexusRequest, execute_nexus_flow
from nexus.nexus_client import NEXUSClient

nexus_client = NEXUSClient()

def execute_lukning(cpr: str):
    # Find patient by CPR
    patient = _fetch_patient_by_query(cpr)
    if not patient:
        return
    print(patient)

def _fetch_patient_by_query(query):
   return nexus_client.find_patient_by_query(query)['pages'][0]['_links']['patientData']['href']

if __name__ == '__main__':
    execute_lukning("111131-1112")