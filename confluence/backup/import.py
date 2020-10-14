#!/usr/bin/env python3

import argparse
import fnmatch
import getpass
import json
import logging
import os
import requests
import sys
import time
import urllib3

urllib3.disable_warnings()

# constant variables
IMPORT_RESOURCE = "rest/confapi/1/backup/import"
terminate_script = [444, 403, 401]

# global variables
batch_mode = False
authentication_tuple = ()
error_collection = []


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
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="increase output verbosity.")
    parser.add_argument("-b", "--batch", action="store_true",
                        help="run in batch mode.")
    parser.add_argument("-U", "--username",
                        help="provide username e.g. admin;\n"
                             "if not provided the user will be prompted to enter a username and a password.")
    parser.add_argument("-P", "--password",
                        help="provide password e.g. admin;\n"
                             "if not provided the user will be prompted to enter a password.")

    return parser.parse_args(args[1:])


def print_url_unreachable(error):
    print("\nURL can't be reached.\n")
    print(error)
    return collect_error(444, "url not reachable")


def print_http_error(http_response):
    print("An error occurred: " + str(http_response.status_code) + "\n" +
          requests.status_codes._codes[http_response.status_code][0])
    return collect_error(http_response.status_code, requests.status_codes._codes[http_response.status_code][0])


def parse_json(content):
    try:
        content = content.decode("utf-8")
        result = json.loads(content)
    except:
        result = {}
    return result


def print_progress(title, percentage):
    if not batch_mode:
        sys.stdout.write("\r%s: %d%%" % (title, percentage))
        sys.stdout.flush()

        if percentage == 100:
            print()


def import_start(host, file):
    exit_response = 0
    print("\nStart importing space using file " + file)

    url_infix = "/" if host[-1] != "/" else ""
    url = "{}{}{}".format(host, url_infix, IMPORT_RESOURCE)

    # Ping server to verify credentials and permissions
    ping_server(host, url)

    try:
        print("Upload: No progress info available (yet)")
        import_response = requests.post(url, files={'file': open(file, 'rb')}, auth=authentication_tuple, verify=False)

        if not import_response.ok:
            content = parse_json(import_response.content)
            if "errorMessages" in content:
                print(content["errorMessages"])
            exit_response = print_http_error(import_response)
        else:
            if import_response.status_code == 201:
                print_progress("Import", 100)
            if import_response.status_code == 202:
                queue_url = import_response.headers['Location']
                import_queue(queue_url)
            collect_error(0, "Success")

    except requests.exceptions.ConnectionError as e:
        exit_response = print_url_unreachable(e)

    return exit_response


def import_queue(queue_url):
    while True:
        queue_response = requests.get(queue_url, auth=authentication_tuple, verify=False)

        if queue_response.ok:
            content = parse_json(queue_response.content)
            percentage = content["percentageComplete"]
            print_progress("Import", percentage)

        if queue_response.status_code != 200:
            break

        time.sleep(1)


def ping_server(baseurl, url):
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


def init_logging_mode(args):
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)


def init_batch_mode(args):
    global batch_mode
    batch_mode = args.batch


def init_authentication_tuple(args):
    global authentication_tuple

    username = args.username
    password = args.password

    if username is None:
        username = input("Username: ")
    if args.username is None or password is None:
        password = getpass.getpass(prompt='Password: ', stream=None)

    authentication_tuple = (username, password)


def main(argv):
    global error_collection
    error_collection = []

    args = parse_args(argv)

    init_logging_mode(args)
    init_batch_mode(args)
    init_authentication_tuple(args)

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
                file_names.append(directory + "/" + file)

    url_infix = "/" if args.host[-1] != "/" else ""
    url = "{}{}{}".format(args.host, url_infix, IMPORT_RESOURCE)

    # Ping server to verify credentials and permissions
    exit_response = ping_server(args.host, url)
    if exit_response:
        return error_collection

    print("\nImporting spaces using the following files:")
    for file in file_names:
        print("- " + file)

    for file in file_names:
        import_start(args.host, file)

        if exit_response:
            return error_collection

    if any(error != '0: Success' for error in error_collection):
        print(error_collection)
    return error_collection


if __name__ == "__main__":
    main(argv=sys.argv)
