import logging
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
