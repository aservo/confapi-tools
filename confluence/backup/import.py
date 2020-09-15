#!/usr/bin/env python3

import requests
import time
import sys
import json
import os
import fnmatch
import argparse
import getpass

authentication_tuple = ("admin", "admin")


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
    res = str(headers).replace('"', '\\"')
    res = str(res).replace("'", '"')
    return json.loads(res)


def parse_json_body(body):
    try:
        body = body.decode("utf-8")
        result = json.loads(body)
    except Exception as e:
        result = {}
    return result


def handle_asynchronous(queue_url):
    response_get_queue = requests.get(queue_url, auth=authentication_tuple)
    while response_get_queue.status_code == 200:
        js = parse_json_body(response_get_queue.content)
        percentage = js["percentageComplete"]
        response_get_queue = requests.get(queue_url, auth=authentication_tuple)
        time.sleep(1)
        sys.stdout.write("\r%d%%" % percentage)
        sys.stdout.flush()
    sys.stdout.write("\r%d%%" % 100)
    sys.stdout.flush()
    print()


def ping_server(baseurl, url):
    # PING server
    try:
        resp_get = requests.get(baseurl, auth=authentication_tuple)
        resp_put = requests.put(url, auth=authentication_tuple)
    except requests.exceptions.ConnectionError as e:
        print_url_unreachable(e)

    if not resp_get.ok:
        print_http_error(resp_get)

    if not resp_put.ok:
        if resp_put.status_code == 403:
            print_http_error(resp_put)


def main():
    global authentication_tuple

    parser = argparse.ArgumentParser(
        description="sample usage: \n python3 import.py base-url unix-wildcard1 unix-wildcard2 --username my_username --password my_password"
                    "\n python3 import.py http://localhost:1990/confluence Confluence.zip *.zip --username admin --password admin\n or just: \n ./import http://localhost:1990/confluence Confluence.zip *.xml.zip --username admin --password admin",
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("host", help="provide host url e.g. http://localhost:1990/confluence")
    parser.add_argument('vars', nargs='*', help="provide list of unix wildcards e.g. *.zip *.xml")
    parser.add_argument("--username", "-U",
                        help="provide username e.g. admin; \nif not provided the user will be prompted to introduce username and password.",
                        required=False)
    parser.add_argument("--password", "-P",
                        help="provide password e.g. admin; \nif not provided the user will be prompted to introduce username and password.",
                        required=False)
    args = parser.parse_args()

    username = args.username
    password = args.password
    if username is None or password is None:
        username = input("Username: ")
        password = getpass.getpass(prompt='Password: ', stream=None)
    authentication_tuple = (username, password)

    file_wildcards = args.vars
    file_names = []

    for file in os.listdir('.'):
        for wildcard in file_wildcards:
            if fnmatch.fnmatch(file, wildcard):
                file_names.append(file)
    print(file_names)

    for file in file_names:
        print("\nUploading " + file)

        # Create link
        multipart_form_dict = {'file': open(file, 'rb')}
        suffix = "/" if args.host[-1] != "/" else ""
        url = args.host + suffix + "rest/confapi/1/backup/import"

        # Ping server to verify credentials and permissions
        ping_server(args.host, url)

        # Try to connect
        response = requests.Response()
        try:
            response = requests.put(url, files=multipart_form_dict, auth=authentication_tuple)
        except requests.exceptions.ConnectionError as e:
            print_url_unreachable(e)

        # Handle connection responses
        if not response.ok:
            js = parse_json_body(response.content)
            if "errorMessages" in js:
                print(js["errorMessages"])
            print_http_error(response,400)
        else:
            if response.status_code == 201:
                print("100%")
            if response.status_code == 202:
                js = parse_json_header(response.headers)
                queue_url = js['Location']
                handle_asynchronous(queue_url)


if __name__ == "__main__":
    main()
