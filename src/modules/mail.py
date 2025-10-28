import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import datetime
from datetime import timedelta

class EmailSender:
    def __init__(self, smtp_server, smtp_port, smtp_username, smtp_password, sender_email, recipients_email):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.sender_email = sender_email
        
        if isinstance(recipients_email, list):
            self.recipients_email = recipients_email
        else:
            self.recipients_email = [recipients_email]

    def _get_time(self):
        time_format = '%Y-%m-%d %H:%M'  # 在这里加上 :%S

        self.past_time_str = (datetime.datetime.now() - timedelta(hours=1)).strftime(time_format)
        self.current_time_str = datetime.datetime.now().strftime(time_format)

    def _get_email_context(self, body):
        self._get_time()

        subject = f"RevBot 运行状态报告: {self.past_time_str} - {self.current_time_str}"

        self.msg = MIMEMultipart()
        self.msg['From'] = self.sender_email
        self.msg['To'] = ', '.join(self.recipients_email)
        self.msg['Subject'] = subject

        self.msg.attach(MIMEText(body, 'plain', 'utf-8'))

    def send_email(self, body):
        self._get_email_context(body)

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # 587 TLS Port
                server.login(self.smtp_username, self.smtp_password)  # login smtp server
            
                server.sendmail(self.sender_email, self.recipients_email, self.msg.as_string())
                
        except smtplib.SMTPAuthenticationError as auth_error:
            raise Exception("邮件发送失败：SMTP认证错误。请检查您的用户名和密码。") from auth_error
        except Exception as e:
            raise Exception(f"邮件发送失败，发生未知错误：{e}") from e
