"""Send HTML emails via QQ SMTP."""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

SMTP_HOST = "smtp.qq.com"
SMTP_PORT = 465  # SSL


def send_email(
    html_content: str,
    subject: str,
    smtp_user: str,
    smtp_pass: str,
    to_addr: str = "",
) -> bool:
    """Send HTML email via QQ SMTP.

    Args:
        html_content: Full HTML email body
        subject: Email subject line
        smtp_user: QQ email address (also used as from_addr)
        smtp_pass: QQ SMTP authorization code (NOT QQ password)
        to_addr: Recipient address (defaults to smtp_user = send to self)

    Returns:
        True if sent successfully, False otherwise
    """
    if not smtp_user or not smtp_pass:
        print("[sender] Missing SMTP credentials, skipping send")
        return False

    to_addr = to_addr or smtp_user

    msg = MIMEMultipart("alternative")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = smtp_user
    msg["To"] = to_addr
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, [to_addr], msg.as_string())
        print(f"[sender] Email sent: {subject}")
        return True
    except smtplib.SMTPException as e:
        print(f"[sender] SMTP error: {e}")
        return False
    except OSError as e:
        print(f"[sender] Connection error: {e}")
        return False
