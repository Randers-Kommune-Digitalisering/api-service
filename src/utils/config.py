import os
from dotenv import load_dotenv


# loads .env file, will not overide already set enviroment variables (will do nothing when testing, building and deploying)
load_dotenv()


DEBUG = os.getenv('DEBUG', 'False') in ['True', 'true']
PORT = os.getenv('PORT', '8080')
POD_NAME = os.getenv('POD_NAME', 'Pod name not set')

DELTA_TOP_ADM_UNIT_UUID = os.environ['DELTA_TOP_ADM_UNIT_UUID'].strip()
DELTA_CERT_BASE64 = os.environ['DELTA_CERT_BASE64'].strip()
DELTA_CERT_PASS = os.environ['DELTA_CERT_PASS'].strip()
DELTA_BASE_URL = os.environ['DELTA_BASE_URL'].strip()

# NEXUS
NEXUS_URL = os.environ["NEXUS_URL"].strip()
NEXUS_CLIENT_ID = os.environ["NEXUS_CLIENT_ID"].strip()
NEXUS_CLIENT_SECRET = os.environ["NEXUS_CLIENT_SECRET"].strip()

# KP
KP_URL = os.environ["KP_URL"].strip()
KP_USERNAME = os.environ["KP_USERNAME"].strip()
KP_PASSWORD = os.environ["KP_PASSWORD"].strip()
KP_SESSION_COOKIE = os.environ["KP_SESSION_COOKIE"].strip()
KP_CONNECTION_ID = os.environ["KP_CONNECTION_ID"].strip()

# SBSYS
SBSYS_URL = os.environ["SBSYS_URL"].strip()
SBSIP_URL = os.environ["SBSIP_URL"].strip()
SBSIP_MASTER_URL = os.environ["SBSIP_MASTER_URL"].strip()

# Personalesager
SBSIP_PSAG_CLIENT_ID = os.environ["SBSIP_PSAG_CLIENT_ID"].strip()
SBSIP_PSAG_CLIENT_SECRET = os.environ["SBSIP_PSAG_CLIENT_SECRET"].strip()
SBSYS_PSAG_USERNAME = os.environ["SBSYS_PSAG_USERNAME"].strip()
SBSYS_PSAG_PASSWORD = os.environ["SBSYS_PSAG_PASSWORD"].strip()

# Korsel
SBSIP_CLIENT_ID = os.environ["SBSIP_CLIENT_ID"].strip()
SBSIP_CLIENT_SECRET = os.environ["SBSIP_CLIENT_SECRET"].strip()
SBSYS_USERNAME = os.environ["SBSYS_USERNAME"].strip()
SBSYS_PASSWORD = os.environ["SBSYS_PASSWORD"].strip()

# Browserless
BROWSERLESS_BASIC_AUTH = os.environ["BROWSERLESS_BASIC_AUTH"].strip()
BROWSERLESS_CLIENT_ID = os.environ["BROWSERLESS_CLIENT_ID"].strip()
BROWSERLESS_CLIENT_SECRET = os.environ["BROWSERLESS_CLIENT_SECRET"].strip()
