from flask import Flask, jsonify
from healthcheck import HealthCheck
from prometheus_client import generate_latest

from utils.logging import set_logging_configuration, APP_RUNNING
from utils.config import DEBUG, PORT, POD_NAME, DELTA_CERT_BASE64, DELTA_CERT_PASS, DELTA_BASE_URL, DELTA_TOP_ADM_UNIT_UUID
from utils.nexus_token import NEXUSClient
from delta import DeltaClient


# Create an instance of NEXUSClient
nexus_client = NEXUSClient()
# Create an instance of DeltaClient
dc = DeltaClient(cert_base64=DELTA_CERT_BASE64, cert_pass=DELTA_CERT_PASS, base_url=DELTA_BASE_URL, top_adm_org_uuid=DELTA_TOP_ADM_UNIT_UUID)


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
    try:
        response = nexus_client.home_resource()
        return jsonify(response), 200
    except Exception as e:
        app.logger.error(f"Error fetching home resource: {e}")
        return str(e), 500


@app.route('/test-employees', methods=['GET'])
def test_employees_route():
    try:
        response = dc.get_employees_changed()
        print(response)
        return jsonify(response), 200
    except Exception as e:
        app.logger.error(f"Error fetching employees: {e}")
        return str(e), 500


if __name__ == "__main__":  # pragma: no cover
    app.run(debug=DEBUG, host='0.0.0.0', port=PORT)
