import smtplib
import os
import json
import uuid
import logging
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timezone, timedelta
from config import Config

logger = logging.getLogger("BBMP_FW_Report.MailSender")
IST = timezone(timedelta(hours=5, minutes=30))
STATE_FILE_PATH = Path(__file__).resolve().parent / ".email_thread_state.json"

def _format_msg_id(msg_id: str) -> str:
    cleaned = msg_id.strip("<>").strip()
    return f"<{cleaned}>"

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
        self.enable_threading = Config.ENABLE_EMAIL_THREADING
        self.thread_id = Config.EMAIL_THREAD_ID

    def _get_thread_headers(self, thread_id: str):
        formatted_thread_id = _format_msg_id(thread_id)
        if STATE_FILE_PATH.exists():
            try:
                with open(STATE_FILE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    t_data = data.get(thread_id, {})
                    if not t_data and "root_msg_id" in data:
                        t_data = data
                    root_id = t_data.get("root_msg_id") or formatted_thread_id
                    last_id = t_data.get("last_msg_id") or formatted_thread_id
                    return _format_msg_id(root_id), _format_msg_id(last_id)
            except Exception as e:
                logger.warning(f"Could not read thread state: {e}")
        return formatted_thread_id, formatted_thread_id

    def _save_thread_state(self, thread_id: str, root_msg_id: str, sent_msg_id: str):
        try:
            data = {}
            if STATE_FILE_PATH.exists():
                try:
                    with open(STATE_FILE_PATH, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    data = {}
            data[thread_id] = {
                "root_msg_id": root_msg_id,
                "last_msg_id": sent_msg_id,
                "updated_at": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
            }
            with open(STATE_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Updated thread state with last_msg_id={sent_msg_id}")
        except Exception as e:
            logger.warning(f"Could not save thread state: {e}")

    def send_email(self, html_content_path, attachment_path=None, subject=None):
        if not self.recipients:
            logger.error("No recipient emails configured.")
            return False

        if not os.path.exists(html_content_path):
            logger.error(f"HTML content file not found: {html_content_path}")
            return False

        with open(html_content_path, "r", encoding="utf-8") as f:
            html_body = f.read()

        # Subject Line: Keep constant subject prefix for 100% email client thread matching
        mail_subject = subject or Config.EMAIL_SUBJECT_PREFIX

        domain = "schnellenergy.com"
        if self.sender and "@" in self.sender:
            domain = self.sender.split("@")[-1].strip()
        current_msg_id = f"<{int(datetime.now().timestamp())}.{uuid.uuid4().hex[:8]}@{domain}>"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = mail_subject
        msg["From"] = f"BBMP Panel Monitor <{self.sender}>"
        msg["To"] = ", ".join(self.recipients)
        msg["Message-ID"] = current_msg_id

        # In-Reply-To & References for RFC 5322 Email Threading
        root_msg_id = None
        if self.enable_threading:
            root_msg_id, parent_msg_id = self._get_thread_headers(self.thread_id)
            msg["In-Reply-To"] = parent_msg_id
            if root_msg_id != parent_msg_id:
                msg["References"] = f"{root_msg_id} {parent_msg_id}"
            else:
                msg["References"] = root_msg_id
            msg["Thread-Topic"] = mail_subject.replace("[", "").replace("]", "").strip()
            logger.info(f"Email Threading Active | In-Reply-To: {parent_msg_id} | References: {msg['References']}")

        # Attach text & HTML versions
        msg.attach(MIMEText("Please view this email in an HTML-compatible email client.", "plain"))
        msg.attach(MIMEText(html_body, "html"))

        if attachment_path and os.path.exists(attachment_path):
            try:
                with open(attachment_path, "rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())
                encoders.encode_base64(part)
                filename = os.path.basename(attachment_path)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename= {filename}",
                )
                msg.attach(part)
                logger.info(f"Attached file: {filename}")
            except Exception as e:
                logger.error(f"Failed to attach {attachment_path}: {e}")

        all_destinations = list(set(self.recipients + self.bcc))

        logger.info(f"Connecting to SMTP server {self.server}:{self.port}...")
        try:
            with smtplib.SMTP(self.server, self.port, timeout=30) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
                server.sendmail(self.sender, all_destinations, msg.as_string())
                logger.info(f"Email successfully sent to {len(self.recipients)} recipients (+ {len(self.bcc)} BCC)")
                
                # Persist thread state
                if self.enable_threading and root_msg_id:
                    self._save_thread_state(self.thread_id, root_msg_id, current_msg_id)
                    
                return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
