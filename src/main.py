from flask import Flask, jsonify
from healthcheck import HealthCheck
from prometheus_client import generate_latest

from utils.logging import set_logging_configuration, APP_RUNNING
from utils.config import DEBUG, PORT, POD_NAME
from utils.nexus_token import NEXUSClient

# Create an instance of NEXUSClient
nexus_client = NEXUSClient()


def create_app():
    app = Flask(__name__)
    health = HealthCheck()
    app.add_url_rule("/healthz", "healthcheck", view_func=lambda: health.run())
    app.add_url_rule('/metrics', "metrics", view_func=generate_latest)
    APP_RUNNING.labels(POD_NAME).set(1)
    return app


set_logging_configuration()
app = create_app()


@app.route('/test-home-resource', methods=['GET'])
def test_home_resource_route():
    print("Test resource")
    try:
        response = nexus_client.home_resource()
        return jsonify(response), 200
    except Exception as e:
        app.logger.error(f"Error fetching home resource: {e}")
        return str(e), 500


def test_home_resource():
    try:
        response = nexus_client.home_resource()
        return jsonify(response)
    except Exception as e:
        return str(e)


if __name__ == "__main__":  # pragma: no cover
    app.run(debug=DEBUG, host='0.0.0.0', port=PORT)

    # Test Delta
    # from delta import DeltaClient
    # from utils.config import DELTA_CERT_BASE64, DELTA_CERT_PASS, DELTA_BASE_URL, DELTA_TOP_ADM_UNIT_UUID
    # dc = DeltaClient(cert_base64=DELTA_CERT_BASE64, cert_pass=DELTA_CERT_PASS, base_url=DELTA_BASE_URL, top_adm_org_uuid=DELTA_TOP_ADM_UNIT_UUID)
    # print(dc.get_adm_org_list()) #NB: takes almost 5 minutes to run

    # Test Nexus
    # test_home_resource()
