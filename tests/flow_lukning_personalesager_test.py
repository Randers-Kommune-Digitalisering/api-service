from src.jobs.flow_lukning_personalesager import extract_cpr_and_institution
import pytest


class TestExtractCprAndInstitution():

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
