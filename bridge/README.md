# FABLAB BRIDGE

Flask bridge for online courses.

# LOCAL RUN
Clone repository, create a new virtual environment and install all dependencies from **requirements.txt** file (recommended python version *3.11.3*). Then just set up environment variables and run **main_run.py** file. When you run Flask server, you can use project Swagger on http://localhost:{port}/apidocs/ (default port for Flask server is 5000).
Alternatively you can build and run docker container from Dockerfile.dev.

<br>
<br>

# DEPLOYMENT
Use gunicorn or other WSGI HTTP server for deployment. You can find one possible deployment config in **nixpacks.toml** file (prepared for deployment on https://railway.app/).
Alternatively you can build and run docker container from Dockerfile.dev.

<br>
<br>

ClassMarker webhooks info:
*	https://www.classmarker.com/online-testing/docs/webhooks/#example-code
*	https://www.classmarker.com/online-testing/docs/webhooks/#link-results


## ENV VARIABLES:

Crypto and auth:
* CLASSMARKER_WEBHOOK_SECRET: https://www.classmarker.com/online-testing/docs/webhooks/#how-to-verify-webhook-payloads
* COURSES_WEB_PRIVATE_KEY: private key for FabLab web
* CRONJOB_TOKEN: verification token for scheduler service
* FABMAN_API_KEY: https://fabman.io/api/v1/documentation
* FERNET_KEY: token for symmetric cryptography https://cryptography.io/en/latest/fernet/
* SECRET_KEY: token for Flask server
* CRONJOB_TOKEN: token for scheduler service
* FLASK_SECRET_KEY: token for Flask server
* VERIFY_CLASSMARKER_REQUESTS: (boolean) incoming requests on endpoint /add_classmarker_training should be verified by HMAC header

Email config (https://pythonhosted.org/Flask-Mail/)
* FABLAB_SUPPORT_EMAIL: email address of FabLab support
* MAIL_PASSWORD: password/app password for email client
* MAIL_PORT: port of email client
* MAIL_SERVER: smtp server for email client
* MAIL_USERNAME: email (sender) for email client
* MAIL_USE_SSL: (boolean) use SSL connection for emails
* MAIL_USE_TLS: (boolean) use TLS connection for emails

Other:
* BE_ENV: name of environment ("prod" for production)
* MAX_COURSE_ATTEMPTS (global allowed counts of attempts of every course)
* TRACK_TIME: (boolean) track requests processing time and return it in response header

<br>
<br>

## WORKFLOW 1 - GET ABSOLVED COURSES ON USER'S PROFILE PAGE
Get active (not expired) trainings of specific user.  
![Absolved trainings workflow schema](/bridge/diagrams/absolved_trainings.jpg "Absolved trainings workflow schema")
<br>
<br>

* Endpoint: /absolved_training/<member_id>
  * method: GET
  * auth: Authorization header with FABMAN_API_KEY

Response of Bridge API:
```python
[
    {
        "id": 1,
        "title": "Course 1",
        "date": "YYY-MM-DD"
    },
    {
        "id": 2,
        "title": "Course 2",
        "date": "YYY-MM-DD"
    }
]
```

<br>
<br>

## WORKFLOW 2 - GET AVAILABLE COURSES FOR USER'S PROFILE PAGE
Get available (not absolved trainings or expired trainings) courses for specific user.
Some of trainings could be only for admins, some of them could be presence-only without online version.
User is not able to absolve online course if he is already out of attempts for it.  
![Available trainings filter schema](/bridge/diagrams/available_trainings.jpg "Available trainings filter schema")  
![Available trainings render schema](/bridge/diagrams/available_trainings_render.jpg "Available trainings render schema")  
<br>
<br>

* Endpoint: /available_trainings/<member_id>
  * method: GET
  * auth: Authorization header with FABMAN_API_KEY

Response of Bridge API:
```python
[
    {
        "id": 1,
        "title": "Course 1",
        "quiz_url": "url-to-ClassMarker-quiz"
    },
    {
        "id": 2,
        "title": "Course 2",
        "quiz_url": "url-to-ClassMarker-quiz"
    }
]
```
<br>
<br>

## WORKFLOW 3 - ONLINE CLASSMARKER COURSE
Integration of process for online courses. Find available course in your user profile -> open quiz via href button -> pass that quiz -> ClassMarker webhook call to FabLab bridge -> handle online course attempt.  
![Online training workflow schema](/bridge/diagrams/online_training.jpg "Online training workflow schema")  
<br>
<br>
 
### CLASSMARKER WEBHOOK:
*	ClassMarker is opened via specific URL - it contains encrypted member ID and training-course ID from Fabman DB (as **cm_user_id**).
*	ClassMarker webhook calls bridge endpoint with results of quiz

<br>
<br>

* Endpoint: /available_trainings/<member_id>
  * method: POST
  * auth: "X-Classmarker-Hmac-Sha256" header: https://www.classmarker.com/online-testing/docs/webhooks/#how-to-verify-webhook-payloads
  * request payload:
```python
{
    "test": {
        "test_name": string
    },
    "result": {
        "email": string,
        "passed": boolean,
        "cm_user_id": string ("encrypted<membed_id-training_id>")
    }
}
```

<br>
<br>

## WORKFLOW 4 - GET SPECIFIC QUIZ URL
Create URL for ClassMarker quiz for specific member and specific training-course, URL of wiki article and youtube video.

* Endpoint: /get_training_links
  * method: POST
  * auth: Authorization header with FABMAN_API_KEY
  * request payload:
```python
{
  "member_id": 123456,
  "training_id": 1234
}
```
* request response:
```python
{
    "quiz_url": "https://www.classmarker.com/online-test/start/?quiz={quiz_ID}&cm_user_id={encrypted data}",
    "title": "Test Quiz",
    "wiki_url": "https://wiki.fablabbrno.cz/test_url",
    "yt_url": "https://www.youtube.com/test_url"
}
```

<br>
<br>

## WORKFLOW 5 - REMOVE MEMBERS EXPIRED TRAININGS
Endpoint for scheduler service. Periodically removes all expired trainings of users and uses this endpoint for sending email notification.

* Endpoint: /get_training_links
  * method: POST
  * auth: CronjobToken header
  * request payload:
```python
{
  "member_id": 123456,
  "training_id": 1234
}
```
* request response: empty

<br>
<br>

### USER NOTIFICATIONS (email, Discord, ...):
Bridge sends email notification in these cases:
*	any exception during bridge operations (process failed, contact your FabLab CORE team)
*	process didn't failed, but user didn't pass ClassMarker quiz (info about remaining attempts or contact your FabLab CORE team because of attempts reset)
*	process succeed, training has been added

<br>
<br>