import logging
import requests
from datetime import datetime
from dateutil.relativedelta import relativedelta
from requests.auth import HTTPBasicAuth

from utils.config import SD_USERNAME, SD_PASSWORD, SD_URL
from sd.sd_client import SDClient

logger = logging.getLogger(__name__)
sd_client = SDClient(SD_USERNAME, SD_PASSWORD, SD_URL)

sd_inst_codes = ["AI", "OV", "RS", "OR",
                 "OB", "OW", "OY", "OQ",
                 "RQ", "OX", "RY", "BQ",
                 "OU", "RO", "OK", "CV",
                 "CZ", "RG", "BX", "RI",
                 "BW", "OZ", "RJ", "RW",
                 "OT", "CU"]

def execute_lukning():
    fetch_employments_changed()
    fetch_personalesag()

def fetch_employments_changed():
    # Fetch changed employments foreach SD institution code
    for inst_code in sd_inst_codes:
        path = 'GetEmploymentChanged20070401'

        # Get the current date and format it as DD.MM.YYYY
        effective_date = datetime.now().strftime('%d.%m.%Y')

        # Get the first and last day of the month three months ago using the function
        activation_date, deactivation_date = _get_first_and_last_day_three_months_ago()

        # Format the activation_date as DD.MM.YYYY
        activation_date = activation_date.strftime('%d.%m.%Y')

        # Format the deactivation_date as DD.MM.YYYY
        deactivation_date = deactivation_date.strftime('%d.%m.%Y')

        # Define the SD params
        params = {
            f'InstitutionIdentifier': inst_code,
            'EmploymentStatusIndicator': 'true',
            'PersonCivilRegistrationIdentifier': '',
            'EmploymentIdentifier': '',
            'DepartmentIdentifier': '',
            'ProfessionIndicator': 'false',
            'DepartmentIndicator': 'false',
            'WorkingTimeIndicator': 'false',
            'SalaryCodeGroupIndicator': 'false',
            'SalaryAgreementIndicator': 'false',
            'ActivationDate': activation_date,
            'DeactivationDate': deactivation_date,
            'submit': 'OK',
            'EffectiveDate': effective_date
        }
        try:
            response = sd_client.post_request(path=path, params=params)
            if not response:
                logger.warning("No response from SD client")
            else:
                logger.info(f"Employments were found: {response}")
            return response

        except Exception as e:
            logger.error(e)
            return None


def _get_first_and_last_day_three_months_ago():
    # Get the current date
    today = datetime.today()

    # Calculate the date three months ago
    three_months_ago = today - relativedelta(months=3)

    # Get the first day of the month three months ago
    first_day_of_three_months_ago = three_months_ago.replace(day=1)

    # Get the last day of the month three months ago
    last_day_of_three_months_ago = (first_day_of_three_months_ago + relativedelta(months=1) - relativedelta(days=1))

    return first_day_of_three_months_ago, last_day_of_three_months_ago


def fetch_personalesag():
    return {}


if __name__ == "__main__":  # pragma: no cover
    execute_lukning()