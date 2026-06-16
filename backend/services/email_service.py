import smtplib
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid, parseaddr
import html


class EmailService:
    def __init__(self, config):
        self.config = config

    def is_configured(self):
        smtp_host = self.config.get("SMTP_HOST")
        smtp_port = self.config.get("SMTP_PORT")
        smtp_username = self.config.get("SMTP_USERNAME")
        smtp_password = self.config.get("SMTP_PASSWORD")
        email_from = self.config.get("EMAIL_FROM")

        return bool(smtp_host and smtp_port and smtp_username and smtp_password and email_from)

    def _get_smtp_settings(self):
        smtp_host = self.config.get("SMTP_HOST")
        smtp_port = self.config.get("SMTP_PORT")
        smtp_username = self.config.get("SMTP_USERNAME")
        smtp_password = self.config.get("SMTP_PASSWORD")
        email_from = self.config.get("EMAIL_FROM")
        use_tls = self.config.get("SMTP_USE_TLS", True)
        use_ssl = self.config.get("SMTP_USE_SSL", False)

        if not self.is_configured():
            raise ValueError("Email delivery is not configured. Please set SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, and EMAIL_FROM.")

        return {
            "smtp_host": smtp_host,
            "smtp_port": smtp_port,
            "smtp_username": smtp_username,
            "smtp_password": smtp_password,
            "email_from": email_from,
            "use_tls": use_tls,
            "use_ssl": use_ssl,
        }

    def _send_message(self, message):
        smtp_settings = self._get_smtp_settings()
        smtp_client = smtplib.SMTP_SSL if smtp_settings["use_ssl"] else smtplib.SMTP

        with smtp_client(smtp_settings["smtp_host"], int(smtp_settings["smtp_port"]), timeout=20) as server:
            server.ehlo()
            if smtp_settings["use_tls"] and not smtp_settings["use_ssl"]:
                server.starttls()
                server.ehlo()
            server.login(smtp_settings["smtp_username"], smtp_settings["smtp_password"])
            refused = server.send_message(message)

        if refused:
            refused_recipients = ", ".join(refused.keys())
            raise ValueError(f"Email server refused the recipient: {refused_recipients}")

    def _sender_header(self, email_from):
        sender_name, sender_email = parseaddr(str(email_from or ""))
        if sender_name or not sender_email:
            return email_from
        return formataddr((self._brand_name(), sender_email))

    def _message_id_domain(self, email_from):
        _, sender_email = parseaddr(str(email_from or ""))
        if "@" not in sender_email:
            return None
        return sender_email.rsplit("@", 1)[-1]

    def _support_email(self):
        support_email = self.config.get("SUPPORT_EMAIL")
        email_from = self.config.get("EMAIL_FROM")
        _, parsed_support = parseaddr(str(support_email or ""))
        _, parsed_from = parseaddr(str(email_from or ""))
        return parsed_support or parsed_from or "support@noobtrade.com"

    def _prepare_transactional_message(self, message, subject, recipient_email):
        smtp_settings = self._get_smtp_settings()
        message["Subject"] = subject
        message["From"] = self._sender_header(smtp_settings["email_from"])
        message["To"] = recipient_email
        message["Reply-To"] = self._support_email()
        message["Date"] = formatdate(localtime=False, usegmt=True)
        message["Message-ID"] = make_msgid(domain=self._message_id_domain(smtp_settings["email_from"]))
        message["Auto-Submitted"] = "auto-generated"
        message["X-Auto-Response-Suppress"] = "All"

    def send_login_code(self, recipient_email, code):
        expiry_minutes = self.config.get("LOGIN_CODE_EXPIRY_MINUTES", 10)
        self._send_security_code_email(
            recipient_email=recipient_email,
            subject="Noob Trade admin login verification code",
            eyebrow="Admin Verification",
            title="Your admin login code",
            intro="Use this code to finish signing in to the protected Noob Trade administrator workspace.",
            code=code,
            expiry_minutes=expiry_minutes,
            action_label="Open Noob Trade",
            action_href=self.config.get("APP_BASE_URL"),
        )

    def send_email_verification_code(self, recipient_email, code):
        expiry_minutes = self.config.get("EMAIL_VERIFICATION_CODE_EXPIRY_MINUTES", 15)
        self._send_security_code_email(
            recipient_email=recipient_email,
            subject="Verify your Noob Trade email",
            eyebrow="Email Verification",
            title="Confirm your email address",
            intro="Welcome to Noob Trade. Enter the code below to verify your email and activate your account.",
            code=code,
            expiry_minutes=expiry_minutes,
            action_label="Verify Your Email",
            action_href=self.config.get("APP_BASE_URL"),
        )

    def send_password_reset_code(self, recipient_email, code):
        expiry_minutes = self.config.get("PASSWORD_RESET_CODE_EXPIRY_MINUTES", 15)
        self._send_security_code_email(
            recipient_email=recipient_email,
            subject="Reset your Noob Trade password",
            eyebrow="Password Reset",
            title="Reset your password",
            intro="We received a request to reset your Noob Trade password. Enter this code to continue.",
            code=code,
            expiry_minutes=expiry_minutes,
            action_label="Reset Password",
            action_href=self.config.get("APP_BASE_URL"),
        )

    def send_login_notice(self, recipient_email, login_context=None):
        message = EmailMessage()
        self._prepare_transactional_message(
            message=message,
            subject="Noob Trade login notice",
            recipient_email=recipient_email,
        )
        message.set_content(self._build_login_notice_plain_text(login_context))
        message.add_alternative(self._build_login_notice_html(login_context), subtype="html")

        self._send_message(message)

    def _send_security_code_email(self, recipient_email, subject, eyebrow, title, intro, code, expiry_minutes, action_label, action_href):
        message = EmailMessage()
        self._prepare_transactional_message(
            message=message,
            subject=subject,
            recipient_email=recipient_email,
        )
        message.set_content(self._build_code_plain_text(title, intro, code, expiry_minutes, action_href))
        message.add_alternative(
            self._build_code_email_html(
                eyebrow=eyebrow,
                title=title,
                intro=intro,
                code=code,
                expiry_minutes=expiry_minutes,
                action_label=action_label,
                action_href=action_href,
            ),
            subtype="html",
        )

        self._send_message(message)

    def _brand_name(self):
        return self.config.get("APP_NAME", "Noob Trade")

    def _brand_links(self):
        return {
            "email": self.config.get("SUPPORT_EMAIL", "support@noobtrade.com"),
            "phone": self.config.get("SUPPORT_PHONE", "+1 (800) 555-0149"),
            "x": self.config.get("X_URL", "https://x.com/noobtrade"),
            "instagram": self.config.get("INSTAGRAM_URL", "https://instagram.com/noobtrade"),
            "discord": self.config.get("DISCORD_URL", "https://discord.gg/noobtrade"),
        }

    def _build_code_plain_text(self, title, intro, code, expiry_minutes, action_href):
        brand_name = self._brand_name()
        links = self._brand_links()

        return "\n".join(
            [line for line in [
                brand_name,
                "",
                title,
                intro,
                "",
                f"Code: {code}",
                f"Expires in: {expiry_minutes} minutes",
                "",
                f"Open app: {action_href}" if action_href else "",
                f"Support email: {links['email']}",
                f"Support phone: {links['phone']}",
                f"X: {links['x']}",
                f"Instagram: {links['instagram']}",
                f"Discord: {links['discord']}",
            ] if line]
        )

    def _build_code_email_html(self, eyebrow, title, intro, code, expiry_minutes, action_label, action_href):
        brand_name = html.escape(self._brand_name())
        safe_eyebrow = html.escape(str(eyebrow or "Security Code"))
        safe_title = html.escape(str(title or "Your verification code"))
        safe_intro = html.escape(str(intro or "Enter this code to continue."))
        safe_code = html.escape(str(code))
        safe_action_label = html.escape(str(action_label or "Open Noob Trade"))
        safe_action_href = html.escape(str(action_href or ""), quote=True)
        safe_expiry_minutes = html.escape(str(expiry_minutes))
        links = {
            key: html.escape(str(value or ""), quote=True)
            for key, value in self._brand_links().items()
        }
        action_html = ""

        if safe_action_href:
            action_html = f"""
                    <tr>
                      <td style="padding:0 34px 26px;">
                        <a href="{safe_action_href}" style="display:inline-block;background:#ea580c;color:#ffffff;text-decoration:none;font-size:14px;font-weight:800;letter-spacing:0.02em;padding:14px 22px;border-radius:999px;">{safe_action_label}</a>
                      </td>
                    </tr>
            """

        return f"""
        <!doctype html>
        <html lang="en">
          <head>
            <meta charset="UTF-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            <title>{brand_name}</title>
          </head>
          <body style="margin:0;padding:0;background:#fff8f2;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#1f2937;">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#fff8f2;padding:28px 12px;">
              <tr>
                <td align="center">
                  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:620px;background:#ffffff;border-radius:28px;overflow:hidden;border:1px solid rgba(251,146,60,0.18);box-shadow:0 24px 64px rgba(194,65,12,0.12);">
                    <tr>
                      <td style="padding:0;">
                        <div style="background:linear-gradient(135deg,#fff7ed 0%,#ffedd5 42%,#fdba74 100%);padding:34px 34px 28px;">
                          <div style="font-size:36px;font-weight:900;letter-spacing:-0.05em;color:#ea580c;line-height:1;">{brand_name}</div>
                          <div style="margin-top:10px;font-size:12px;font-weight:800;letter-spacing:0.16em;text-transform:uppercase;color:#9a3412;">{safe_eyebrow}</div>
                          <div style="margin-top:18px;display:grid;grid-template-columns:1.4fr 1fr;gap:18px;align-items:end;">
                            <div>
                              <div style="font-size:30px;font-weight:850;line-height:1.15;color:#111827;">{safe_title}</div>
                              <p style="margin:14px 0 0;font-size:15px;line-height:1.8;color:#7c2d12;">{safe_intro}</p>
                            </div>
                            <div style="background:rgba(255,255,255,0.68);border:1px solid rgba(249,115,22,0.22);border-radius:22px;padding:18px 18px 16px;text-align:left;">
                              <div style="font-size:11px;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;color:#9a3412;">Security code</div>
                              <div style="margin-top:10px;font-size:34px;font-weight:900;letter-spacing:0.22em;color:#ea580c;">{safe_code}</div>
                              <div style="margin-top:12px;font-size:13px;line-height:1.6;color:#7c2d12;">Valid for <strong>{safe_expiry_minutes} minutes</strong></div>
                            </div>
                          </div>
                        </div>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:28px 34px 18px;">
                        <div style="padding:18px 20px;border-radius:20px;background:#fffaf5;border:1px solid rgba(251,146,60,0.18);">
                          <div style="font-size:14px;font-weight:700;color:#9a3412;">Why you're receiving this</div>
                          <p style="margin:8px 0 0;font-size:14px;line-height:1.8;color:#6b7280;">
                            This security email helps protect your account during sign-up, login verification, and password recovery.
                            If you did not request this action, you can safely ignore this message.
                          </p>
                        </div>
                      </td>
                    </tr>
                    {action_html}
                    <tr>
                      <td style="padding:0 34px 10px;">
                        <div style="font-size:12px;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;color:#9a3412;">Stay connected</div>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:0 34px 28px;">
                        <table role="presentation" cellspacing="0" cellpadding="0" style="width:100%;">
                          <tr>
                            <td style="padding:0 12px 0 0;">
                              <a href="{links['x']}" style="display:block;text-decoration:none;background:#fff7ed;border:1px solid rgba(251,146,60,0.18);border-radius:18px;padding:14px 12px;text-align:center;color:#9a3412;font-size:12px;font-weight:800;">X</a>
                            </td>
                            <td style="padding:0 12px 0 0;">
                              <a href="mailto:{links['email']}" style="display:block;text-decoration:none;background:#fff7ed;border:1px solid rgba(251,146,60,0.18);border-radius:18px;padding:14px 12px;text-align:center;color:#9a3412;font-size:12px;font-weight:800;">Email</a>
                            </td>
                            <td style="padding:0 12px 0 0;">
                              <a href="tel:{links['phone']}" style="display:block;text-decoration:none;background:#fff7ed;border:1px solid rgba(251,146,60,0.18);border-radius:18px;padding:14px 12px;text-align:center;color:#9a3412;font-size:12px;font-weight:800;">Phone</a>
                            </td>
                            <td style="padding:0 12px 0 0;">
                              <a href="{links['instagram']}" style="display:block;text-decoration:none;background:#fff7ed;border:1px solid rgba(251,146,60,0.18);border-radius:18px;padding:14px 12px;text-align:center;color:#9a3412;font-size:12px;font-weight:800;">IG</a>
                            </td>
                            <td style="padding:0;">
                              <a href="{links['discord']}" style="display:block;text-decoration:none;background:#fff7ed;border:1px solid rgba(251,146,60,0.18);border-radius:18px;padding:14px 12px;text-align:center;color:#9a3412;font-size:12px;font-weight:800;">Discord</a>
                            </td>
                          </tr>
                        </table>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:18px 34px 28px;background:#fffaf5;border-top:1px solid rgba(251,146,60,0.14);font-size:12px;line-height:1.8;color:#9ca3af;">
                        {brand_name} account security email<br />
                        {links['email']} · {links['phone']}
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>
          </body>
        </html>
        """

    def _build_login_notice_plain_text(self, login_context=None):
        brand_name = self._brand_name()
        links = self._brand_links()
        context_lines = []

        if login_context:
            context_lines.extend(
                [
                    f"Time: {login_context.get('timeLabel', 'Unknown')}",
                    f"IP: {login_context.get('ipAddress', 'Unknown')}",
                    f"Device: {login_context.get('deviceLabel', 'Unknown')}",
                    f"Location: {login_context.get('locationLabel', 'Unknown')}",
                    f"New device: {'Yes' if login_context.get('isNewDevice') else 'No'}",
                    f"New location: {'Yes' if login_context.get('isNewLocation') else 'No'}",
                    "",
                ]
            )

        return "\n".join(
            [
                f"{brand_name} login notice",
                "",
                "A sign-in attempt was made on your account.",
                *context_lines,
                "If this was not you, reset your password as soon as possible.",
                "",
                f"Support email: {links['email']}",
                f"Support phone: {links['phone']}",
            ]
        )

    def _build_login_notice_html(self, login_context=None):
        brand_name = self._brand_name()
        links = self._brand_links()
        app_href = self.config.get("APP_BASE_URL")
        context_html = ""

        if login_context:
            context_html = f"""
                    <tr>
                      <td style="padding:0 34px 8px;">
                        <div style="padding:18px 20px;border-radius:20px;background:#fffaf5;border:1px solid rgba(251,146,60,0.18);">
                          <div style="font-size:14px;font-weight:700;color:#9a3412;">Login details</div>
                          <p style="margin:8px 0 0;font-size:14px;line-height:1.85;color:#6b7280;">
                            Time: <strong style="color:#111827;">{login_context.get('timeLabel', 'Unknown')}</strong><br />
                            IP: <strong style="color:#111827;">{login_context.get('ipAddress', 'Unknown')}</strong><br />
                            Device: <strong style="color:#111827;">{login_context.get('deviceLabel', 'Unknown')}</strong><br />
                            Location: <strong style="color:#111827;">{login_context.get('locationLabel', 'Unknown')}</strong><br />
                            New device: <strong style="color:#111827;">{'Yes' if login_context.get('isNewDevice') else 'No'}</strong><br />
                            New location: <strong style="color:#111827;">{'Yes' if login_context.get('isNewLocation') else 'No'}</strong>
                          </p>
                        </div>
                      </td>
                    </tr>
            """

        return f"""
        <!doctype html>
        <html lang="en">
          <head>
            <meta charset="UTF-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            <title>{brand_name} Login Notice</title>
          </head>
          <body style="margin:0;padding:0;background:#fff8f2;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#1f2937;">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#fff8f2;padding:28px 12px;">
              <tr>
                <td align="center">
                  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:620px;background:#ffffff;border-radius:28px;overflow:hidden;border:1px solid rgba(251,146,60,0.18);box-shadow:0 24px 64px rgba(194,65,12,0.12);">
                    <tr>
                      <td style="padding:34px;background:linear-gradient(135deg,#fff7ed 0%,#ffedd5 42%,#fdba74 100%);">
                        <div style="font-size:36px;font-weight:900;letter-spacing:-0.05em;color:#ea580c;line-height:1;">{brand_name}</div>
                        <div style="margin-top:10px;font-size:12px;font-weight:800;letter-spacing:0.16em;text-transform:uppercase;color:#9a3412;">Security Notice</div>
                        <div style="margin-top:18px;font-size:30px;font-weight:850;line-height:1.15;color:#111827;">A sign-in attempt was detected</div>
                        <p style="margin:14px 0 0;font-size:15px;line-height:1.8;color:#7c2d12;">
                          If this was you, no action is needed. If this was not you, please reset your password right away.
                        </p>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:28px 34px;">
                        <a href="{app_href}" style="display:inline-block;background:#ea580c;color:#ffffff;text-decoration:none;font-size:14px;font-weight:800;letter-spacing:0.02em;padding:14px 22px;border-radius:999px;">Open Noob Trade</a>
                      </td>
                    </tr>
                    {context_html}
                    <tr>
                      <td style="padding:18px 34px 28px;background:#fffaf5;border-top:1px solid rgba(251,146,60,0.14);font-size:12px;line-height:1.8;color:#9ca3af;">
                        {links['email']} · {links['phone']}
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>
          </body>
        </html>
        """
