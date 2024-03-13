from flask import Flask, Response
from typing import Tuple
import traceback
from functools import wraps

from ..services.extensions import mail, Message
from ..configs.config import MAIL_USERNAME


class CustomError(Exception):
    def __init__(self, description, error_data=None):
        self.args = (description, error_data)
        self.description = description
        self.data = error_data
        super().__init__()


def handle_exception(fn_name: str, e: Exception) -> Response:
    error = e.__class__.__name__

    if isinstance(e, CustomError):
        print(e.description, e.data)
        error = e.description

    else:
        print(error, e.args)

    print(traceback.format_exc())

    if fn_name == "add_classmarker_training":
        msg = Message('Test failed', sender=MAIL_USERNAME, recipients=[MAIL_USERNAME])
        msg.body = f'An error appeared during ClassMarker test processing: {error}'
        mail.send(msg)

    return Response(f'Error: {error}, for more information check applications log', 200)


def error_handler(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        try:
            return f(*args, **kwargs)

        except Exception as e:
            return handle_exception(f.__name__, e)

    return decorator
