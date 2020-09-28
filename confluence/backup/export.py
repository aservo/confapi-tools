#!/usr/bin/env python3
from typing import Tuple

import requests
import time
import sys
import json
import os
import argparse
import getpass

export_resource = "rest/confapi/1/backup/export/"
authentication_tuple: Tuple[str, str] = ("admin", "admin")
error_collection = []
terminate_script = [444, 403, 401]
batch_mode = False


def collect_error(error_code, value):
    global error_collection
    global terminate_script
    message = str(error_code) + ": " + value
    error_collection.append(message)
    if error_code == 401:
        print("HINT: After multiple failed login attempts it might be required to solve a CAPTCHA")
    if error_code in terminate_script:
        print(error_collection)
        return 1
    return 0


def print_url_unreachable(error):
    print("\nURL can't be reached.\n")
    print(error)
    return collect_error(444, "url not reachable")


def print_http_error(http_response):
    print("An error occurred: " + str(http_response.status_code) + "\n" +
          requests.status_codes._codes[http_response.status_code][0])
    return collect_error(http_response.status_code, requests.status_codes._codes[http_response.status_code][0])


def parse_json_header(headers):
    res = str(headers).replace("'", '"')
    return json.loads(res)


def parse_json_body(body):
    try:
        body = body.decode("utf-8")
        result = json.loads(body)
    except Exception as e:
        result = {}
    return result


def export_download(key, url, chunk_size=128):
    save_file_path = os.getcwd() + "/Confluence-space-export-" + key + ".xml.zip"
    r = requests.get(url, stream=True, auth=authentication_tuple)
    with open(save_file_path, 'wb') as fd:
        for chunk in r.iter_content(chunk_size=chunk_size):
            fd.write(chunk)
    return collect_error(0, "Success")


def export_queue(key, queue_url):
    response_get_queue = requests.get(queue_url, auth=authentication_tuple)
    global batch_mode

    if response_get_queue.ok:
        # decorate
        while response_get_queue.status_code == 200:
            js = parse_json_body(response_get_queue.content)
            percentage = js["percentageComplete"]
            response_get_queue = requests.get(queue_url, auth=authentication_tuple)
            time.sleep(1)
            if not batch_mode:
                sys.stdout.write("\r%d%%" % percentage)
                sys.stdout.flush()
        if response_get_queue.status_code == 201:
            if not batch_mode:
                sys.stdout.write("\r%d%%" % 100)
                sys.stdout.flush()
                print()
            response_get_queue = requests.get(queue_url, auth=authentication_tuple)
            js = parse_json_header(response_get_queue.headers)
            zip_url = js['Location']
            return export_download(key, zip_url)
        return 1

    else:
        js = parse_json_body(response_get_queue.content)
        print(js["errorMessages"])
        return collect_error(
            str(response_get_queue.status_code) + ": " + requests.status_codes._codes[response_get_queue.status_code][
                0])


def main(args):
    global authentication_tuple
    global export_resource
    global error_collection
    global batch_mode
    error_collection = []
    exit_response = 0

    parser = argparse.ArgumentParser(
        description="sample usage: \n python3 export.py base-url key1,key2 --username my_username --password "
                    "my_password "
                    "\n python3 export.py http://localhost:1990/confluence KEY,ds --username admin --password admin "
                    "\n or just: \n ./export.py http://localhost:1990/confluence KEY,ds --username admin --password "
                    "admin\n ",
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("host", help="provide host url e.g. http://localhost:1990/confluence")
    parser.add_argument("key", help="provide key e.g. KEY")
    parser.add_argument("--username", "-U",
                        help="provide username e.g. admin; \nif not provided the user will be prompted to introduce "
                             "username and password.",
                        required=False)
    parser.add_argument("--password", "-P",
                        help="provide password e.g. admin; \nif not provided the user will be prompted to introduce "
                             "username and password.",
                        required=False)
    parser.add_argument("--batch", "-b",
                        action="store_true",
                        help="Enter batch mode.",
                        required=False)
    args = parser.parse_args(args[1:])
    username = args.username
    password = args.password

    if username is None or password is None:
        username = input("Username: ")
        password = getpass.getpass(prompt='Password: ', stream=None)
    authentication_tuple = (username, password)

    batch_mode = False
    if args.batch:
        batch_mode = True
    base_url = args.host
    key_list = args.key.split(',')

    for key in key_list:
        print("\nDownloading space " + key)

        # Build url
        suffix = "/" if base_url[-1] != "/" else ""
        request_page_url = base_url + suffix + export_resource + key

        try:
            # Try to connect
            response_request_page = requests.get(request_page_url, auth=authentication_tuple)

            if not response_request_page.ok:
                exit_response = print_http_error(response_request_page)

                js = parse_json_body(response_request_page.content)
                if "errorMessages" in js:
                    print(js["errorMessages"])

            else:
                js = parse_json_header(response_request_page.headers)
                url = js['Location']

                if response_request_page.status_code == 201:
                    if not batch_mode:
                        print("100%")
                    export_download(key, url)

                if response_request_page.status_code == 202:
                    exit_response = export_queue(key, url)
        except requests.exceptions.ConnectionError as e:
            exit_response = print_url_unreachable(e)

        if exit_response:
            return error_collection

    if any(error != '0: Success' for error in error_collection):
        print(error_collection)
    return error_collection


if __name__ == "__main__":
    main(args=sys.argv)
