import smtplib
import os
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta
from config import Config

logger = logging.getLogger("BBMP_FW_Report.MailSender")
IST = timezone(timedelta(hours=5, minutes=30))

class MailSender:
    def __init__(self):
        self.server = Config.SMTP_SERVER
        self.port = Config.SMTP_PORT
        self.use_tls = Config.SMTP_USE_TLS
        self.username = Config.SMTP_USERNAME
        self.password = Config.SMTP_PASSWORD
        self.sender = Config.SENDER_EMAIL
        self.recipients = Config.RECIPIENT_EMAILS
        self.bcc = Config.BCC_EMAILS

    def send_email(self, html_content_path, subject=None):
        if not self.recipients:
            logger.error("No recipient emails configured.")
            return False

        if not os.path.exists(html_content_path):
            logger.error(f"HTML content file not found: {html_content_path}")
            return False

        with open(html_content_path, "r", encoding="utf-8") as f:
            html_body = f.read()

        now_str = datetime.now(IST).strftime("%d-%b-%Y")
        mail_subject = subject or f"{Config.EMAIL_SUBJECT_PREFIX} - {now_str}"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = mail_subject
        msg["From"] = f"BBMP Panel Monitor <{self.sender}>"
        msg["To"] = ", ".join(self.recipients)
        msg["Message-ID"] = f"<bbmp-fw-report-{int(datetime.now().timestamp())}@schnellenergy.com>"

        # Attach text & HTML versions
        msg.attach(MIMEText("Please view this email in an HTML-compatible email client.", "plain"))
        msg.attach(MIMEText(html_body, "html"))

        all_destinations = list(set(self.recipients + self.bcc))

        logger.info(f"Connecting to SMTP server {self.server}:{self.port}...")
        try:
            with smtplib.SMTP(self.server, self.port, timeout=30) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
                server.sendmail(self.sender, all_destinations, msg.as_string())
                logger.info(f"Email successfully sent to {len(self.recipients)} recipients (+ {len(self.bcc)} BCC)")
                return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
