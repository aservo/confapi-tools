#!/usr/bin/env python3

import argparse
import fnmatch
import getpass
import json
import os
import requests
import sys
import time
import urllib3

urllib3.disable_warnings()

IMPORT_RESOURCE = "rest/confapi/1/backup/import"

authentication_tuple = ("admin", "admin")
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


def parse_args(args):
    parser = argparse.ArgumentParser(
        description="sample usage: \n"
                    "python3 import.py base-url unix-wildcard1 unix-wildcard2 --username user --password pass\n"
                    "python3 import.py http://localhost:1990/confluence export.zip --username admin --password admin\n"
                    "or just: \n"
                    "./import.py http://localhost:1990/confluence *.xml.zip --username admin --password admin",
        formatter_class=argparse.RawTextHelpFormatter)

    # positional arguments
    parser.add_argument("host", help="provide host url e.g. http://localhost:1990/confluence")
    parser.add_argument('vars', nargs='*', help="provide list of unix wildcards e.g. *.zip *.xml")

    # optional arguments
    parser.add_argument("--username", "-U",
                        help="provide username e.g. admin;\n"
                             "if not provided the user will be prompted to enter a username and a password.")
    parser.add_argument("--password", "-P",
                        help="provide password e.g. admin;\n"
                             "if not provided the user will be prompted to enter a password.")
    parser.add_argument("--batch", "-b", action="store_true",
                        help="run in batch mode.")

    return parser.parse_args(args[1:])


def print_url_unreachable(error):
    print("\nURL can't be reached.\n")
    print(error)
    return collect_error(444, "url not reachable")


def print_http_error(http_response):
    print("An error occurred: " + str(http_response.status_code) + "\n" +
          requests.status_codes._codes[http_response.status_code][0])
    return collect_error(http_response.status_code, requests.status_codes._codes[http_response.status_code][0])


def parse_json_body(body):
    try:
        body = body.decode("utf-8")
        result = json.loads(body)
    except Exception as e:
        result = {}
    return result


def import_start(host, file):
    exit_response = 0
    print("\nStart importing space from " + file)

    url_infix = "/" if host[-1] != "/" else ""
    url = "{}{}{}".format(host, url_infix, IMPORT_RESOURCE)

    # Ping server to verify credentials and permissions
    ping_server(host, url)

    try:
        # Try to connect
        response = requests.put(url, files={'file': open(file, 'rb')}, auth=authentication_tuple, verify=False)

        # Handle connection responses
        if not response.ok:
            js = parse_json_body(response.content)
            if "errorMessages" in js:
                print(js["errorMessages"])
            exit_response = print_http_error(response)
        else:
            if response.status_code == 201:
                print("100%")
            if response.status_code == 202:
                queue_url = response.headers['Location']
                import_queue(queue_url)
            collect_error(0, "Success")

    except requests.exceptions.ConnectionError as e:
        exit_response = print_url_unreachable(e)

    return exit_response


def import_queue(queue_url):
    response_get_queue = requests.get(queue_url, auth=authentication_tuple, verify=False)

    while response_get_queue.status_code == 200:
        js = parse_json_body(response_get_queue.content)
        percentage = js["percentageComplete"]
        response_get_queue = requests.get(queue_url, auth=authentication_tuple, verify=False)
        time.sleep(1)
        if not batch_mode:
            sys.stdout.write("\r%d%%" % percentage)
            sys.stdout.flush()
    if not batch_mode:
        sys.stdout.write("\r%d%%" % 100)
        sys.stdout.flush()
        print()


def ping_server(baseurl, url):
    # PING server
    try:
        resp_get = requests.get(baseurl, auth=authentication_tuple, verify=False)
        resp_put = requests.put(url, auth=authentication_tuple, verify=False)
    except requests.exceptions.ConnectionError as e:
        return print_url_unreachable(e)

    if not resp_get.ok:
        return print_http_error(resp_get)

    if not resp_put.ok:
        if resp_put.status_code == 403:
            return print_http_error(resp_put)


def main(argv):
    global authentication_tuple
    global error_collection
    global batch_mode
    error_collection = []

    args = parse_args(argv)

    username = args.username
    password = args.password

    if username is None:
        username = input("Username: ")
    if username is None or password is None:
        password = getpass.getpass(prompt='Password: ', stream=None)

    authentication_tuple = (username, password)

    file_wildcards = args.vars
    file_names = []
    for wildcard in file_wildcards:
        directory = '.'
        if "/" in wildcard:
            pos = wildcard.rfind('/')
            directory = wildcard[0:pos]
            wildcard = wildcard[pos + 1:]
        for file in os.listdir(directory):
            if fnmatch.fnmatch(file, wildcard):
                file_names.append(file)
    print(file_names)

    url_infix = "/" if args.host[-1] != "/" else ""
    url = "{}{}{}".format(args.host, url_infix, IMPORT_RESOURCE)

    # Ping server to verify credentials and permissions
    exit_response = ping_server(args.host, url)
    if exit_response:
        return error_collection

    batch_mode = False
    if args.batch:
        batch_mode = True

    for file in file_names:
        import_start(args.host, file)

        if exit_response:
            return error_collection

    if any(error != '0: Success' for error in error_collection):
        print(error_collection)
    return error_collection


if __name__ == "__main__":
    main(argv=sys.argv)
