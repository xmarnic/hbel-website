import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ["SECRET_KEY"]
    SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USERNAME = os.environ["SMTP_USERNAME"]
    SMTP_APP_PASSWORD = os.environ["SMTP_APP_PASSWORD"]
    CONTACT_RECIPIENT = os.environ.get("CONTACT_RECIPIENT") or SMTP_USERNAME
