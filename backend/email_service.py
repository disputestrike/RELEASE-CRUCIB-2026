"""
CrucibAI Email Service
SMTP abstraction layer - ready for your email credentials
"""

import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio
from jinja2 import Template

logger = logging.getLogger(__name__)


class EmailTemplate:
    """Email template definitions"""
    
    WELCOME = """
    <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>Welcome to CrucibAI!</h2>
            <p>Hi {{ first_name }},</p>
            <p>Thank you for signing up. You can now start building amazing applications with CrucibAI.</p>
            <p><a href="{{ login_url }}">Click here to login</a></p>
            <p>Best regards,<br>CrucibAI Team</p>
        </body>
    </html>
    """
    
    PASSWORD_RESET = """
    <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>Password Reset Request</h2>
            <p>Hi {{ first_name }},</p>
            <p>We received a request to reset your password. Click the link below to proceed:</p>
            <p><a href="{{ reset_url }}">Reset Password</a></p>
            <p>This link expires in 24 hours.</p>
            <p>If you didn't request this, please ignore this email.</p>
            <p>Best regards,<br>CrucibAI Team</p>
        </body>
    </html>
    """
    
    EMAIL_VERIFICATION = """
    <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>Verify Your Email</h2>
            <p>Hi {{ first_name }},</p>
            <p>Please verify your email address by clicking the link below:</p>
            <p><a href="{{ verification_url }}">Verify Email</a></p>
            <p>This link expires in 24 hours.</p>
            <p>Best regards,<br>CrucibAI Team</p>
        </body>
    </html>
    """
    
    BUILD_COMPLETE = """
    <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>Your Build is Complete!</h2>
            <p>Hi {{ first_name }},</p>
            <p>Your project "{{ project_name }}" has been successfully built in {{ build_time }}s.</p>
            <p>
                <strong>Build Summary:</strong><br>
                Files Generated: {{ files_generated }}<br>
                Quality Score: {{ quality_score }}/10<br>
                Tokens Used: {{ tokens_used }}
            </p>
            <p><a href="{{ project_url }}">View Project</a></p>
            <p>Best regards,<br>CrucibAI Team</p>
        </body>
    </html>
    """
    
    ERROR_ALERT = """
    <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>Build Error Alert</h2>
            <p>Hi {{ first_name }},</p>
            <p>Your build for project "{{ project_name }}" encountered an error:</p>
            <p><code>{{ error_message }}</code></p>
            <p><a href="{{ project_url }}">View Details</a></p>
            <p>Best regards,<br>CrucibAI Team</p>
        </body>
    </html>
    """


class EmailService:
    """Email service with SMTP support"""
    
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME") or os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("SMTP_FROM_EMAIL", "noreply@crucibai.app")
        self.from_name = os.getenv("SMTP_FROM_NAME", "CrucibAI")
        
        self.configured = all([
            self.smtp_host,
            self.smtp_username,
            self.smtp_password
        ])
        
        if not self.configured:
            logger.warning("⚠️ Email service not configured - SMTP credentials missing")
        else:
            logger.info("✅ Email service configured")
    
    def _render_template(self, template: str, context: Dict[str, Any]) -> str:
        """Render email template with context"""
        jinja_template = Template(template)
        return jinja_template.render(**context)
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        reply_to: Optional[str] = None
    ) -> bool:
        """Send email via SMTP"""
        
        if not self.configured:
            logger.warning(f"⚠️ Email not sent (not configured): {to_email}")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = to_email
            
            if reply_to:
                msg["Reply-To"] = reply_to
            
            # Add text and HTML parts
            if text_body:
                msg.attach(MIMEText(text_body, "plain"))
            msg.attach(MIMEText(html_body, "html"))
            
            # Send email asynchronously
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._send_smtp,
                msg
            )
            
            logger.info(f"✅ Email sent to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send email to {to_email}: {e}")
            return False
    
    def _send_smtp(self, msg):
        """Send via SMTP (blocking operation)"""
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)
    
    async def send_welcome_email(self, user_email: str, first_name: str, login_url: str) -> bool:
        """Send welcome email"""
        html_body = self._render_template(EmailTemplate.WELCOME, {
            "first_name": first_name,
            "login_url": login_url
        })
        
        return await self.send_email(
            to_email=user_email,
            subject="Welcome to CrucibAI!",
            html_body=html_body
        )
    
    async def send_password_reset_email(
        self,
        user_email: str,
        first_name: str,
        reset_url: str
    ) -> bool:
        """Send password reset email"""
        html_body = self._render_template(EmailTemplate.PASSWORD_RESET, {
            "first_name": first_name,
            "reset_url": reset_url
        })
        
        return await self.send_email(
            to_email=user_email,
            subject="Reset Your CrucibAI Password",
            html_body=html_body
        )
    
    async def send_email_verification(
        self,
        user_email: str,
        first_name: str,
        verification_url: str
    ) -> bool:
        """Send email verification"""
        html_body = self._render_template(EmailTemplate.EMAIL_VERIFICATION, {
            "first_name": first_name,
            "verification_url": verification_url
        })
        
        return await self.send_email(
            to_email=user_email,
            subject="Verify Your Email Address",
            html_body=html_body
        )
    
    async def send_build_complete_email(
        self,
        user_email: str,
        first_name: str,
        project_name: str,
        build_time: float,
        files_generated: int,
        quality_score: float,
        tokens_used: int,
        project_url: str
    ) -> bool:
        """Send build complete notification"""
        html_body = self._render_template(EmailTemplate.BUILD_COMPLETE, {
            "first_name": first_name,
            "project_name": project_name,
            "build_time": f"{build_time:.2f}",
            "files_generated": files_generated,
            "quality_score": f"{quality_score:.1f}",
            "tokens_used": tokens_used,
            "project_url": project_url
        })
        
        return await self.send_email(
            to_email=user_email,
            subject=f"Build Complete: {project_name}",
            html_body=html_body
        )
    
    async def send_error_alert_email(
        self,
        user_email: str,
        first_name: str,
        project_name: str,
        error_message: str,
        project_url: str
    ) -> bool:
        """Send error alert email"""
        html_body = self._render_template(EmailTemplate.ERROR_ALERT, {
            "first_name": first_name,
            "project_name": project_name,
            "error_message": error_message,
            "project_url": project_url
        })
        
        return await self.send_email(
            to_email=user_email,
            subject=f"Build Error: {project_name}",
            html_body=html_body
        )


# Global instance
email_service = EmailService()


def get_email_service() -> EmailService:
    """Get email service instance"""
    return email_service
