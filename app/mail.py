import smtplib
from email.message import EmailMessage


def send_contact_email(*, name: str, email: str, message: str, config) -> None:
    msg = EmailMessage()
    msg["Subject"] = f"Honeybee Early Learning contact form: {name}"
    msg["From"] = config["SMTP_USERNAME"]
    msg["To"] = config["CONTACT_RECIPIENT"]
    msg["Reply-To"] = email
    msg.set_content(f"Name: {name}\nEmail: {email}\n\n{message}")

    with smtplib.SMTP(config["SMTP_HOST"], config["SMTP_PORT"], timeout=10) as smtp:
        smtp.starttls()
        smtp.login(config["SMTP_USERNAME"], config["SMTP_APP_PASSWORD"])
        smtp.send_message(msg)
