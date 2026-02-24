import os

import requests
from starlette.templating import Jinja2Templates

templates = Jinja2Templates(directory="notifications/templates")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")


def send_email_sendgrid(to_email: str, subject: str, body: str):
    url = "https://api.sendgrid.com/v3/mail/send"
    headers = {
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "personalizations": [{"to": [{"email": to_email}], "subject": subject}],
        "from": {"email": "smolinskijmaksim1@gmail.com"},
        "content": [{"type": "text/html", "value": body}],
    }
    response = requests.post(url, headers=headers, json=data)
    print(response.status_code, response.text)
    return response.status_code


def send_activation_email(user_email: str, token: str):
    subject = "Account Activation"
    template = templates.get_template("activation_account.html")

    body = template.render({"email": user_email, "token": token})

    send_email_sendgrid(user_email, subject, body)


def send_reset_password_email(user_email: str, token: str):
    subject = "Reset Password"
    template = templates.get_template("reset_password.html")

    body = template.render({"email": user_email, "token": token})

    send_email_sendgrid(user_email, subject, body)
