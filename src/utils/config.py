import os
from dotenv import load_dotenv


# loads .env file, will not overide already set enviroment variables (will do nothing when testing, building and deploying)
load_dotenv()


DEBUG = os.getenv('DEBUG', 'False') in ['True', 'true']
PORT = os.getenv('PORT', '8080')
POD_NAME = os.getenv('POD_NAME', 'Pod name not set')

DELTA_CERT_BASE64 = os.environ['DELTA_CERT_BASE64']
DELTA_CERT_PASS = os.environ['DELTA_CERT_PASS']
DELTA_BASE_URL = os.environ['DELTA_BASE_URL']
