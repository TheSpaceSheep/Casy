# conversation/services/email_processor.py
from datetime import datetime, timedelta
from django.utils import timezone

from ..models import (
    Contact,
    Conversation,
    Message,
    ScheduledMessage,
)
from .gmail_service import GmailService
from .nlp_service import NLPService


class EmailProcessor:
    def __init__(self):
        self.gmail = GmailService()
        self.nlp = NLPService()

    def process_new_emails(self):
        """Process all new unread emails"""
        unread_messages = self.gmail.get_unread_messages()

        for message_data in unread_messages:
            self._process_single_email(message_data)

    def _process_single_email(self, message_data):
        """Process a single email message"""
        message_details = self.gmail.get_message_details(message_data["id"])

        # Get or create contact
        contact, _ = Contact.objects.get_or_create(
            email=message_details["from"],
            defaults={"name": ""},  # Extract name in real implementation
        )

        # Get or create conversation
        conversation, _ = Conversation.objects.get_or_create(
            thread_id=message_details["threadId"], defaults={"contact": contact}
        )

        # Save the incoming message
        Message.objects.create(
            conversation=conversation,
            message_id=message_details["id"],
            message_type="INCOMING",
            subject=message_details.get("subject", ""),
            content=message_details["body"],
        )

        # Generate a response
        response_content = self.nlp.generate_response(message_details["body"])

        # Determine appropriate latency
        latency_minutes = self.nlp.determine_latency(message_details["body"])
        send_time = timezone.now() + timedelta(minutes=latency_minutes)

        # TODO: determine if we should reply or notify the admin to take over
        # TODO: notify admin

        # Create and schedule response
        draft_id = self.gmail.create_draft(
            to=contact.email,
            subject=f"Re: {message_details.get('subject', '')}",
            body=response_content,
            thread_id=conversation.thread_id,
        )

        # Schedule the response
        ScheduledMessage.objects.create(
            conversation=conversation,
            draft_content=response_content,
            draft_subject=f"Re: {message_details.get('subject', '')}",
            scheduled_send_time=send_time,
        )

        # Schedule a follow-up if needed
        followup_time = self.nlp.determine_followup_time(message_details["body"])

        followup_subject, followup_content = self.nlp.generate_followup_message()

        ScheduledMessage.objects.create(
            conversation=conversation,
            draft_content=followup_content,
            draft_subject=followup_subject,
            scheduled_send_time=followup_time,
        )

    def send_scheduled_messages(self):
        """Send all scheduled responses whose time has come"""
        now = timezone.now()
        messages_to_send = ScheduledMessage.objects.filter(
            scheduled_send_time__lte=now, sent=False
        )

        for message in messages_to_send:
            conversation = message.conversation
            # Check if there's been a response since scheduling the followup
            latest_message = (
                Message.objects.filter(conversation=conversation)
                .order_by("-timestamp")
                .first()
            )

            if (
                latest_message
                and latest_message.message_type == "INCOMING"
                and latest_message.timestamp > message.created_at
            ):
                # Skip as there's been a new email since the last one
                message.canceled = True
                message.save()
                continue
            # Send the email
            message_id = self.gmail.send_email(
                to=message.conversation.contact.email,
                subject=message.draft_subject,
                body=message.draft_content,
                thread_id=message.conversation.thread_id,
            )

            # Save the outgoing message
            Message.objects.create(
                conversation=message.conversation,
                message_id=message_id,
                message_type="OUTGOING",
                subject=message.draft_subject,
                content=message.draft_content,
            )

            # Mark as sent
            message.sent = True
            message.save()
