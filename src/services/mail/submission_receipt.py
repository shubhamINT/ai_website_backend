import datetime as dt
import html
import uuid
from dataclasses import dataclass

from src.services.mail.context_email import send_email_message


@dataclass(frozen=True)
class SubmissionReceiptResult:
    sent: bool
    message: str
    reference_id: str
    submitted_at: str


_RECEIPT_CONFIG = {
    "contact_form": {
        "reference_prefix": "CNT",
        "subject": "Indus Net | Contact Request Receipt",
        "heading": "Your contact request receipt",
        "intro": "This email includes a copy of the contact details captured during your session.",
        "detail_label": "Reason for reaching out",
        "next_steps": [
            "Keep this reference ID if you need to follow up on the same request.",
            "We recommend keeping this email for your records.",
        ],
    },
    "job_application": {
        "reference_prefix": "JOB",
        "subject": "Indus Net | Job Application Receipt",
        "heading": "Your job application receipt",
        "intro": "This email includes a copy of the job application details captured during your session.",
        "detail_label": "Role or opportunity",
        "next_steps": [
            "Keep this reference ID if you want to follow up on this application.",
            "We recommend keeping this email with the details you submitted.",
        ],
    },
}


def _build_reference_id(prefix: str, submitted_at: dt.datetime) -> str:
    timestamp = submitted_at.strftime("%Y%m%d%H%M%S")
    suffix = uuid.uuid4().hex[:6].upper()
    return f"{prefix}-{timestamp}-{suffix}"


def _format_submitted_at(submitted_at: dt.datetime) -> str:
    return submitted_at.strftime("%Y-%m-%d %H:%M:%S UTC")


def _build_details_rows(details: list[tuple[str, str]]) -> str:
    rows = []
    for label, value in details:
        rows.append(
            "<tr>"
            f'<td style="padding: 12px 14px; border: 1px solid #dbe4ee; width: 180px; '
            f'font-weight: 700; color: #334155; background-color: #f8fafc;">{html.escape(label)}</td>'
            f'<td style="padding: 12px 14px; border: 1px solid #dbe4ee; color: #0f172a;">{html.escape(value)}</td>'
            "</tr>"
        )
    return "".join(rows)


def _build_next_steps_html(next_steps: list[str]) -> str:
    items = []
    for step in next_steps:
        items.append(f'<li style="margin: 0 0 10px;">{html.escape(step)}</li>')
    return "".join(items)


def _compose_submission_receipt(
    submission_type: str,
    user_name: str,
    user_email: str,
    user_phone: str,
    detail_value: str,
    submitted_at: dt.datetime,
) -> tuple[str, str, str, str, str]:
    if submission_type not in _RECEIPT_CONFIG:
        raise ValueError(f"Unsupported submission type: {submission_type}")

    config = _RECEIPT_CONFIG[submission_type]
    reference_id = _build_reference_id(config["reference_prefix"], submitted_at)
    submitted_at_text = _format_submitted_at(submitted_at)
    cleaned_name = user_name.strip()
    greeting_name = cleaned_name or "there"
    cleaned_detail_value = detail_value.strip() or "Not provided"

    details = [
        ("Reference ID", reference_id),
        ("Submitted at", submitted_at_text),
        ("Status", "Received"),
        ("Name", cleaned_name or "Not provided"),
        ("Email", user_email.strip()),
        ("Phone", user_phone.strip() or "Not provided"),
        (config["detail_label"], cleaned_detail_value),
    ]

    plain_lines = [
        config["heading"],
        "",
        f"Hi {greeting_name},",
        "",
        config["intro"],
        "",
        "Submission details:",
    ]
    plain_lines.extend(f"- {label}: {value}" for label, value in details)
    plain_lines.extend(["", "Next steps:"])
    plain_lines.extend(f"- {step}" for step in config["next_steps"])
    plain_lines.extend(["", "Indus Net Assistant"])
    plain_text = "\n".join(plain_lines)

    html_body = (
        "<!doctype html>"
        '<html lang="en">'
        "<head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        f"<title>{html.escape(config['subject'])}</title>"
        "</head>"
        "<body style=\"margin: 0; padding: 0; background-color: #edf2f7; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; color: #1e293b;\">"
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background: linear-gradient(180deg, #e2e8f0 0%, #f8fafc 100%); padding: 32px 16px;">'
        '<tr><td align="center">'
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width: 680px; background-color: #ffffff; border: 1px solid #dbe4ee; border-radius: 18px; overflow: hidden; box-shadow: 0 18px 42px rgba(15, 23, 42, 0.08);">'
        '<tr><td style="padding: 28px 32px; background: linear-gradient(135deg, #0f172a 0%, #1d4ed8 100%);">'
        '<p style="margin: 0 0 10px; font-size: 12px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: #bfdbfe;">Indus Net Assistant</p>'
        f'<h1 style="margin: 0; font-size: 28px; line-height: 1.2; font-weight: 700; color: #ffffff;">{html.escape(config["heading"])}</h1>'
        "</td></tr>"
        '<tr><td style="padding: 32px;">'
        '<p style="margin: 0 0 12px; font-size: 16px; line-height: 1.6; color: #0f172a;">'
        f"Hi {html.escape(greeting_name)},"
        "</p>"
        f'<p style="margin: 0 0 24px; font-size: 15px; line-height: 1.7; color: #334155;">{html.escape(config["intro"])}</p>'
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse: collapse; margin-bottom: 24px;">'
        f"{_build_details_rows(details)}"
        "</table>"
        '<h2 style="margin: 0 0 14px; font-size: 14px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: #475569;">Next Steps</h2>'
        '<ul style="margin: 0; padding-left: 22px; font-size: 15px; line-height: 1.7; color: #0f172a;">'
        f"{_build_next_steps_html(config['next_steps'])}"
        "</ul>"
        "</td></tr>"
        '<tr><td style="padding: 18px 32px 24px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #64748b;">Shared by Indus Net Assistant.</td></tr>'
        "</table>"
        "</td></tr>"
        "</table>"
        "</body>"
        "</html>"
    )

    return (
        config["subject"],
        plain_text,
        html_body,
        reference_id,
        submitted_at_text,
    )


async def send_submission_receipt(
    recipient_email: str,
    submission_type: str,
    user_name: str,
    user_phone: str,
    detail_value: str,
) -> SubmissionReceiptResult:
    submitted_at = dt.datetime.now(dt.timezone.utc)
    subject, plain_text, html_body, reference_id, submitted_at_text = (
        _compose_submission_receipt(
            submission_type=submission_type,
            user_name=user_name,
            user_email=recipient_email,
            user_phone=user_phone,
            detail_value=detail_value,
            submitted_at=submitted_at,
        )
    )

    sent, message = await send_email_message(
        recipient_email=recipient_email,
        subject=subject,
        plain_text=plain_text,
        html_body=html_body,
    )
    return SubmissionReceiptResult(
        sent=sent,
        message=message,
        reference_id=reference_id,
        submitted_at=submitted_at_text,
    )
