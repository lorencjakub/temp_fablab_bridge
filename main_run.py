import os
import requests
from flask import Flask, Response, request, jsonify
import traceback
from tools import decrypt_identifiers, filter_non_admins_trainings
from functions import verify_payload, process_failed_attempt, add_training_to_member, \
    remove_failed_training_from_user, get_active_user_trainings_and_user_data, create_cm_link, \
    check_members_training, data_from_get_request
from flasgger import Swagger, swag_from
import swagger_config


app = Flask("classmarker_fabman_bridge")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", default="")

swagger = Swagger(app)

MAX_COURSE_ATTEMPTS = os.environ.get("MAX_COURSE_ATTEMPTS", default=3)
FERNET_KEY = os.environ.get("FERNET_KEY", default="")
FABMAN_API_KEY = os.environ.get("FABMAN_API_KEY", default="")
CLASSMARKER_WEBHOOK_SECRET = os.environ.get("CLASSMARKER_WEBHOOK_SECRET", default="")


@app.route("/add_classmarker_training/", methods=["POST"])
@swag_from(swagger_config.cm_quiz_hook_schema)
def add_classmarker_training():
    try:
        hmac_header = request.headers.get('X-Classmarker-Hmac-Sha256')
        request_data = request.json

        if not verify_payload(request.data, hmac_header.encode('ascii', 'ignore')):
            raise Exception("Unauthorized webhook access")

        identifiers = decrypt_identifiers(request_data["result"].get("cm_user_id"))
        member_id = int(identifiers.split("-")[0])
        training_id = int(identifiers.split("-")[1])

        if not request_data["result"]["passed"]:
            process_failed_attempt(member_id, training_id, True)

            # <<<---------------------- EMAIL: FAILED TRAINING, X ATTEMPTS LEFT---------------------->>>

            return Response("Failed attempt saved in Fabman", 200)

        member_data = data_from_get_request(
            f'https://fabman.io/api/v1/members/{member_id}?embed=trainings',
            FABMAN_API_KEY
        )
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
                raise Exception("Error during old training removing")

        print(f'User ID {member_id} absolved training ID {training_id}')

        # <<<---------------------- EMAIL: TRAINING PASSED ---------------------->>>

        return Response("Training passed, updated in Fabman", 200)

    except Exception as e:
        print(traceback.format_exc())

        # <<<---------------------- EMAIL: PROCESS FAILED ---------------------->>>

        return Response(f'Error: {e.args}', 400)


@app.route("/absolved_trainings/<member_id>", methods=["GET"])
@swag_from(swagger_config.absolved_trainings_schema)
def get_list_of_absolved_trainings(member_id: str):
    try:
        return jsonify(get_active_user_trainings_and_user_data(member_id, request.headers.get("Authorization"))[0])

    except Exception as e:
        print(traceback.format_exc())

        return Response(f'Error: {e.args}', 400)


@app.route("/available_trainings/<member_id>", methods=["GET"])
@swag_from(swagger_config.available_trainings_schema)
def get_list_of_available_trainings(member_id: str):
    try:
        token = request.headers.get("Authorization")

        user_active_trainings, user_data = get_active_user_trainings_and_user_data(member_id, token)
        trainings = data_from_get_request("https://fabman.io/api/v1/training-courses", token)
        available_trainings_for_member = [
            t for t in trainings
            if not any((ut for ut in user_active_trainings if t["id"] == ut["trainingCourse"]))
        ]

        if user_data["_embedded"]["privileges"]["privileges"] != "admin":
            available_trainings_for_member = filter_non_admins_trainings(available_trainings_for_member)

        for_render = []

        for t in available_trainings_for_member:
            t["quiz_url"] = create_cm_link(
                member_id,
                t["id"],
                available_trainings_for_member,
                token
            )
            for_render.append(t)

        return jsonify(for_render)

    except Exception as e:
        print(traceback.format_exc())

        return Response(f'Error: {e.args}', 400)


# ------------------------ !!!DEVELOPMENT!!! ------------------------
@app.route("/create_cm_link", methods=["POST"])
@swag_from(swagger_config.cm_urls_schema)
def create_quiz_link():
    """
    TEST API for URL function
    """
    try:
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

    except Exception as e:
        print(traceback.format_exc())

        return Response(f'Error: {e.args}', 400)
# ------------------------ !!!DEVELOPMENT!!! ------------------------


# ------------------------ !!!FUTURE!!! ------------------------
@app.route("/activities", methods=["POST"])
def activities_notifications():
    """
    Future functionality, event listener for disabled and re-enabled resources.
    :return: info about resource
    """
    try:
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

    except Exception as e:
        print(traceback.format_exc())

        return Response(f'Error: {e.args}', 400)
# ------------------------ !!!FUTURE!!! ------------------------


if __name__ == "__main__":
    # if not FABMAN_API_KEY:
    #     raise Exception("Missing Fabman API key")
    #
    # if not CLASSMARKER_WEBHOOK_SECRET:
    #     raise Exception("Missing Classmarker secret")
    #
    # if not FERNET_KEY:
    #     raise Exception("Missing Fernet Key secret")

    app.run(debug=True)
