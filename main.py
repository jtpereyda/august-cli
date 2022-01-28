import argparse
import json
import sys

from pprint import pprint

from august.api import Api
from august.authenticator import Authenticator, AuthenticationState
import august

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
    subparsers_house = lock.add_subparsers()
    lock_list = subparsers_house.add_parser('list', help='list locks')
    lock_list.add_argument("house", nargs="?", help="get locks for a specific house name")
    lock_list.set_defaults(func=cli_lock_list)
    lock_get = subparsers_house.add_parser('get', help='get lock details')
    lock_get.add_argument("house", help="house name")
    lock_get.add_argument("lock", help="lock name")
    lock_get.set_defaults(func=cli_lock_get)

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
    locks = api.get_locks(token)
    if house is not None:
        house_details = get_house(house, api, token)
        locks = [l for l in locks if l.house_id == house_details["HouseID"]]
    if lock is not None:
        locks = [l for l in locks if l.device_name == lock]
    for lock in locks:
        lock_obj = api.get_lock_detail(token, lock.device_id)
        print(lock_obj)
        pprint(lock_obj.data)




# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
