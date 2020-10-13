import unittest
import importlib
import requests
import sys
import os
import json



CONFLUENCE_FILES = {
    "KEYONE": "Confluence-space-export-ds.xmlkeyone.zip",
    "ds": "Confluence-space-export-ds.xml.zip"
}
CONFLUENCE_BASEURL = "http://localhost:1990/confluence"
CONFLUENCE_INVALID_BASEURL = "http://localhost:1991/confluence"
CONFLUENCE_KEYS = ["KEYONE", "ds"]
CONFLUENCE_USERS = {
    "admin_user": {
        "username": "admin",
        "password": "admin"
    },
    "normal_user": {
        "username": "user",
        "password": "user"
    },
    "invalid_user": {
        "username": "admin2",
        "password": "admin2"
    }
}


def parse_json(body):
    try:
        body = body.decode("utf-8")
        result = json.loads(body)
    except Exception as e:
        result = {}
    return result


class ConfluenceTestExport(unittest.TestCase):

    def setUpClass() -> None:
        # add current folder to PYTHONPATH for discovering the space imports
        dir_path = os.path.dirname(os.path.realpath(__file__))
        parent_dir = os.path.join(dir_path, '../../../')
        sys.path.insert(0, parent_dir)
        sys.path.insert(0, dir_path)

        importlib.import_module("confluence.backup.export")
        importlib.import_module("confluence.backup.import")

    def get_existing_spaces(self):
        url = CONFLUENCE_BASEURL + "/rest/api/space"
        r = requests.get(url, stream=True,
                         auth=(CONFLUENCE_USERS["admin_user"]["username"], CONFLUENCE_USERS["admin_user"]["password"]))
        self.assertEqual(r.status_code, 200)
        js = parse_json(r.content)
        return [result["key"] for result in js["results"]]

    def setUp(self):
        existing_keys = self.get_existing_spaces()
        if "KEYONE" not in existing_keys:
            lst = ["file", CONFLUENCE_BASEURL, CONFLUENCE_FILES["KEYONE"], "--username",
                   CONFLUENCE_USERS["admin_user"]["username"],
                   "--password", CONFLUENCE_USERS["admin_user"]["password"], "--batch"]
            results = sys.modules["confluence.backup.import"].main(lst)
            self.assertEqual(results, ["0: Success"])

        if "ds" not in existing_keys:
            lst = ["file", CONFLUENCE_BASEURL, CONFLUENCE_FILES["ds"], "--username",
                   CONFLUENCE_USERS["admin_user"]["username"],
                   "--password", CONFLUENCE_USERS["admin_user"]["password"], "--batch"]
            results = sys.modules["confluence.backup.import"].main(lst)
            self.assertEqual(results, ["0: Success"])

    def tearDown(self):
        if os.path.exists("Confluence-space-export-KEYONE.xml.zip"):
            os.remove("Confluence-space-export-KEYONE.xml.zip")

    def test_export_basic(self):
        lst = ["file", CONFLUENCE_BASEURL, CONFLUENCE_KEYS[0], "--username", CONFLUENCE_USERS["admin_user"]["username"],
               "--password", CONFLUENCE_USERS["admin_user"]["password"], "--batch"]
        results = sys.modules["confluence.backup.export"].main(lst)
        self.assertEqual(results, ["0: Success"])

    def test_export_basic_multiple_keys(self):
        confluence_keys = ",".join(CONFLUENCE_KEYS)
        lst = ["file", CONFLUENCE_BASEURL, confluence_keys, "--username", CONFLUENCE_USERS["admin_user"]["username"],
               "--password", CONFLUENCE_USERS["admin_user"]["password"], "--batch"]
        results = sys.modules["confluence.backup.export"].main(lst)
        self.assertEqual(results, ['0: Success', '0: Success'])

    def test_export_invalid_key(self):
        invalid_key = "INVALID"
        lst = ["file", CONFLUENCE_BASEURL, invalid_key, "--username",
               CONFLUENCE_USERS["admin_user"]["username"],
               "--password", CONFLUENCE_USERS["admin_user"]["password"], "--batch"]
        results = sys.modules["confluence.backup.export"].main(lst)
        self.assertEqual(results, ['404: not_found'])

    def test_export_one_invalid_key_from_multiple(self):
        invalid_key = "INVALID"
        valid_key = "KEYONE"
        confluence_keys = invalid_key + "," + valid_key
        lst = ["file", CONFLUENCE_BASEURL, confluence_keys, "--username",
               CONFLUENCE_USERS["admin_user"]["username"],
               "--password", CONFLUENCE_USERS["admin_user"]["password"], "--batch"]
        results = sys.modules["confluence.backup.export"].main(lst)
        self.assertEqual(results, ['404: not_found', '0: Success'])

    def test_export_invalid_url(self):
        lst = ["file", CONFLUENCE_INVALID_BASEURL, CONFLUENCE_KEYS[0], "--username",
               CONFLUENCE_USERS["admin_user"]["username"],
               "--password", CONFLUENCE_USERS["admin_user"]["password"], "--batch"]
        results = sys.modules["confluence.backup.export"].main(lst)
        self.assertEqual(results, ['444: url not reachable'])

    def test_export_invalid_credentials(self):
        lst = ["file", CONFLUENCE_BASEURL, CONFLUENCE_KEYS[0], "--username",
               CONFLUENCE_USERS["invalid_user"]["username"],
               "--password", CONFLUENCE_USERS["invalid_user"]["password"], "--batch"]
        results = sys.modules["confluence.backup.export"].main(lst)
        self.assertEqual(results, ['401: unauthorized'])

    def test_export_invalid_permissions(self):
        lst = ["file", CONFLUENCE_BASEURL, CONFLUENCE_KEYS[0], "--username",
               CONFLUENCE_USERS["normal_user"]["username"],
               "--password", CONFLUENCE_USERS["normal_user"]["password"], "--batch"]
        results = sys.modules["confluence.backup.export"].main(lst)
        self.assertEqual(results, ['403: forbidden'])
