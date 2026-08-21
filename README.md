# OTP Authentication Service

An email-based OTP authentication service built with **FastAPI, Redis, NATS, and the Gmail API**.

The service generates a secure OTP, stores it temporarily in Redis, and uses NATS to process email delivery asynchronously through the Gmail API.

## Architecture

![Architecture Diagram](./architecture.png)

### OTP Flow

```text
Frontend
   │
   │ Email
   ▼
Backend API
   │
   ├──► Redis
   │     └── Store OTP + Expiration
   │
   └──► NATS
          │
          ▼
      NATS Worker
          │
          ▼
      Gmail API
          │
          ▼
     User's Email
```

For verification:

```text
User submits OTP
       │
       ▼
Backend API
       │
       ▼
     Redis
       │
       ▼
 Verify OTP
       │
   ┌───┴────┐
   │        │
Correct   Incorrect
   │        │
   ▼        ▼
Success   Attempt++
            │
            ▼
       Maximum 5 attempts
```

## Why Redis?

Redis is used for temporary OTP storage. OTPs are short-lived authentication data, so Redis's fast access and built-in key expiration (TTL) make it a good fit.

The default OTP expiration time is **5 minutes**.

## Why NATS?

NATS separates the API from the email-delivery process.

The backend publishes an OTP email job to NATS, and a worker consumes the job and sends the email through the Gmail API. This keeps email delivery separate from the API and allows additional workers to be added later if needed.

If NATS is unavailable, the application can fall back to direct Gmail API delivery.

## Why the Gmail API (not SMTP)?

The service originally used SMTP (`smtplib`) with Gmail's SMTP server. This was switched to the **Gmail API over HTTPS** for one main reason: **Render's free-tier web services block outbound traffic on SMTP ports 25, 465, and 587**, which made direct SMTP delivery impossible on Render's free instance type.

The Gmail API sends mail over standard HTTPS (port 443), so it isn't affected by this restriction and works on Render's free tier without upgrading to a paid instance.

Authentication uses OAuth2 (Client ID, Client Secret, and a long-lived refresh token) rather than a Gmail App Password. The refresh token is generated **once**, locally, via a one-time OAuth consent flow — not as part of the running application.

Services such as SendGrid, Mailgun, Resend, or Amazon SES are common production alternatives, but most either require a verified custom domain or restrict free-tier sending to a single verified address, which didn't fit this project's requirements. The Gmail API was chosen as a free, domain-free option that could send to arbitrary recipients.

---

## Tech Stack

* **Backend:** FastAPI
* **Server:** Uvicorn
* **Cache / OTP Storage:** Redis
* **Message Broker:** NATS
* **Email:** Gmail API (OAuth2)
* **Language:** Python

---

## Local Setup

### 1. Clone the repository

```bash
git clone git@github.com:jayssSmm/micro_service.git
cd micro_service
```

### 2. Create a virtual environment

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows:**

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up Gmail API credentials (one-time)

The Gmail API requires an OAuth2 Client ID/Secret and a refresh token, generated once via Google Cloud Console:

1. Create a project in [Google Cloud Console](https://console.cloud.google.com), enable the **Gmail API**.
2. Configure the **OAuth consent screen** (External, add your sending Gmail account as a **Test user**).
3. Create an **OAuth Client ID** of type **Desktop app**, download the credentials JSON.
4. Run the included one-time script to complete the OAuth flow and obtain a refresh token:

   ```bash
   pip install google-auth-oauthlib google-api-python-client
   python get_gmail_token.py
   ```

   This opens a browser, asks you to log into the sending Gmail account, and prints/saves `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, and `GMAIL_REFRESH_TOKEN`.

> **Note:** While the OAuth consent screen is in "Testing" mode, refresh tokens expire after 7 days. Publish the app (Google Auth Platform → Audience → Publish) to remove this expiry — full Google verification is generally not required for the `gmail.send` scope alone.

### 5. Configure environment variables

Create a `.env` file in the project root:

```env
GMAIL_CLIENT_ID=<from step 4>
GMAIL_CLIENT_SECRET=<from step 4>
GMAIL_REFRESH_TOKEN=<from step 4>
GMAIL_SENDER_EMAIL=<the gmail account used to authorize>

REDIS_URL=<redis_url>

NATS_URL=<nats_url>
NATS_CREDS_PATH=<path_to_nats.creds_file>
```

For local services, for example:

```env
REDIS_URL=redis://127.0.0.1:6379
NATS_URL=nats://localhost:4222
```

`credentials.json` and `nats.creds` should never be committed — both are already covered by `.gitignore`.

---

## Running the Application

Make sure Redis and NATS are running.

Start the API with:

```bash
uvicorn wsgi:app --port 8000
```

The server runs on:

```text
http://localhost:8000
```

Alternatively:

```bash
uvicorn wsgi:app --host 0.0.0.0 --port 8000 --reload
```

---

## API Documentation

Once the server is running, FastAPI provides interactive API documentation:

* **Swagger UI:** `http://localhost:8000/docs`
* **ReDoc:** `http://localhost:8000/redoc`

### Send OTP

**`POST /auth/send-otp`**

Request:

```json
{
  "email": "user@example.com"
}
```

The API generates an OTP, stores it in Redis, and publishes an email job to NATS.

---

### Verify OTP

**`POST /auth/verify-otp`**

Request:

```json
{
  "email": "user@example.com",
  "otp": "123456"
}
```

The submitted OTP is checked against the value stored in Redis.

A maximum of **5 incorrect attempts** is allowed by default. After successful verification, the OTP is removed from Redis.

---

## Configuration

The following values can be configured through environment variables:

| Variable                     |          Default | Description                          |
| ----------------------------- | ---------------: | ------------------------------------ |
| `OTP_TTL_SECONDS`             |            `300` | OTP expiration time                  |
| `MAX_OTP_ATTEMPTS`            |              `5` | Maximum incorrect attempts           |
| `NATS_OTP_REQUEST_TIMEOUT`    |             `20` | NATS request timeout                 |
| `SMTP_RETRY_BACKOFF_SECONDS`  |              `2` | Email retry delay                    |
| `GMAIL_CLIENT_ID`             |                 — | Gmail API OAuth2 client ID           |
| `GMAIL_CLIENT_SECRET`         |                 — | Gmail API OAuth2 client secret       |
| `GMAIL_REFRESH_TOKEN`         |                 — | Gmail API OAuth2 refresh token       |
| `GMAIL_SENDER_EMAIL`          |                 — | Gmail address used as the sender     |
| `CORS_ORIGINS`                |              `*` | Allowed frontend origins             |

---

## Project Structure

```text
.
├── README.md
├── app
│   ├── __init__.py
│   ├── auth
│   │   └── auth.py
│   ├── config.py
│   ├── email
│   │   └── email_utils.py
│   ├── extension.py
│   ├── models
│   │   └── otp_models.py
│   ├── otp
│   │   └── otp_store.py
│   ├── routes
│   │   ├── send_otp.py
│   │   └── verify_otp.py
│   └── worker.py
├── get_gmail_token.py
├── requirements.txt
├── templates
│   ├── index.html
│   └── static
│       ├── scripts.js
│       └── styles.css
└── wsgi.py
```

## Security

* OTPs automatically expire through Redis TTL.
* OTP verification is limited to a maximum number of attempts.
* OTPs are deleted after successful verification.
* Gmail API credentials (Client ID/Secret/Refresh Token) and NATS credentials are stored in environment variables / secret files, never in source.
* `.env`, `credentials.json`, `gmail_token_output.json`, and `nats.creds` are all excluded via `.gitignore`.

## Deployment Notes

* Hosted on **Render's free tier**, which blocks outbound SMTP ports (25/465/587). Email delivery uses the Gmail API over HTTPS instead, which is unaffected by this restriction.
* NATS is hosted via **Synadia Cloud** and connected over the standard NATS client port (4222), which is not restricted on Render's free tier.

## Assignment Deliverables

* Source code
* README with setup instructions
* Architecture diagram
* API documentation
* Local development instructions