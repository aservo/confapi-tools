import unittest
import importlib
import sys
import requests
import time
from zipfile import ZipFile
import os
import shutil

CONFLUENCE_BASEURL = "http://localhost:1990/confluence"
CONFLUENCE_INVALID_BASEURL = "http://localhost:1991/confluence"
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

CONFLUENCE_FILES = {
    "KEYONE": "Confluence-space-export-ds.xmlkeyone.zip",
    "regex_all": "*.zip",
    "regex_restricted": "Confluence-space-export-ds.*",
    "regex_invalid": "INVALID.*",
    "invalid": "INVALID",
    "ds": "Confluence-space-export-ds.xml.zip",
    "large": "Confluence-space-export-ds-large.xml.zip"
}


class ConfluenceTestImport(unittest.TestCase):

    def setUpClass() -> None:

        # add current folder to PYTHONPATH for discovering the space imports
        dir_path = os.path.dirname(os.path.realpath(__file__))
        parent_dir = os.path.join(dir_path, '../../../')
        sys.path.insert(0, parent_dir)
        sys.path.insert(0, dir_path)

        # dynamic import for the unittest, otherwise it will not find the packages (confluence.backup.tests)
        importlib.import_module("confluence.backup.import")

        # dynamically create large import file
        file_size = 64 * 1024 * 1024  # 128 MB
        file_name = "Confluence-space-export-ds.xml.zip"
        extract_folder = "Confluence-space-export-ds.xml"
        result_file = "Confluence-space-export-ds-large.xml"
        move_file_to = "./Confluence-space-export-ds.xml/attachments/"

        with ZipFile(file_name, 'r') as zip:
            zip.printdir()
            zip.extractall(extract_folder)

        with open('large_file.txt', 'wb') as fout:
            fout.write(os.urandom(file_size))

        shutil.move("./large_file.txt", move_file_to + "large_file.txt")
        shutil.make_archive(result_file, 'zip', extract_folder)
        shutil.rmtree("./" + extract_folder)

    def tearDownClass() -> None:
        if os.path.exists("Confluence-space-export-ds-large.xml.zip"):
            os.remove("Confluence-space-export-ds-large.xml.zip")

    def delete_spaces(self, list_of_keys):
        for key in list_of_keys:
            url = CONFLUENCE_BASEURL + "/rest/api/space/" + key
            response_delete = requests.delete(url, auth=(
            CONFLUENCE_USERS["admin_user"]["username"], CONFLUENCE_USERS["admin_user"]["password"]))
            self.assertEqual(response_delete.status_code, 202)
            js = sys.modules["confluence.backup.import"].parse_json_body(response_delete.content)
            status_resource = js["links"]["status"]
            url_status = CONFLUENCE_BASEURL + status_resource
            response_status = requests.get(url_status, auth=(
            CONFLUENCE_USERS["admin_user"]["username"], CONFLUENCE_USERS["admin_user"]["password"]))
            percentage_complete = 0

            while percentage_complete < 100:
                time.sleep(1)
                js = sys.modules["confluence.backup.import"].parse_json_body(response_status.content)
                percentage_complete = js["percentageComplete"]
                response_status = requests.get(url_status, auth=(
                    CONFLUENCE_USERS["admin_user"]["username"], CONFLUENCE_USERS["admin_user"]["password"]))

    def get_existing_spaces(self):
        url = CONFLUENCE_BASEURL + "/rest/api/space"
        r = requests.get(url, stream=True,
                         auth=(CONFLUENCE_USERS["admin_user"]["username"], CONFLUENCE_USERS["admin_user"]["password"]))
        self.assertEqual(r.status_code, 200)
        js = sys.modules["confluence.backup.import"].parse_json_body(r.content)
        return [result["key"] for result in js["results"]]

    def setUp(self):
        existing_keys = self.get_existing_spaces()
        self.delete_spaces(existing_keys)

    def tearDown(self):
        pass

    def test_import_basic(self):
        lst = ["file", CONFLUENCE_BASEURL, CONFLUENCE_FILES["KEYONE"], "--username",
               CONFLUENCE_USERS["admin_user"]["username"],
               "--password", CONFLUENCE_USERS["admin_user"]["password"], "--batch"]
        results = sys.modules["confluence.backup.import"].main(lst)
        self.assertEqual(results, ["0: Success"])

    def test_import_double_file(self):
        lst = ["file", CONFLUENCE_BASEURL, CONFLUENCE_FILES["ds"], CONFLUENCE_FILES["ds"],
               "--username", CONFLUENCE_USERS["admin_user"]["username"],
               "--password", CONFLUENCE_USERS["admin_user"]["password"], "--batch"]
        results = sys.modules["confluence.backup.import"].main(lst)
        self.assertIn("0: Success", results)
        self.assertIn("400: bad_request", results)

    def test_import_more_files(self):
        lst = ["file", CONFLUENCE_BASEURL, CONFLUENCE_FILES["KEYONE"], CONFLUENCE_FILES["ds"], "--username",
               CONFLUENCE_USERS["admin_user"]["username"],
               "--password", CONFLUENCE_USERS["admin_user"]["password"], "--batch"]
        results = sys.modules["confluence.backup.import"].main(lst)
        self.assertEqual(results, ["0: Success", "0: Success"])

    def test_import_regex(self):
        lst = ["file", CONFLUENCE_BASEURL, CONFLUENCE_FILES["regex_restricted"], "--username",
               CONFLUENCE_USERS["admin_user"]["username"],
               "--password", CONFLUENCE_USERS["admin_user"]["password"], "--batch"]
        results = sys.modules["confluence.backup.import"].main(lst)
        self.assertEqual(results, ["0: Success", "0: Success"])

    def test_import_invalid_regex(self):
        lst = ["file", CONFLUENCE_BASEURL, CONFLUENCE_FILES["regex_invalid"], "--username",
               CONFLUENCE_USERS["admin_user"]["username"],
               "--password", CONFLUENCE_USERS["admin_user"]["password"], "--batch"]
        results = sys.modules["confluence.backup.import"].main(lst)
        self.assertEqual(results, [])

    def test_import_one_invalid_regex_from_multiple(self):
        lst = ["file", CONFLUENCE_BASEURL, CONFLUENCE_FILES["regex_invalid"], CONFLUENCE_FILES["regex_restricted"],
               "--username", CONFLUENCE_USERS["admin_user"]["username"],
               "--password", CONFLUENCE_USERS["admin_user"]["password"], "--batch"]
        results = sys.modules["confluence.backup.import"].main(lst)
        self.assertEqual(results, ["0: Success", "0: Success"])

    def test_import_invalid_url_small(self):
        lst = ["file", CONFLUENCE_INVALID_BASEURL, CONFLUENCE_FILES["ds"], "--username",
               CONFLUENCE_USERS["admin_user"]["username"],
               "--password", CONFLUENCE_USERS["admin_user"]["password"], "--batch"]
        results = sys.modules["confluence.backup.import"].main(lst)
        self.assertEqual(results, ["444: url not reachable"])

    def test_import_invalid_url_large(self):
        lst = ["file", CONFLUENCE_INVALID_BASEURL, CONFLUENCE_FILES["large"], "--username",
               CONFLUENCE_USERS["admin_user"]["username"],
               "--password", CONFLUENCE_USERS["admin_user"]["password"], "--batch"]
        results = sys.modules["confluence.backup.import"].main(lst)
        self.assertEqual(results, ["444: url not reachable"])

    def test_import_invalid_credentials_small(self):
        lst = ["file", CONFLUENCE_BASEURL, CONFLUENCE_FILES["ds"], "--username",
               CONFLUENCE_USERS["invalid_user"]["username"],
               "--password", CONFLUENCE_USERS["invalid_user"]["password"], "--batch"]
        results = sys.modules["confluence.backup.import"].main(lst)
        self.assertEqual(results, ["401: unauthorized"])

    def test_import_invalid_credentials_large(self):
        lst = ["file", CONFLUENCE_BASEURL, CONFLUENCE_FILES["large"], "--username",
               CONFLUENCE_USERS["invalid_user"]["username"],
               "--password", CONFLUENCE_USERS["invalid_user"]["password"], "--batch"]
        results = sys.modules["confluence.backup.import"].main(lst)
        self.assertEqual(results, ["401: unauthorized"])

    def test_import_invalid_permissions_small(self):
        lst = ["file", CONFLUENCE_BASEURL, CONFLUENCE_FILES["ds"], "--username",
               CONFLUENCE_USERS["normal_user"]["username"],
               "--password", CONFLUENCE_USERS["normal_user"]["password"], "--batch"]
        results = sys.modules["confluence.backup.import"].main(lst)
        self.assertEqual(results, ["403: forbidden"])

    def test_import_invalid_permissions_large(self):
        lst = ["file", CONFLUENCE_BASEURL, CONFLUENCE_FILES["large"], "--username",
               CONFLUENCE_USERS["normal_user"]["username"],
               "--password", CONFLUENCE_USERS["normal_user"]["password"], "--batch"]
        results = sys.modules["confluence.backup.import"].main(lst)
        self.assertEqual(results, ["403: forbidden"])
