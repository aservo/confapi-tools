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


def print_url_unreachable(error):
    print("\nURL can't be reached.\n")
    print(error)
    exit()


def print_http_error(http_response, let_through = 5000):
    print("An error occurred: " + str(http_response.status_code) + "\n" +
          requests.status_codes._codes[http_response.status_code][0])
    if http_response.status_code != let_through:
        exit()


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


def export_queue(key, queue_url):
    response_get_queue = requests.get(queue_url, auth=authentication_tuple)

    if response_get_queue.ok:
        while response_get_queue.status_code == 200:
            js = parse_json_body(response_get_queue.content)
            percentage = js["percentageComplete"]
            response_get_queue = requests.get(queue_url, auth=authentication_tuple)
            time.sleep(1)
            sys.stdout.write("\r%d%%" % percentage)
            sys.stdout.flush()

        if response_get_queue.status_code == 201:
            sys.stdout.write("\r%d%%" % 100)
            sys.stdout.flush()
            print()

            response_get_queue = requests.get(queue_url, auth=authentication_tuple)
            js = parse_json_header(response_get_queue.headers)
            zip_url = js['Location']
            export_download(key, zip_url)

    else:
        js = parse_json_body(response_get_queue.content)
        print(js["errorMessages"])
        exit()


def main():
    global authentication_tuple
    global export_resource

    parser = argparse.ArgumentParser(description="sample usage: \n python3 export.py base-url key1,key2 --username my_username --password my_password"
                                                 "\n python3 export.py http://localhost:1990/confluence KEY,ds --username admin --password admin \n or just: \n ./export http://localhost:1990/confluence KEY,ds --username admin --password admin\n ", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("host", help="provide host url e.g. http://localhost:1990/confluence")
    parser.add_argument("key", help="provide key e.g. KEY")
    parser.add_argument("--username", "-U", help="provide username e.g. admin; \nif not provided the user will be prompted to introduce username and password.", required=False)
    parser.add_argument("--password", "-P", help="provide password e.g. admin; \nif not provided the user will be prompted to introduce username and password.", required=False)
    args = parser.parse_args()
    username = args.username
    password = args.password

    if username is None or password is None:
        username = input("Username: ")
        password = getpass.getpass(prompt='Password: ', stream=None)
    authentication_tuple = (username, password)

    base_url = args.host
    key_list = args.key.split(',')

    for key in key_list:
        print("\nDownloading space " + key)

        # Build url
        suffix = "/" if base_url[-1] != "/" else ""
        request_page_url = base_url + suffix + export_resource + key

        # Try to connect
        response_request_page = requests.Response()
        try:
            response_request_page = requests.get(request_page_url, auth=authentication_tuple)
        except requests.exceptions.ConnectionError as e:
            print_url_unreachable(e)

        # Handle connection responses
        if not response_request_page.ok:
            print_http_error(response_request_page,404)

            js = parse_json_body(response_request_page.content)
            if "errorMessages" in js:
                print(js["errorMessages"])

            # space exists, upload other spaces
            if response_request_page.status_code == 404:
                continue
            exit()
        else:
            js = parse_json_header(response_request_page.headers)
            url = js['Location']

            if response_request_page.status_code == 201:
                print("100%")
                export_download(key, url)

            if response_request_page.status_code == 202:
                export_queue(key, url)


if __name__ == "__main__":
    main()
