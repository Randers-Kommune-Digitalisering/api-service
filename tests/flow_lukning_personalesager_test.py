from src.jobs.flow_lukning_personalesager import extract_cpr_and_institution, extract_employment_dates
import pytest


class TestExtractCprAndInstitution:

    def test_single_person_single_employment(self):
        person_list = [
            {
                "PersonCivilRegistrationIdentifier": "1234567890",
                "Employment": {
                    "EmploymentIdentifier": "E1",
                    "InstitutionIdentifier": "Inst1"
                }
            }
        ]
        expected = [("1234567890", ["Inst1"])]
        assert extract_cpr_and_institution(person_list) == expected

    def test_single_person_multiple_employments(self):
        person_list = [
            {
                "PersonCivilRegistrationIdentifier": "1234567890",
                "Employment": [
                    {
                        "EmploymentIdentifier": "E1",
                        "InstitutionIdentifier": "Inst5"
                    },
                    {
                        "EmploymentIdentifier": "E2",
                        "InstitutionIdentifier": "Inst1"
                    }
                ]
            }
        ]
        expected = [("1234567890", ["Inst5", "Inst1"])]
        assert extract_cpr_and_institution(person_list) == expected

    def test_multiple_persons(self):
        person_list = [
            {
                "PersonCivilRegistrationIdentifier": "1234567890",
                "Employment": {
                    "EmploymentIdentifier": "E1",
                    "InstitutionIdentifier": "Inst1"
                }
            },
            {
                "PersonCivilRegistrationIdentifier": "0987654321",
                "Employment": [
                    {
                        "EmploymentIdentifier": "E",
                        "InstitutionIdentifier": "Inst2"
                    },
                    {
                        "EmploymentIdentifier": "E3",
                        "InstitutionIdentifier": "Inst3"
                    }
                ]
            }
        ]
        expected = [
            ("1234567890", ["Inst1"]),
            ("0987654321", ["Inst2", "Inst3"])
        ]
        assert extract_cpr_and_institution(person_list) == expected

    def test_person_without_cpr(self):
        person_list = [
            {
                "Employment": {
                    "EmploymentIdentifier": "E1",
                    "InstitutionIdentifier": "Inst1"
                }
            }
        ]
        expected = []
        assert extract_cpr_and_institution(person_list) == expected

    def test_person_no_employment(self):
        person_list = [
            {
                "PersonCivilRegistrationIdentifier": "1234567890"
            }
        ]
        expected = [("1234567890", [])]
        assert extract_cpr_and_institution(person_list) == expected

    def test_duplicate_institutions(self):
        person_list = [
            {
                "PersonCivilRegistrationIdentifier": "1234567890",
                "Employment": [
                    {
                        "EmploymentIdentifier": "E1",
                        "InstitutionIdentifier": "Inst1"
                    },
                    {
                        "EmploymentIdentifier": "E2",
                        "InstitutionIdentifier": "Inst1"
                    }
                ]
            }
        ]
        expected = [("1234567890", ["Inst1"])]
        assert extract_cpr_and_institution(person_list) == expected


class TestExtractEmploymentDates:

    def test_extract_single_date_format1(self):
        text = "du er fra den 1. april 2024 ansat"
        expected = ["2024-04-01"]
        assert extract_employment_dates(text) == expected

    def test_extract_single_date_format2(self):
        text = "Anseet .dato 01.02.2024"
        expected = ["2024-02-01"]
        assert extract_employment_dates(text) == expected

    def test_extract_single_date_format3(self):
        text = "Det bekræftes hermed at du fra den 1. april 2024 er ansat som test"
        expected = ["2024-04-01"]
        assert extract_employment_dates(text) == expected

    def test_extract_multiple_dates(self):
        text = "Du er fra den 1. april 2024 ansat og Anseet.dato 01.02.2024"
        expected = ["2024-04-01", "2024-02-01"]
        assert extract_employment_dates(text) == expected

    def test_extract_date_with_different_format(self):
        text = "Startdato: 01-02-2024"
        expected = ["2024-02-01"]
        assert extract_employment_dates(text) == expected

    def test_extract_date_with_leading_zero(self):
        text = "Du er fra den 01. marts 2024 ansat"
        expected = ["2024-03-01"]
        assert extract_employment_dates(text) == expected

    def test_no_date_match(self):
        text = "Ingen dato nævnt her"
        expected = []
        assert extract_employment_dates(text) == expected

    def test_invalid_date_format(self):
        text = "Du er fra den 32. februar 2024 ansat"
        expected = []  # This is an invalid date
        assert extract_employment_dates(text) == expected

    def test_mixed_case(self):
        text = "Du er fra den 1. APRIL 2024 ansat"
        expected = ["2024-04-01"]
        assert extract_employment_dates(text) == expected
