import os
import requests
from flask import Response, request, jsonify, render_template
import hashlib

from application.services.tools import decrypt_identifiers, track_api_time
from ..configs import swagger_config
from application.configs.config import VERIFY_CLASSMARKER_REQUESTS, FABMAN_API_KEY, MAIL_USERNAME,\
    MAX_COURSE_ATTEMPTS, CRONJOB_TOKEN, COURSES_WEB_PRIVATE_KEY
from . import main
from ..services.error_handlers import CustomError, error_handler
from ..services.api_functions import verify_payload, process_failed_attempt, add_training_to_member, \
    remove_failed_training_from_user, get_active_user_trainings_and_user_data, create_cm_link, \
    check_members_training, data_from_get_request, get_training_links_fn
from ..services.extensions import mail, Message, swag_from


@main.route("/add_classmarker_training", methods=["POST"])
@swag_from(swagger_config.cm_quiz_hook_schema)
@error_handler
def add_classmarker_training():
    """
    Endpoint for ClassMarker webhook
    """

    hmac_header = request.headers.get('X-Classmarker-Hmac-Sha256')
    request_data = request.json

    if VERIFY_CLASSMARKER_REQUESTS and not verify_payload(request.data, hmac_header.encode('ascii', 'ignore')):
        raise CustomError("Unauthorized webhook access")

    payload_status = request_data.get("payload_status")

    if payload_status == "verify":
        return Response({}, 200)

    identifiers = decrypt_identifiers(request_data["result"].get("cm_user_id"))
    member_id = int(identifiers.split("-")[0])
    training_id = int(identifiers.split("-")[1])

    member_data = data_from_get_request(
        f'https://fabman.io/api/v1/members/{member_id}?embed=trainings',
        FABMAN_API_KEY
    )

    training = data_from_get_request(
        f'https://fabman.io/api/v1/training-courses/{training_id}',
        FABMAN_API_KEY
    )

    attempts = process_failed_attempt(member_id, training_id, True, member_data=member_data,
                                      return_attempts=True, token=FABMAN_API_KEY)

    if not request_data["result"]["passed"]:
        # <<<---------------------- EMAIL: FAILED TRAINING, X ATTEMPTS LEFT---------------------->>>
        template = "failed_attempt.html" if attempts < MAX_COURSE_ATTEMPTS else "out_of_attempts.html"
        msg = Message("FabLab info - test failed", sender=MAIL_USERNAME, recipients=[member_data["emailAddress"]])
        msg.html = render_template(template, training_title=training["title"])
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
    msg = Message("FabLab info - test passed", sender=MAIL_USERNAME, recipients=[member_data["emailAddress"]])
    msg.html = render_template("succeed_attempt.html", training_title=training["title"])
    mail.send(msg)

    return Response("Training passed, updated in Fabman", 200)


@main.route("/absolved_trainings/<member_id>", methods=["GET"])
@swag_from(swagger_config.absolved_trainings_schema)
@track_api_time
@error_handler
def get_list_of_absolved_trainings(member_id: str):
    """
    List of member's active trainings
    """

    token = os.environ['FABMAN_API_KEY']
    trainings = get_active_user_trainings_and_user_data(member_id, token)[0]
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
    """
    List of all trainings available for online course
    """

    token = os.environ['FABMAN_API_KEY']
    user_active_trainings, user_data = get_active_user_trainings_and_user_data(member_id, token)

    trainings_url = "https://fabman.io/api/v1/training-courses?q=for_web"

    if user_data.get("privileges") != "admin":
        trainings_url += ",for_members"

    trainings = data_from_get_request(trainings_url, token)

    trainings_data = [{k: t[k] for k in ["id", "title", "metadata"]} for t in trainings]
    user_active_trainings_ids = [at["id"] for at in user_active_trainings]

    available_trainings_for_member = [t for t in trainings_data if t["id"] not in user_active_trainings_ids]
    for_render = []

    for t in available_trainings_for_member:
        t["quiz_url"] = create_cm_link(
            member_id,
            t["id"],
            available_trainings_for_member,
            token,
            member_data={"metadata": user_data["metadata"] or {}, "lockVersion": user_data["lockVersion"]}
        )

        del t["metadata"]

        for_render.append(t)

    return for_render


@main.route("/get_training_links", methods=["POST"])
@swag_from(swagger_config.training_urls_schema)
@error_handler
def get_training_links():
    """
    Training's detail
    """
    request_data = request.json

    return jsonify(get_training_links_fn(request_data, request.headers.get("Authorization")))


@main.route("/training_expiration", methods=["POST"])
@swag_from(swagger_config.expiration_schema)
@error_handler
def training_expiration():
    """
    Handle expiration of trainings
    """
    request_data = request.json
    member_id = request_data.get("member_id")

    if not member_id:
        raise ValueError("Missing member_id")

    if request.headers.get("CronjobToken") != CRONJOB_TOKEN:
        raise CustomError("Unauthorized access")

    public_key = hashlib.sha512(f'{member_id}{COURSES_WEB_PRIVATE_KEY}'.encode()).hexdigest()
    url = f'https://skoleni.fablabbrno.cz?id={member_id}&key={public_key}'

    member_data = data_from_get_request(f'https://fabman.io/api/v1/members/{member_id}', FABMAN_API_KEY)
    training_data = get_training_links_fn(request_data, FABMAN_API_KEY)

    # <<<---------------------- EMAIL: TRAINING EXPIRATION ---------------------->>>
    msg = Message("FabLab info - training expiration", sender=MAIL_USERNAME, recipients=[member_data["emailAddress"]])
    msg.html = render_template(
        "training_expiration.html",
        training_title=training_data.get("title"),
        training_url=url
    )
    mail.send(msg)

    return Response("", 200)


# ------------------------ !!!FUTURE!!! ------------------------
@main.route("/activities", methods=["POST"])
@error_handler
def activities_notifications():
    """
    Future functionality, event listener for disabled and re-enabled resources
    :return: info about resource
    """
    request_data = request.json

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
