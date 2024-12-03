import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
print(SENDGRID_API_KEY)
def send_email(to_email, subject, content):
    """
    Sends an email using SendGrid.
    :param to_email: Recipient's email address
    :param subject: Email subject
    :param content: Email content (HTML or plain text)
    """
    try:
        message = Mail(
            from_email=os.getenv('SENDGRID_FROM_EMAIL'),
            to_emails=to_email,
            subject=subject,
            html_content=content
        )
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        return response.status_code, response.body, response.headers
    except Exception as e:
        print(f"Error sending email: {e}")
        return None
