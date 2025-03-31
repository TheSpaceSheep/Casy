# conversation/management/commands/check_emails.py
from django.core.management.base import BaseCommand
from conversation.services.email_processor import EmailProcessor


class Command(BaseCommand):
    help = "Manually check for new emails and process them"

    def handle(self, *args, **kwargs):
        processor = EmailProcessor()

        self.stdout.write("Checking for new emails...")
        processor.process_new_emails()

        self.stdout.write("Sending scheduled responses...")
        processor.send_scheduled_messages()

        self.stdout.write(self.style.SUCCESS("Email processing completed!"))
