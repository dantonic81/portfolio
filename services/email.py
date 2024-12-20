import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from typing import Tuple, Optional
from utils.logger import logger


# Retrieve the SendGrid API key from environment variables
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
SENDGRID_FROM_EMAIL = os.getenv('SENDGRID_FROM_EMAIL')


def send_email(to_email: str, subject: str, content: str) -> Optional[Tuple[int, str, dict]]:
    """
    Sends an email using SendGrid.

    Args:
        to_email (str): Recipient's email address.
        subject (str): Email subject.
        content (str): Email content (HTML or plain text).

    Returns:
        Optional[Tuple[int, str, dict]]: Tuple containing the response status code, body, and headers, or `None` if an error occurs.
    """
    if not SENDGRID_API_KEY or not SENDGRID_FROM_EMAIL:
        logger.info("Error: Required environment variables are not set.")
        return None

    try:
        message = Mail(
            from_email=SENDGRID_FROM_EMAIL,
            to_emails=to_email,
            subject=subject,
            html_content=content
        )
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        return response.status_code, response.body, response.headers
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return None
