import requests
from flask import Response, request, jsonify, session
from application.services.tools import decrypt_identifiers, filter_non_admins_trainings, track_api_time

from ..configs import swagger_config
from application.configs.config import VERIFY_CLASSMARKER_REQUESTS, FABMAN_API_KEY, MAIL_USERNAME, MAX_COURSE_ATTEMPTS
from . import main
from ..services.error_handlers import CustomError, error_handler
from ..services.api_functions import verify_payload, process_failed_attempt, add_training_to_member, \
    remove_failed_training_from_user, get_active_user_trainings_and_user_data, create_cm_link, \
    check_members_training, data_from_get_request
from ..services.extensions import mail, Message, swag_from


@main.route("/add_classmarker_training/", methods=["POST"])
@swag_from(swagger_config.cm_quiz_hook_schema)
@error_handler
def add_classmarker_training():
    hmac_header = request.headers.get('X-Classmarker-Hmac-Sha256')
    request_data = request.json

    if VERIFY_CLASSMARKER_REQUESTS and not verify_payload(request.data, hmac_header.encode('ascii', 'ignore')):
        raise CustomError("Unauthorized webhook access")

    identifiers = decrypt_identifiers(request_data["result"].get("cm_user_id"))
    member_id = int(identifiers.split("-")[0])
    training_id = int(identifiers.split("-")[1])

    member_data = data_from_get_request(
        f'https://fabman.io/api/v1/members/{member_id}?embed=trainings',
        FABMAN_API_KEY
    )

    if not request_data["result"]["passed"]:
        attempts = process_failed_attempt(member_id, training_id, True, member_data=member_data,
                                          return_attempts=True, token=FABMAN_API_KEY)

        # <<<---------------------- EMAIL: FAILED TRAINING, X ATTEMPTS LEFT---------------------->>>
        msg = Message('Test failed', sender=MAIL_USERNAME, recipients=[member_data["emailAddress"]])
        msg.body = f'You failed your test :( {MAX_COURSE_ATTEMPTS - attempts} attempts left'
        mail.send(msg)

        return Response("Failed attempt saved in Fabman", 200)

    expired_training_id = check_members_training(
        training_id,
        member_data["_embedded"]["trainings"] if member_data.get("_embedded") else []
    )

    add_training_to_member(member_id, training_id)
    remove_failed_training_from_user(member_data, member_id, training_id)

    if expired_training_id:
        res = requests.delete(
            f'https://fabman.io/api/v1/members/{member_id}/trainings/{expired_training_id}',
            headers={"Authorization": f'{FABMAN_API_KEY}'}
        )

        if res.status_code != 204:
            raise CustomError("Error during old training removing")

    print(f'User ID {member_id} absolved training ID {training_id}')

    # <<<---------------------- EMAIL: TRAINING PASSED ---------------------->>>
    msg = Message('Test passed', sender=MAIL_USERNAME, recipients=[member_data["emailAddress"]])
    msg.body = "You passed the test! Now you can use the device."
    mail.send(msg)

    return Response("Training passed, updated in Fabman", 200)


@main.route("/absolved_trainings/<member_id>", methods=["GET"])
@swag_from(swagger_config.absolved_trainings_schema)
@track_api_time
@error_handler
def get_list_of_absolved_trainings(member_id: str):
    trainings = get_active_user_trainings_and_user_data(member_id, request.headers.get("Authorization"))[0]
    res = []

    for t in trainings:
        if "metadata" in t.keys():
            del t["metadata"]

        res.append(t)

    return res


@main.route("/available_trainings/<member_id>", methods=["GET"])
@swag_from(swagger_config.available_trainings_schema)
@track_api_time
@error_handler
def get_list_of_available_trainings(member_id: str):
    token = request.headers.get("Authorization")
    user_active_trainings, user_data = get_active_user_trainings_and_user_data(member_id, token)
    trainings = data_from_get_request("https://fabman.io/api/v1/training-courses", token)

    trainings_data = [{k: t[k] for k in ["id", "title", "metadata"]} for t in trainings if t.get("metadata") and t["metadata"].get("for_web")]
    user_active_trainings_ids = [at["id"] for at in user_active_trainings]

    available_trainings_for_member = [t for t in trainings_data if t["id"] not in user_active_trainings_ids]

    if user_data["privileges"] != "admin":
        available_trainings_for_member = filter_non_admins_trainings(available_trainings_for_member)

    for_render = []

    for t in available_trainings_for_member:
        t["quiz_url"] = create_cm_link(
            member_id,
            t["id"],
            available_trainings_for_member,
            token,
            member_data={"metadata": user_data["metadata"], "lockVersion": user_data["lockVersion"]}
        )

        del t["metadata"]

        for_render.append(t)

    return for_render


# ------------------------ !!!DEVELOPMENT!!! ------------------------
@main.route("/create_cm_link", methods=["POST"])
@swag_from(swagger_config.cm_urls_schema)
@error_handler
def create_quiz_link():
    """
    TEST API for URL function
    """
    request_data = request.json

    member_id = request_data.get("member_id")
    training_id = request_data.get("training_id")
    base_quiz_url = request_data.get("base_quiz_url")
    token = request.headers.get("Authorization")

    training = {
        "id": training_id,
        "metadata": {"cm_url": base_quiz_url}
    }

    if not base_quiz_url:
        training = data_from_get_request(f'https://fabman.io/api/v1/training-courses/{training_id}', token)

    link = create_cm_link(
        member_id,
        training_id,
        [training],
        token
    )
    return Response(link, 200)

# ------------------------ !!!DEVELOPMENT!!! ------------------------


# ------------------------ !!!FUTURE!!! ------------------------
@main.route("/activities", methods=["POST"])
@error_handler
def activities_notifications():
    """
    Future functionality, event listener for disabled and re-enabled resources.
    :return: info about resource
    """
    request_data = request.json
    print("REQUEST DATA", request_data)
    if request_data.get("type") != "resource_updated":
        return Response("Not a resource update event, ignored", 200)

    event_created = request_data["createdAt"]
    equipment_data = request_data["details"].get("resource") or {}
    target_data = ["name", "state", "maintenanceNotes", "updatedBy"]
    data = {key: value for key, value in equipment_data.items() if key in target_data}
    data["createdAt"] = event_created
    print("DATA FOR WEBHOOK", data)
    requests.post(
        "https://discord-controller-production.up.railway.app/activities",
        json=data
    )

    return jsonify(data)
# ------------------------ !!!FUTURE!!! ------------------------
