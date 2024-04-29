from flasgger import Swagger, swag_from
from flask_mail import Mail, Message


SWAGGER_TEMPLATE = {
    "securityDefinitions": {
        "apiKey": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header"
        },
        "cm_hmac": {
            "type": "apiKey",
            "name": "X-Classmarker-Hmac-Sha256",
            "in": "header"
        },
        "cronjob_token": {
            "type": "apiKey",
            "name": "CronjobToken",
            "in": "header"
        }
    },
    "security": [
        {
            "apiKey": []
        },
        {
            "cm_hmac": []
        },
        {
            "cronjob_token": []
        }
    ],
    "info": {
        "title": "FabLab Bridge Swagger",
        "description": "OpenSource API with logic for online Fabman courses",
        "version": "1.0.0",
        "contact": {
            "name": "FabLab Brno",
            "url": "https://www.fablabbrno.cz/kontakt/"
        }
    }
}


mail = Mail()
swagger = Swagger(template=SWAGGER_TEMPLATE)
