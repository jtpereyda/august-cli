import argparse
import datetime
import json
import sys
import time

from pprint import pprint

import dateutil.parser

from august.api import Api
from august.authenticator import Authenticator, AuthenticationState
from august import api_common
from august.api_common import API_BASE_URL
import august

API_GET_USERS_URL = API_BASE_URL + "/users"
API_ADD_USER_URL = API_BASE_URL + "/unverifiedusers"
API_UPDATE_USER_URL = API_BASE_URL + "/locks/{lock_id}/users/{user_id}/pin"
API_SYNC_PINS_URL = API_BASE_URL + "/locks/{lock_id}/pins/sync"


# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.


def main():
    api = Api(timeout=20)
    token_filename = "token"
    try:
        with open(token_filename, "r") as f:
            token = json.load(f)["access_token"]
    except FileNotFoundError:
        token = None

    if token is None:
        authenticator = Authenticator(api, "email", "joshua.t.pereyda@gmail.com", "",
                                      access_token_cache_file=token_filename)

        authentication = authenticator.authenticate()

        # State can be either REQUIRES_VALIDATION, BAD_PASSWORD or AUTHENTICATED
        # You'll need to call different methods to finish authentication process, see below
        state = authentication.state
        print(f"state: {state}")

        # If AuthenticationState is BAD_PASSWORD, that means your login_method, username and password do not match

        # If AuthenticationState is AUTHENTICATED, that means you're authenticated already. If you specify "access_token_cache_file", the authentication is cached in a file. Everytime you try to authenticate again, it'll read from that file and if you're authenticated already, Authenticator won't call August again as you have a valid access_token

        # If AuthenticationState is REQUIRES_VALIDATION, then you'll need to go through verification process
        # send_verification_code() will send a code to either your phone or email depending on login_method
        if state == AuthenticationState.REQUIRES_VALIDATION:
            authenticator.send_verification_code()
            code = input("Please enter verification code:")
            validation_result = authenticator.validate_verification_code(code)

            # If ValidationResult is INVALID_VERIFICATION_CODE, then you'll need to either enter correct one or resend by calling send_verification_code() again
            while True:
                if validation_result == august.authenticator.ValidationResult.INVALID_VERIFICATION_CODE:
                    code = input("Please enter verification code:")
                    validation_result = authenticator.validate_verification_code(code)
                elif validation_result == august.authenticator.ValidationResult.VALIDATED:
                    break
                else:
                    raise Exception(f"Unexpected validation state: {validation_result}")

        # If ValidationResult is VALIDATED, then you'll need to call authenticate() again to finish authentication process
        authentication = authenticator.authenticate()
        token = authentication.access_token

    parser = argparse.ArgumentParser(description="CLI for August API")
    subparsers = parser.add_subparsers()

    house = subparsers.add_parser('house', help='houses')
    subparsers_house = house.add_subparsers()
    house_list = subparsers_house.add_parser('list', help='list houses')
    house_list.set_defaults(func=cli_house_list)
    house_get = subparsers_house.add_parser('get', help='get house details')
    house_get.add_argument("name")
    house_get.set_defaults(func=cli_house_get)

    lock = subparsers.add_parser('lock', help='locks')
    subparsers_lock = lock.add_subparsers()
    lock_list = subparsers_lock.add_parser('list', help='list locks')
    lock_list.add_argument("house", nargs="?", help="get locks for a specific house name")
    lock_list.set_defaults(func=cli_lock_list)
    lock_get = subparsers_lock.add_parser('get', help='get lock details')
    lock_get.add_argument("house", help="house name")
    lock_get.add_argument("lock", help="lock name")
    lock_get.set_defaults(func=cli_lock_get)

    user = subparsers.add_parser('user', help='users')
    subparsers_user = user.add_subparsers()
    user_list = subparsers_user.add_parser('list', help='list users')
    # user_list.add_argument("house", nargs="?", help="get users for a specific house name")
    user_list.set_defaults(func=cli_user_list)
    user_add = subparsers_user.add_parser('add', help='add user')
    user_add.add_argument("house", help="house name")
    user_add.add_argument("lock", help="lock name")
    user_add.add_argument("first_name", help="first name")
    user_add.add_argument("last_name", help="last name")
    user_add.add_argument("--start", help="start time")
    user_add.add_argument("--end", help="end time")
    # user_list.add_argument("house", nargs="?", help="get users for a specific house name")
    user_add.set_defaults(func=cli_user_add)

    args = parser.parse_args()
    args.func(args, api, token)

    return

    # Once you have authenticated and validated you can use the access token to make API calls
    locks = api.get_locks(token)
    print(locks)
    for lock in locks:
        details = api.get_lock_detail(token, lock.device_id)
        print(f"{lock.device_id}:")
        pprint(details.data)
        pins = api.get_pins(token, lock.device_id)
        pprint(pins)
        for pin in pins:
            pprint(pin.data)

    pin = api.get_pin(token, lock.device_id, "61de59d3bbfc7d8ff6e02bb6")
    pprint(pin)


def cli_user_list(args, api, token):
    users = api._dict_to_api({"method": "get", "url": API_GET_USERS_URL, "access_token": token}).json()
    pprint(users)
    # for lock in locks:
    #     pprint(lock.data)


def cli_user_add(args, api, token):
    house = args.house
    lock = args.lock
    first_name = args.first_name
    last_name = args.last_name
    start = args.start
    end = args.end

    start_time = (dateutil.parser.parse(start) + datetime.timedelta(seconds=time.timezone)).isoformat(timespec='milliseconds')+'Z'
    end_time = (dateutil.parser.parse(end) + datetime.timedelta(seconds=time.timezone)).isoformat(timespec='milliseconds')+'Z'

    lock_obj = get_lock(house, lock, api, token)
    lock_id = lock_obj.device_id

    add_user(first_name, last_name, start_time, end_time, lock_id, api, token)


def add_user(first_name, last_name, start_time, end_time, lock_id, api, token):
    """ Add a user to a lock

    Reverse engineering notes:
    - Timestamp error messages give us a prescribed format: "must follow pattern YYYY-MM-DDTHH:mm:ss.SSSZ"
    """
    resp = api._dict_to_api({"method": "post", "url": API_ADD_USER_URL.format(), "access_token": token,
                             "json":
                                 {'lockID': lock_id,
                                  'firstName': first_name,
                                  'lastName': last_name,
                                  }
                             }
                            )
    print(resp.status_code)
    pprint(resp.json())
    new_user = resp.json()
    new_id = new_user['id']

    resp = api._dict_to_api({"method": "put", "url": API_UPDATE_USER_URL.format(lock_id=lock_id, user_id=new_id), "access_token": token,
                             "json": {
                                 "state": "load",
                                 "action": "intent",
                                 "pin": new_user["pin"],
                                 'accessType': 'temporary',
                                 # 'accessTimes': 'DTSTART=2022-02-07T23:00:00.000Z;DTEND=2022-02-08T19:05:00.000Z',
                                 'accessTimes': f'DTSTART={start_time};DTEND={end_time}',
                             },
                             })
    print(resp.status_code)
    pprint(resp.json())

    resp = api._dict_to_api({"method": "put", "url": API_UPDATE_USER_URL.format(lock_id=lock_id, user_id=new_id), "access_token": token,
                             "json": {
                                 "state": "load",
                                 "action": "commit",
                                 "pin": new_user["pin"],
                                 'accessType': 'temporary',
                                 # 'accessTimes': 'DTSTART=2022-02-07T23:00:00.000Z;DTEND=2022-02-08T19:05:00.000Z',
                                 'accessTimes': f'DTSTART={start_time};DTEND={end_time}',
                             },
                             })
    print(resp.status_code)
    pprint(resp.json())

    resp = api._dict_to_api({"method": "put", "url": API_UPDATE_USER_URL.format(lock_id=lock_id, user_id=new_id), "access_token": token,
                             "json": {
                                 "state": "disable",
                                 "action": "intent",
                                 "pin": new_user["pin"],
                                 'accessType': 'temporary',
                                 # 'accessTimes': 'DTSTART=2022-02-07T23:00:00.000Z;DTEND=2022-02-08T19:05:00.000Z',
                                 'accessTimes': f'DTSTART={start_time};DTEND={end_time}',
                             },
                             })
    print(resp.status_code)
    pprint(resp.json())

    resp = api._dict_to_api({"method": "put", "url": API_UPDATE_USER_URL.format(lock_id=lock_id, user_id=new_id), "access_token": token,
                             "json": {
                                 "state": "disable",
                                 "action": "commit",
                                 "pin": new_user["pin"],
                                 'accessType': 'temporary',
                                 # 'accessTimes': 'DTSTART=2022-02-07T23:00:00.000Z;DTEND=2022-02-08T19:05:00.000Z',
                                 'accessTimes': f'DTSTART={start_time};DTEND={end_time}',
                             },
                             })
    print(resp.status_code)
    pprint(resp.json())

    resp = api._dict_to_api({"method": "put", "url": API_UPDATE_USER_URL.format(lock_id=lock_id, user_id=new_id), "access_token": token,
                             "json": {
                                 "state": "enable",
                                 "action": "intent",
                                 "pin": new_user["pin"],
                                 'accessType': 'temporary',
                                 # 'accessTimes': 'DTSTART=2022-02-07T23:00:00.000Z;DTEND=2022-02-08T19:05:00.000Z',
                                 'accessTimes': f'DTSTART={start_time};DTEND={end_time}',
                             },
                             })
    print(resp.status_code)
    pprint(resp.json())

    resp = api._dict_to_api({"method": "put", "url": API_UPDATE_USER_URL.format(lock_id=lock_id, user_id=new_id), "access_token": token,
                             "json": {
                                 "state": "enable",
                                 "action": "commit",
                                 "pin": new_user["pin"],
                                 'accessType': 'temporary',
                                 # 'accessTimes': 'DTSTART=2022-02-07T23:00:00.000Z;DTEND=2022-02-08T19:05:00.000Z',
                                 'accessTimes': f'DTSTART={start_time};DTEND={end_time}',
                             },
                             })
    print(resp.status_code)
    pprint(resp.json())

    # Sync URL doesn't seem to help. interestingly it returns "{'numRecords': 0}"
    resp = api._dict_to_api({"method": "put", "url": API_SYNC_PINS_URL.format(lock_id=lock_id), "access_token": token,
                             "json": {"pin": new_user["pin"]},
                             })
    print(resp.status_code)
    pprint(resp.json())
    return


def cli_house_list(args, api, token):
    resp = api.get_houses(token)
    pprint(resp.json())


def cli_house_get(args, api, token):
    name = args.name
    details = get_house(name, api, token)
    pprint(details)


def get_house(name, api, token):
    houses = api.get_houses(token).json()
    house_id = None
    for house in houses:
        if house["HouseName"] == name:
            house_id = house["HouseID"]
            break
    if house_id is None:
        print(f"error: House name not found: {name}", file=sys.stderr)
        return
    details = api.get_house(token, house_id)
    return details


def cli_lock_list(args, api, token):
    house = args.house
    locks = api.get_locks(token)
    if house is not None:
        house_details = get_house(house, api, token)
        locks = [l for l in locks if l.house_id == house_details["HouseID"]]
    # pprint(locks)
    for lock in locks:
        pprint(lock.data)


def cli_lock_get(args, api, token):
    house = args.house
    lock = args.lock
    lock_obj = get_lock(house, lock, api, token)
    print(lock_obj)
    pprint(lock_obj.data)


def get_lock(house, lock, api, token):
    locks = api.get_locks(token)
    if house is not None:
        house_details = get_house(house, api, token)
        locks = [l for l in locks if l.house_id == house_details["HouseID"]]
    if lock is not None:
        locks = [l for l in locks if l.device_name == lock]
    if len(locks) > 1:
        print(f"warning: multiple locks found for {house}/{lock}", file=sys.stderr)
    elif len(locks) == 0:
        raise Exception(f"error: no locks found for {house}/{lock}")
    lock = locks[0]
    lock_obj = api.get_lock_detail(token, lock.device_id)
    return lock_obj


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
