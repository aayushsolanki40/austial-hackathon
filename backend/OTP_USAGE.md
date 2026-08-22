# OTP Module Usage Guide

The OTP (One-Time Password) module provides OTP generation and verification with built-in development mode support.

## Configuration

Add these environment variables to your `.env` file:

```bash
# Enable development mode (fixed OTP code, no email sending)
DEVELOPMENT_MODE=true

# Fixed OTP code for development (default: "123456")
FIXED_OTP_CODE=123456

# OTP length (number of digits)
OTP_LENGTH=6

# OTP time-to-live in minutes
OTP_TTL_MINUTES=10

# Maximum verification attempts before OTP is locked
OTP_MAX_ATTEMPTS=3
```

## Development Mode Behavior

When `DEVELOPMENT_MODE=true`:

- **OTP codes are fixed** to the value in `FIXED_OTP_CODE` (default: "123456")
- **Email sending is disabled** - OTP codes are only logged to console
- **OTP codes are returned in API responses** for testing convenience

Example console output:
```
[DEV MODE] Using fixed OTP code: 123456
[DEV MODE] OTP for user@example.com (email_verification): 123456
Email sending disabled in development mode. Set DEVELOPMENT_MODE=false to enable.
```

## Production Mode Behavior

When `DEVELOPMENT_MODE=false`:

- **OTP codes are randomly generated** using cryptographically secure random number generation
- **Emails are actually sent** via SMTP (requires email service configuration)
- **OTP codes are NOT returned** in API responses (empty string)

## API Endpoints

### Generate OTP

**POST** `/otp/generate`

Request body:
```json
{
  "recipient": "user@example.com",
  "purpose": "email_verification"
}
```

Response (development mode):
```json
{
  "message": "OTP generated and sent successfully",
  "dev_otp_code": "123456"
}
```

Response (production mode):
```json
{
  "message": "OTP generated and sent successfully",
  "dev_otp_code": null
}
```

### Verify OTP

**POST** `/otp/verify`

Request body:
```json
{
  "recipient": "user@example.com",
  "purpose": "email_verification",
  "code": "123456"
}
```

Response (success):
```json
{
  "verified": true,
  "message": "OTP verified successfully"
}
```

Error responses:
- `401 Unauthorized` - Invalid or expired OTP code
- `401 Unauthorized` - Maximum verification attempts exceeded

## Using OTP Service in Other Modules

To integrate OTP verification into another module (e.g., email verification during registration):

1. Import `OtpModule` in your module:

```python
from src.modules.otp.otp_module import OtpModule

@Module(
    imports=[OtpModule],  # Import OtpModule
    controllers=[MyController],
    providers=[MyService],
)
class MyModule:
    pass
```

2. Inject `OtpService` into your service:

```python
from src.modules.otp.otp_service import OtpService

@Injectable()
class MyService:
    def __init__(self, otp_service: OtpService):
        self.otp_service = otp_service
    
    async def send_verification_email(self, email: str):
        """Send OTP for email verification."""
        # Generate and send OTP (returns code in dev mode)
        otp_code = await self.otp_service.generate_and_send(
            recipient=email,
            purpose="email_verification"
        )
        # In dev mode, otp_code contains "123456"
        # In production, otp_code is empty string (code sent via email)
    
    async def verify_email(self, email: str, code: str):
        """Verify email with OTP."""
        try:
            verified = await self.otp_service.verify(
                recipient=email,
                purpose="email_verification",
                code=code
            )
            # Verification successful
            return True
        except UnauthorizedException:
            # Invalid/expired code or max attempts exceeded
            return False
```

## Common Use Cases

### Email Verification During Registration

```python
# 1. User registers with email
await auth_service.register(email, password)

# 2. Send OTP for email verification
await otp_service.generate_and_send(email, "email_verification")

# 3. User submits OTP code
await otp_service.verify(email, "email_verification", code)

# 4. Mark email as verified
await user_service.mark_email_verified(email)
```

### Two-Factor Authentication (2FA)

```python
# 1. User logs in with email/password
user = await auth_service.login(email, password)

# 2. Send OTP for 2FA
await otp_service.generate_and_send(email, "login_2fa")

# 3. User submits OTP code
await otp_service.verify(email, "login_2fa", code)

# 4. Issue JWT tokens
return await auth_service.issue_tokens(user)
```

### Phone Number Verification

```python
# 1. User adds phone number
await user_service.add_phone(user_id, phone_number)

# 2. Send OTP via SMS (would need SMS provider integration)
await otp_service.generate_and_send(phone_number, "phone_verification")

# 3. User submits OTP code
await otp_service.verify(phone_number, "phone_verification", code)

# 4. Mark phone as verified
await user_service.mark_phone_verified(user_id)
```

## Database Migration

Run the migration to create the `otp_code` table:

```bash
cd backend
alembic upgrade head
```

## Testing

In development mode, always use "123456" as the OTP code:

```bash
# Generate OTP
curl -X POST http://localhost:8000/otp/generate \
  -H "Content-Type: application/json" \
  -d '{"recipient":"test@example.com","purpose":"email_verification"}'

# Verify OTP
curl -X POST http://localhost:8000/otp/verify \
  -H "Content-Type: application/json" \
  -d '{"recipient":"test@example.com","purpose":"email_verification","code":"123456"}'
```

## Future Email Service Integration (Phase 9)

When integrating a real email service (SendGrid, AWS SES, etc.):

1. Add email service configuration to `.env`:
   ```bash
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your-email@gmail.com
   SMTP_PASSWORD=your-app-password
   FROM_EMAIL=noreply@swadely.com
   ```

2. Update `OtpService._send_otp()` to use the email service:
   ```python
   async def _send_otp(self, recipient: str, code: str, purpose: str) -> None:
       if self.dev_mode:
           logger.info(f"[DEV MODE] OTP for {recipient} ({purpose}): {code}")
           return
       
       # Production: send via email service
       await self.email_service.send(
           to=recipient,
           subject="Your verification code",
           body=f"Your OTP code is: {code}. Valid for 10 minutes."
       )
   ```

## Security Notes

- OTP codes are stored as SHA-256 hashes, not plaintext
- Each OTP has a configurable expiration time (default: 10 minutes)
- Maximum verification attempts prevent brute-force attacks (default: 3 attempts)
- Each new OTP invalidates any previous unverified OTP for the same recipient/purpose
- Purpose field prevents OTP reuse across different verification flows
