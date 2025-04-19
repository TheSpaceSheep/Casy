from django.core.management.base import BaseCommand
from conversation.services.gmail_service import GmailService


class Command(BaseCommand):
    help = "Set up Gmail API authentication"

    def handle(self, *args, **kwargs):
        self.stdout.write("Setting up Gmail API authentication...")

        # This will trigger the OAuth flow if needed
        service = GmailService()

        if service.service:
            self.stdout.write(
                self.style.SUCCESS("Gmail API authentication successful!")
            )
        else:
            self.stdout.write(self.style.ERROR("Failed to authenticate with Gmail API"))
