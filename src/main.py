from flask import Flask
from healthcheck import HealthCheck
from prometheus_client import generate_latest

from utils.logging import set_logging_configuration, APP_RUNNING
from utils.config import DEBUG, PORT, POD_NAME


def create_app():
    app = Flask(__name__)
    health = HealthCheck()
    app.add_url_rule("/healthz", "healthcheck", view_func=lambda: health.run())
    app.add_url_rule('/metrics', "metrics", view_func=generate_latest)
    APP_RUNNING.labels(POD_NAME).set(1)
    return app


set_logging_configuration()
app = create_app()


if __name__ == "__main__":  # pragma: no cover
    #app.run(debug=DEBUG, host='0.0.0.0', port=PORT)
    from delta import DeltaClient
    from utils.config import DELTA_CERT_BASE64, DELTA_CERT_PASS, DELTA_BASE_URL, DELTA_TOP_ADM_UNIT_UUID
    dc = DeltaClient(cert_base64=DELTA_CERT_BASE64, cert_pass=DELTA_CERT_PASS, base_url=DELTA_BASE_URL, top_adm_unit_uuid=DELTA_TOP_ADM_UNIT_UUID)
    print(cd.get_adm_unit_list()) #NB: takes almost 5 minutes to run
