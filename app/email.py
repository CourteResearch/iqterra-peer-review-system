import os
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import quote


def send_student_invitation(email: str, display_name: str, token: str) -> None:
    sender = os.getenv("IQT02_SMTP_USERNAME", "").strip()
    password = os.getenv("APP")
    public_url = os.getenv("IQT02_PUBLIC_URL", "").replace("[object Object]", "").rstrip("/")
    if not sender:
        raise RuntimeError("IQT02_SMTP_USERNAME must contain the Gmail sender address.")
    if not password:
        raise RuntimeError("The APP email password environment variable is not configured.")
    if not public_url:
        raise RuntimeError("IQT02_PUBLIC_URL must be set to the deployed app URL.")

    message = EmailMessage()
    message["Subject"] = "Set up your IQTerra student account"
    message["From"] = sender
    message["To"] = email
    message.set_content(
        f"Hello {display_name},\n\n"
        "You have been enrolled in IQTerra. Set your password using this "
        "one-time link (valid for 24 hours):\n\n"
        f"{public_url}/?invite={quote(token)}\n\n"
        "After setting your password, sign in with this email address.\n"
    )

    context = ssl.create_default_context()
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as smtp:
        smtp.ehlo()
        smtp.starttls(context=context)
        smtp.ehlo()
        smtp.login(sender, password)
        smtp.send_message(message)
