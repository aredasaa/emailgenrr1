from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
import random
import string
from threading import Timer
import re

app = FastAPI()

# Root endpoint untuk mengembalikan HTML
@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("templates/index.html", "r", encoding="utf-8") as file:
        content = file.read()
    return content

# Model untuk input data email
class EmailRequest(BaseModel):
    email: EmailStr  # Menggunakan EmailStr dari Pydantic untuk validasi otomatis

# Fungsi untuk membuat email sementara
def generate_email():
    domain = "tempemail.com"
    random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"{random_part}@{domain}"

# Simpan email sementara
active_emails = {}
# Simpan timer untuk setiap email agar tidak terjadi duplikasi
email_timers = {}

# Fungsi untuk menginisialisasi inbox (dummy inbox)
def generate_inbox(email):
    # Inbox dummy, bisa dikembangkan lebih lanjut
    return [
        {"from": "service@instagram.com", "subject": "Confirm your email", "body": "Your code: 123456"},
        {"from": "service@facebook.com", "subject": "Verify your account", "body": "Your code: 654321"},
    ]

# Fungsi untuk menghapus email setelah 1 jam
def delete_email_after_timeout(email):
    if email in active_emails:
        del active_emails[email]
        email_timers.pop(email, None)  # Hapus timer juga
        print(f"Email {email} telah dihapus setelah 1 jam.")

# Endpoint untuk membuat email baru
@app.post("/api/new-email")
async def create_email():
    # Generate email sementara
    email = generate_email()

    # Cek apakah email sudah ada di active_emails
    if email in active_emails:
        raise HTTPException(status_code=400, detail="Email sudah ada, coba lagi.")
    
    # Simpan email sementara beserta inboxnya
    active_emails[email] = {"inbox": generate_inbox(email)}

    # Set timer untuk menghapus email setelah 1 jam (3600 detik)
    if email not in email_timers:
        timer = Timer(3600, delete_email_after_timeout, [email])
        email_timers[email] = timer
        timer.start()
    
    return {"email": email}

# Fungsi untuk mengekstrak kode verifikasi dari email
def extract_verification_code(email_body: str):
    # Menggunakan ekspresi regular untuk mengekstrak kode verifikasi (misalnya kode 6 digit)
    match = re.search(r'Your code: (\d{6})', email_body)
    if match:
        return match.group(1)
    return None

# Endpoint untuk cek inbox dan mengambil kode verifikasi
@app.post("/api/inbox")
async def check_inbox(payload: EmailRequest):
    email = payload.email

    # Cek apakah email ditemukan
    if email in active_emails:
        inbox = active_emails[email]["inbox"]
        
        # Cek setiap pesan di inbox untuk menemukan kode verifikasi
        for message in inbox:
            if "service@instagram.com" in message["from"]:
                verification_code = extract_verification_code(message["body"])
                if verification_code:
                    return {"verification_code": verification_code}
        
        # Jika tidak ditemukan kode verifikasi
        raise HTTPException(status_code=404, detail="Kode verifikasi tidak ditemukan!")
    else:
        raise HTTPException(status_code=404, detail="Email tidak ditemukan!")

# Endpoint untuk menghapus email
@app.delete("/api/delete-email")
async def delete_email(payload: EmailRequest):
    email = payload.email

    # Cek apakah email ada
    if email in active_emails:
        del active_emails[email]
        if email in email_timers:
            email_timers[email].cancel()  # Cancel timer jika ada
            email_timers.pop(email)
        return {"message": f"Email {email} telah dihapus."}
    else:
        raise HTTPException(status_code=404, detail="Email tidak ditemukan!")

# Fungsi untuk memvalidasi email (untuk memastikan email valid)
def is_valid_email(email: str) -> bool:
    try:
        # Cek apakah email valid menggunakan EmailStr dari Pydantic
        EmailStr.validate(email)  # Pydantic menggunakan metode ini untuk validasi
        return True
    except ValidationError:
        return False
