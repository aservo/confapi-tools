#!/usr/bin/env python3

import argparse
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
EXPORT_RESOURCE = "rest/confapi/1/backup/export"
terminate_script = [401, 403, 444]

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
                    "python3 export.py base-url key1,key2 --username my_username --password my_password\n"
                    "python3 export.py http://localhost:1990/confluence KEY,ds --username admin --password admin\n"
                    "or just:\n"
                    "./export.py http://localhost:1990/confluence KEY,ds --username admin --password  admin\n",
        formatter_class=argparse.RawTextHelpFormatter)

    # positional arguments
    parser.add_argument("host", help="provide host url e.g. http://localhost:1990/confluence")
    parser.add_argument("key", help="provide key e.g. KEY")

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


def export_start(host, key):
    exit_response = 0
    print("\nStart exporting space using key " + key)

    url_infix = "/" if host[-1] != "/" else ""
    url = "{}{}{}/{}".format(host, url_infix, EXPORT_RESOURCE, key)

    try:
        export_response = requests.get(url, auth=authentication_tuple, verify=False)

        if not export_response.ok:
            exit_response = print_http_error(export_response)

            content = parse_json(export_response.content)
            if "errorMessages" in content:
                print(content["errorMessages"])

        else:
            location = export_response.headers['Location']

            if export_response.status_code == 201:
                export_download(location, key)

            if export_response.status_code == 202:
                exit_response = export_queue(location, key)

    except requests.exceptions.ConnectionError as e:
        exit_response = print_url_unreachable(e)

    return exit_response


def export_queue(queue_url, key):
    while True:
        queue_response = requests.get(queue_url, auth=authentication_tuple, verify=False)

        if queue_response.status_code != 200:
            if queue_response.status_code == 201:
                location = queue_response.headers['Location']
                return export_download(location, key)
            elif not queue_response.ok:
                content = parse_json(queue_response.content)
                print(content["errorMessages"])
                return collect_error(str(queue_response.status_code) + ": "
                                     + requests.status_codes._codes[queue_response.status_code][0])
            break

        content = parse_json(queue_response.content)
        percentage = content["percentageComplete"]
        print_progress("Export", percentage)
        time.sleep(1)
    return 1


def export_download(download_url, key):
    print_progress("Export", 100)

    download_file = os.getcwd() + "/Confluence-space-export-" + key + ".xml.zip"
    with open(download_file, 'wb') as fd:
        download_response = requests.get(download_url, stream=True, auth=authentication_tuple, verify=False)
        download_size = download_response.headers['Content-Length']
        download_progress = 0.0

        for chunk in download_response.iter_content(chunk_size=4096):
            fd.write(chunk)

            if download_size is not None:
                download_progress += len(chunk)
                print_progress("Download", int(100 * download_progress / int(download_size)))

    return collect_error(0, "Success")


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

    print("\nExporting spaces using the following keys:")
    for key in args.key.split(','):
        print("- " + key)

    for key in args.key.split(','):
        exit_response = export_start(args.host, key)

        if exit_response:
            return error_collection

    if any(error != '0: Success' for error in error_collection):
        print(error_collection)
    return error_collection


if __name__ == "__main__":
    main(argv=sys.argv)
