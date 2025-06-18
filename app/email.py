import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models import Pengguna, ResetPassword
from app.security import create_access_token
from dotenv import load_dotenv

load_dotenv()

# SMTP Configuration
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
FROM_EMAIL = os.getenv("FROM_EMAIL")

async def send_password_reset_email(email: str, db: Session):
    # Find user by email
    user = db.query(Pengguna).filter(Pengguna.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email tidak ditemukan"
        )

    # Create reset token
    expires_delta = timedelta(hours=1)  # Token valid for 1 hour
    reset_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=expires_delta
    )

    # Store reset token in database
    reset_entry = ResetPassword(
        id_pengguna=user.id,
        token=reset_token,
        kadaluarsa_pada=datetime.utcnow() + expires_delta
    )
    db.add(reset_entry)
    db.commit()

    # Create email message
    msg = MIMEMultipart()
    msg['From'] = FROM_EMAIL
    msg['To'] = email
    msg['Subject'] = "Permintaan Reset Password"

    # Create reset link
    reset_link = f"http://localhost:8000/auth/reset-password?token={reset_token}"

    # Email body
    body = f"""
    Halo,

    Anda telah meminta untuk mereset kata sandi Anda. Silakan klik link berikut untuk mengatur ulang kata sandi Anda:
    {reset_link}

    Link ini akan kadaluarsa dalam 1 jam. Jika Anda tidak meminta reset kata sandi, abaikan email ini.

    Terima kasih,
    Tim Aplikasi
    """
    msg.attach(MIMEText(body, 'plain'))

    try:
        # Connect to SMTP server
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        # Delete the reset token if email sending fails
        db.delete(reset_entry)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal mengirim email: {str(e)}"
        )