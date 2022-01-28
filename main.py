from pprint import pprint

from august.api import Api
from august.authenticator import Authenticator, AuthenticationState
import august

import json

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


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
