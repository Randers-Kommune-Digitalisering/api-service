import logging
import base64
from sbsys.sbsys_client import SbsysClient
from flask import Blueprint, request, jsonify
from utils.config import (SBSYS_USERNAME, SBSYS_PASSWORD, SBSIP_CLIENT_ID, SBSIP_CLIENT_SECRET,
                          SBSYS_PSAG_USERNAME, SBSYS_PSAG_PASSWORD, SBSIP_PSAG_CLIENT_ID, SBSIP_PSAG_CLIENT_SECRET, SBSYS_URL)

logger = logging.getLogger(__name__)

sbsys_client = SbsysClient(SBSIP_CLIENT_ID, SBSIP_CLIENT_SECRET,
                           SBSYS_USERNAME, SBSYS_PASSWORD, SBSYS_URL)
sbsys_psag_client = SbsysClient(SBSIP_PSAG_CLIENT_ID, SBSIP_PSAG_CLIENT_SECRET,
                                SBSYS_PSAG_USERNAME, SBSYS_PSAG_PASSWORD, SBSYS_URL)

api_sbsys_bp = Blueprint('api_sbsys', __name__, url_prefix='/api/sbsys')


@api_sbsys_bp.route('/sag/status', methods=['POST'])
def change_sag_status():
    data = request.get_json()
    status_id = data.get('SagsStatusID')
    # comment = data.get('Kommentar')

    if not status_id:
        return jsonify({"error": "SagsStatusID is required"}), 400
    # TODO journaliser kladder, og udfør erindringer for sager der skal afluttes, lukkes etc.


@api_sbsys_bp.route('/sag/search', methods=['POST'])
def sag_search():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "data is required"}), 400

        response = sbsys_client.sag_search(payload=data)
        return response, 200
    except Exception as e:
        return e, 500


# Returns a files based on Documents name property
# Documents can have multiple files
# Documents are filtered by the name property
@api_sbsys_bp.route('/fil/keywords', methods=['POST'])
def fil_by_keyword():
    allowed_filetypes = []
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "'keywords' and 'sagID' properties are required. 'keywords' is an array of strings. 'sagID' is a integer"}), 400
        if not data['keywords'] or not data['sagID']:
            return jsonify({"error": "'keywords' and 'sagID' properties are required. 'keywords' is an array of strings. 'sagID' is a integer"}), 400
        if not isinstance(data['keywords'], list):
            return jsonify({"error": "keywords has to be a list"})
        if data['allowedFiletypes']:
            if not isinstance(data['allowedFiletypes'], list):
                return jsonify({"error": "allowedFiletypes must be a list of strings. e.g. ['pdf', 'docs']"})
            allowed_filetypes = data['allowedFiletypes']

        # Fetch documents from sag specified by sag id
        documents_response = sbsys_client.fetch_documents(data['sagID'])
        if not documents_response:
            return jsonify({"error": f"No documents were found with sag id: {data['sagID']}"}), 404


        files = []
        # Iterate over keywords, and filter by comparing keyword name with document name
        for keyword in data['keywords']:
            keyword = keyword.lower()
            filtered_documents = [doc for doc in documents_response if 'Navn' in doc and keyword in doc['Navn'].lower()]
            for document in filtered_documents:
                for fil in document['Filer']:
                    file_content = sbsys_client.fetch_file(fil['ShortId'])
                    if not file_content:
                        continue

                    file_content = file_content.content
                    # Check if the file has allowed filetypes
                    if allowed_filetypes and not fil['Filendelse'].lower() in allowed_filetypes:
                        continue

                    # Encode binary file code to base64
                    encoded_file = base64.b64encode(file_content).decode('utf-8')

                    #  Create a file object
                    files.append({
                        'filename': fil['Filnavn'],
                        'document_name': document['Navn'],
                        'data': encoded_file,
                        'mime_type': fil['MimeType']
                    })


        return jsonify(files), 200
    except Exception as e:
        return jsonify({"error": f"{e}"}), 500
