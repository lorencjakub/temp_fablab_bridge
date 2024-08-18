# FABLAB TRAINING EXPIRATION SCHEDULER

Flask scheduler for training expiration. 
Script fetches members data with absolved trainings. If any training is expired, request on bridge service (expiration email notification) is sent. On success response, DELETE request with current training is sent to the Fabman and training is removed from member's trainings.

This service is optional for handling trainings expiration.

# LOCAL RUN
Clone repository, create a new virtual environment and install all dependencies from **requirements.txt** file (recomended python version *3.11.3*). Then just set up environment variables and run **main_run.py** script.

<br>
<br>

# DEPLOYMENT
Use scheduler on every system with support of scheduled tasks. You can find one possible deployment config in **nixpacks.toml** file (prepared for deployment on https://railway.app/).

<br>
<br>

ClassMarker webhooks info:
*	https://www.classmarker.com/online-testing/docs/webhooks/#example-code
*	https://www.classmarker.com/online-testing/docs/webhooks/#link-results


## ENV VARIABLES:

Crypto and auth:
* CRONJOB_TOKEN: verification token for scheduler service
* FABMAN_API_KEY: https://fabman.io/api/v1/documentation

Email config (https://pythonhosted.org/Flask-Mail/)
* FABLAB_SUPPORT_EMAIL: email address of FabLab support
* MAIL_PASSWORD: password/app password for email client
* MAIL_PORT: port of email client
* MAIL_SERVER: smtp server for email client
* MAIL_USERNAME: email (sender) for email client
* MAIL_USE_SSL: (boolean) use SSL connection for emails
* MAIL_USE_TLS: (boolean) use TLS connection for emails

Other:
* RAILWAY_API_URL: URL of bridge service

<br>
<br>