import os
import requests
from datetime import datetime
from typing import List, Dict, Union
import traceback
from functools import wraps


RAILWAY_API_URL = os.getenv("RAILWAY_API_URL")
CRONJOB_TOKEN = os.getenv("CRONJOB_TOKEN")
FABMAN_API_KEY = os.getenv("FABMAN_API_KEY")


class CustomError(Exception):
    def __init__(self, description, error_data=None):
        self.args = (description, error_data)
        self.description = description
        self.data = error_data
        super().__init__()

    def __str__(self):
        return self.description


def expired_date(dt: str, date: bool = True) -> bool:
    """
    Compare specific date/datetime with current date/datetime and return if provided date is expired.
    :param dt: ISO string date ('2023-9-28')
    :param date: True if function should compare dates, False for comparing datetimes
    :return: bool - provided date is expired
    """
    dt = datetime(*[int(i) for i in dt.split("-")])

    if date:
        return dt.date() < datetime.now().date()

    return dt < datetime.now()


def data_from_get_request(url: str, token: str) -> Union[List, Dict]:
    """
    Function for GET requests with auth header, returning fetched data.
    :param url: API URL
    :param token: Fabman API token with admin permissions
    :raises Error during data fetching: request failed
    :return: data from GET request
    """
    res = requests.get(url, headers={"Authorization": f'{token}'})

    if res.status_code != 200:
        raise CustomError("Error during data fetching", f'{url}, {res.json()}')

    return res.json()


def send_expiration_notification(member_id: int, training_course_id: int) -> bool:
    res = requests.post(
        f'{RAILWAY_API_URL}/training_expiration',
        json={
            "member_id": member_id,
            "training_id": training_course_id
        },
        headers={"CronjobToken": f'{CRONJOB_TOKEN}'}
    )

    if res.status_code != 200:
        print(f'Error during {training_course_id} for user {member_id}')
        print(res.content)
    else:
        print(f'email with training {training_course_id} sent to user {member_id}')
    return res.status_code == 200


def remove_expired_course(member_id: int, user_course_id: int) -> bool:
    res = requests.delete(
        f'https://fabman.io/api/v1/members/{member_id}/trainings/{user_course_id}',
        headers={"Authorization": f'{FABMAN_API_KEY}'}
    )

    if res.status_code != 204:
        print(f'Error during removing {user_course_id} for user {member_id}')
        print(res.content)
    else:
        print(f'training {user_course_id} removed from user {member_id}')

    return res.status_code == 200


def railway_api_healtcheck() -> bool:
    res = requests.get(f'{RAILWAY_API_URL}/health', headers={"CronjobToken": f'{CRONJOB_TOKEN}'})

    if res.status_code != 200:
        print("Railway API is probably down")

    return res.status_code == 200


def error_handler(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        try:
            return f(*args, **kwargs)

        except Exception:
            print(traceback.format_exc())

    return decorator


@error_handler
def check_expired_trainings():
    """
    Check all trainings of all members. Send email notification and remove training if it's expired.
    """
    if requests.get(f'{RAILWAY_API_URL}/health').status_code != 200:
        return

    print("Starting expiration check")

    if os.getenv("TEST_USER"):
        members = [data_from_get_request(
            f'https://fabman.io/api/v1/members/{os.getenv("TEST_USER")}?embed=trainings',
            os.getenv("FABMAN_API_KEY")
        )]
        print(os.getenv("TEST_USER"), members)

    else:
        members = data_from_get_request("https://fabman.io/api/v1/members?embed=trainings", os.getenv("FABMAN_API_KEY"))
        print(members[:5])

    checked_trainings = 0
    expired_trainings = 0

    for m in members:
        for t in m["_embedded"]["trainings"]:
            checked_trainings += 1

            if not (expired_date(t["untilDate"]) if t.get("untilDate") else False):
                print(f'training {t["trainingCourse"]} is not expired for user {m["id"]}')
                continue

            expired_trainings += 1

            if send_expiration_notification(m["id"], t["trainingCourse"]):
                remove_expired_course(m["id"], t["id"])

    print(f'Checked {checked_trainings} trainings of {len(members)} members. Expired {expired_trainings} trainings.')

print("Module init")
if __name__ == "__main__":
    print("Should start")
    check_expired_trainings()
