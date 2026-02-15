import asyncio
from typing import Optional, Tuple

from platform_common.config.settings import get_settings
from platform_common.db.dal.notification_outbox_dal import NotificationOutboxDAL
from platform_common.db.session import get_session
from platform_common.logging.logging import get_logger
from platform_common.models.notification_outbox import NotificationOutbox
from platform_common.utils.time_helpers import get_current_epoch

from app.api.handler.email_handler import EmailHandler
from app.api.handler.mailgun_handler import MailgunEmailHandler

logger = get_logger("notification_outbox_worker")

MAX_ATTEMPTS = 10
CLAIM_LIMIT = 25
POLL_INTERVAL_SECONDS = 1.5
MIN_BACKOFF_SECONDS = 10
MAX_BACKOFF_SECONDS = 3600


def _compute_backoff_seconds(attempt_count_after_failure: int) -> int:
    # 10s, 20s, 40s, ... capped at 1h
    return max(
        MIN_BACKOFF_SECONDS,
        min(MAX_BACKOFF_SECONDS, MIN_BACKOFF_SECONDS * (2 ** max(0, attempt_count_after_failure - 1))),
    )


def _render_email(template_key: Optional[str], payload: dict) -> Tuple[str, str]:
    key = template_key or "generic_email"

    if key == "org_invite_email":
        org_name = payload.get("organization_name") or "your organization"
        role = payload.get("role") or "member"
        accept_url = payload.get("accept_url") or ""
        return (
            f"You were invited to join {org_name}",
            f"You were invited to join {org_name} as {role}.\n\nAccept invitation:\n{accept_url}",
        )

    if key == "resource_invite_email":
        resource_type = payload.get("resource_type") or "resource"
        resource_name = payload.get("resource_name") or payload.get("resource_id") or "resource"
        accept_url = payload.get("accept_url") or ""
        return (
            f"You were invited to collaborate on {resource_name}",
            f"You were invited to collaborate on {resource_type} '{resource_name}'.\n\nAccept invitation:\n{accept_url}",
        )

    if key == "user_invite_email":
        display_name = payload.get("display_name") or "there"
        accept_url = payload.get("accept_url") or ""
        return (
            "Verify your email",
            f"Hi {display_name},\n\nPlease verify your email by clicking:\n{accept_url}",
        )

    return (
        payload.get("subject") or "Notification",
        payload.get("content") or "You have a new notification.",
    )


async def _send_email(to_email: str, subject: str, content: str) -> None:
    settings = get_settings()
    from_email = settings.email_from

    sendgrid_error = None
    try:
        await asyncio.to_thread(
            EmailHandler().send_email,
            to_email,
            from_email,
            subject,
            content,
        )
        return
    except Exception as exc:  # fallback path
        sendgrid_error = exc
        logger.warning(f"SendGrid send failed, attempting Mailgun fallback: {exc}")

    try:
        await asyncio.to_thread(
            MailgunEmailHandler().send_email,
            to_email,
            from_email,
            subject,
            content,
        )
    except Exception as exc:
        if sendgrid_error:
            raise RuntimeError(
                f"SendGrid failed ({sendgrid_error}); Mailgun failed ({exc})"
            )
        raise RuntimeError(f"Mailgun send failed: {exc}")


async def process_notification_outbox_once() -> int:
    processed = 0

    async for session in get_session():
        dal = NotificationOutboxDAL(session)
        batch = await dal.claim_batch(channel="email", limit=CLAIM_LIMIT)

        for row in batch:
            processed += 1
            await _process_item(dal, row)

        break

    return processed


async def _process_item(dal: NotificationOutboxDAL, row: NotificationOutbox) -> None:
    try:
        if not row.recipient_email:
            raise RuntimeError("Outbox item missing recipient_email")

        subject, content = _render_email(row.template_key, row.payload or {})
        await _send_email(row.recipient_email, subject, content)
        await dal.mark_sent(row.id)
    except Exception as exc:
        err_msg = str(exc)
        next_attempt_number = (row.attempt_count or 0) + 1
        if next_attempt_number >= MAX_ATTEMPTS:
            await dal.mark_dead(row.id, err_msg)
            logger.error(
                f"Notification outbox item {row.id} moved to dead after {next_attempt_number} attempts: {err_msg}"
            )
            return

        backoff_seconds = _compute_backoff_seconds(next_attempt_number)
        next_attempt_at = get_current_epoch() + backoff_seconds
        await dal.mark_failed(row.id, err_msg, next_attempt_at)
        logger.warning(
            f"Notification outbox item {row.id} failed attempt {next_attempt_number}: {err_msg}"
        )


async def start_notification_outbox_worker() -> None:
    while True:
        try:
            await process_notification_outbox_once()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception(f"Outbox worker loop failed: {exc}")

        await asyncio.sleep(POLL_INTERVAL_SECONDS)
