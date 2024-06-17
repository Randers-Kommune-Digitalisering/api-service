import os
from dotenv import load_dotenv


# loads .env file, will not overide already set enviroment variables (will do nothing when testing, building and deploying)
load_dotenv()


DEBUG = os.getenv('DEBUG', 'False') in ['True', 'true']
PORT = os.getenv('PORT', '8080')
POD_NAME = os.getenv('POD_NAME', 'Pod name not set')

DELTA_TOP_ADM_UNIT_UUID = "c16de869-8639-4d94-aa30-fa6c8e2459b3"
DELTA_CERT_BASE64 = os.environ['DELTA_CERT_BASE64'].strip()
DELTA_CERT_PASS = os.environ['DELTA_CERT_PASS'].strip()
DELTA_BASE_URL = os.environ['DELTA_BASE_URL'].strip()

# NEXUS
NEXUS_URL = os.environ["NEXUS_URL"].strip()
NEXUS_CLIENT_ID = os.environ["NEXUS_CLIENT_ID"].strip()
NEXUS_CLIENT_SECRET = os.environ["NEXUS_CLIENT_SECRET"].strip()
