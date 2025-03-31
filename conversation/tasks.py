# conversation/tasks.py
from celery import shared_task
from .services.email_processor import EmailProcessor


@shared_task
def check_for_new_emails():
    """Background task to check for and process new emails"""
    processor = EmailProcessor()
    processor.process_new_emails()


@shared_task
def send_scheduled_emails():
    """Background task to send scheduled email responses"""
    processor = EmailProcessor()
    processor.send_scheduled_responses()
