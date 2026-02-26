from dataclasses import replace

import request
def extract_credentials(request):
    #dictionary for encoding strings in password
    encode_strings = {
        "%21": "!",
        "%40": "@",
        "%23": "#",
        "%24": "$",
        "%25": "%",
        "%5E": "^",
        "%26": "&",
        "%28": "(",
        "%29": ")",
        "%2D": "-",
        "%5F": "_",
        "%3D": "="
    }

    data = request.body.decode()
    body = data.split("&",1)
    username_part = body[0].split("=",1)
    username = username_part[1]
    password_part  = body[1].split("=",1)
    password = password_part[1]
    for key in encode_strings:
        password = password.replace(key,encode_strings[key])

    return [username,password]

def validate_password(password):
    #length of password must be at least 8
    #password must contain at least 1 uppercase character
    #password must contain at least 1 lowercase character
    #password must contain at least 1 number
    #passowrd must contain at least 1 special character
    #passowrd must not contain any invalid characters, characters outside of the 12 encoded special character.

    if len(password) < 8:
        return False

    isLower = False
    isUpper = False
    containsSpecial = False
    containsNum = False

    special = [
        '!', '@', '#', '$', '%', '^',
        '&', '(', ')', '-', '_', '='
    ]

    for char in password:
        if char.islower():
            isLower = True
        elif char.isupper():
            isUpper = True
        elif char.isnumeric():
            containsNum = True
        elif char in special:
            containsSpecial = True
        else:
            return False

        return isLower and isUpper and containsSpecial and containsNum