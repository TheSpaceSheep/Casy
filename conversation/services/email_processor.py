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
        print(f"[DEBUG] Processing new email with data: {message_data}")
        message_details = self.gmail.get_message_details(message_data["id"])
        print(f"[DEBUG] Retrieved message details: {message_details}")

        # Get or create contact
        contact, created = Contact.objects.get_or_create(
            email=message_details["from"],
            defaults={"name": ""},  # Extract name in real implementation
        )
        print(f"[DEBUG] {'Created' if created else 'Found'} contact: {contact.email}")

        # Get or create conversation
        conversation, created = Conversation.objects.get_or_create(
            thread_id=message_details["threadId"], defaults={"contact": contact}
        )
        print(
            f"[DEBUG] {'Created' if created else 'Found'} conversation with thread ID: {conversation.thread_id}"
        )

        # Save the incoming message
        message = Message.objects.create(
            conversation=conversation,
            message_id=message_details["id"],
            message_type="INCOMING",
            subject=message_details.get("subject", ""),
            content=message_details["body"],
        )
        print(f"[DEBUG] Saved incoming message with ID: {message.message_id}")

        # Generate a response
        response_content = self.nlp.generate_response(message_details["body"])
        print(f"[DEBUG] Generated response content: {response_content[:100]}...")

        # Determine appropriate latency
        latency_minutes = self.nlp.determine_latency(message_details["body"])
        send_time = timezone.now() + timedelta(minutes=latency_minutes)
        print(
            f"[DEBUG] Determined latency: {latency_minutes} minutes (send time: {send_time})"
        )

        # TODO: determine if we should reply or notify the admin to take over
        # TODO: notify admin

        # Create and schedule response
        draft_id = self.gmail.create_draft(
            to=contact.email,
            subject=f"Re: {message_details.get('subject', '')}",
            body=response_content,
            thread_id=conversation.thread_id,
        )
        print(f"[DEBUG] Created draft with ID: {draft_id}")

        # Schedule the response
        scheduled_message = ScheduledMessage.objects.create(
            conversation=conversation,
            draft_content=response_content,
            draft_subject=f"Re: {message_details.get('subject', '')}",
            scheduled_send_time=send_time,
        )
        print(f"[DEBUG] Scheduled response with ID: {scheduled_message.draft_subject}")

        # Schedule a follow-up if needed
        followup_time = self.nlp.determine_followup_time(message_details["body"])
        print(f"[DEBUG] Determined followup time: {followup_time}")

        followup_subject, followup_content = self.nlp.generate_followup_message()
        print(f"[DEBUG] Generated followup content: {followup_content[:100]}...")

        followup_message = ScheduledMessage.objects.create(
            conversation=conversation,
            draft_content=followup_content,
            draft_subject=followup_subject,
            scheduled_send_time=followup_time,
        )
        print(f"[DEBUG] Scheduled followup with ID: {followup_message.draft_subject}")

    def send_scheduled_messages(self):
        """Send all scheduled responses whose time has come"""
        now = timezone.now()
        print(f"[DEBUG] Checking for scheduled messages to send at {now}")
        messages_to_send = ScheduledMessage.objects.filter(
            scheduled_send_time__lte=now, sent=False
        )
        print(f"[DEBUG] Found {messages_to_send.count()} messages to process")

        for message in messages_to_send:
            print(f"[DEBUG] Processing scheduled message : {message.draft_subject}")
            conversation = message.conversation
            print(f"[DEBUG] Associated conversation : {conversation.id}")

            # Check if there's been a response since scheduling the followup
            latest_message = (
                Message.objects.filter(conversation=conversation)
                .order_by("-timestamp")
                .first()
            )

            if latest_message:
                print(
                    f"[DEBUG] Latest message in conversation:\n {latest_message.content}\n#########################\nType {latest_message.message_type}, timestamp {latest_message.timestamp}"
                )

            if (
                latest_message
                and latest_message.message_type == "INCOMING"
                and latest_message.timestamp > message.created_at
            ):
                print(
                    "[DEBUG] New incoming message detected - canceling scheduled response"
                )
                message.canceled = True
                message.save()
                print(
                    f"[DEBUG] Marked message as canceled : \n{message.draft_content}\n "
                )
                continue

            print(f"[DEBUG] Preparing to send message ID: {message.draft_subject}")
            try:
                message_id = self.gmail.send_email(
                    to=message.conversation.contact.email,
                    subject=message.draft_subject,
                    body=message.draft_content,
                    thread_id=message.conversation.thread_id,
                )
                print(f"[DEBUG] Successfully sent email with message ID: {message_id}")
            except Exception as e:
                print(f"[ERROR] Failed to send email: {str(e)}")
                continue

            # Save the outgoing message
            outgoing_message = Message.objects.create(
                conversation=message.conversation,
                message_id=message_id,
                message_type="OUTGOING",
                subject=message.draft_subject,
                content=message.draft_content,
            )
            print(f"[DEBUG] Created outgoing message record ID: {outgoing_message.id}")

            # Mark as sent
            message.sent = True
            message.save()
            print(f"[DEBUG] Marked scheduled message ID {message.id} as sent")
