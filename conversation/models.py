# conversation/models.py
from django.db import models


class Contact(models.Model):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_contact = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.email


class Conversation(models.Model):
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE)
    thread_id = models.CharField(max_length=255, unique=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Conversation with {self.contact.email}"


class Message(models.Model):
    MESSAGE_TYPE_CHOICES = [
        ("INCOMING", "Incoming"),
        ("OUTGOING", "Outgoing"),
        ("DRAFT", "Draft"),
    ]

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    message_id = models.CharField(max_length=255, unique=True)
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPE_CHOICES)
    subject = models.CharField(max_length=512, blank=True)
    content = models.TextField()
    sender = models.EmailField(blank=True, null=True)
    receiver = models.EmailField(blank=True, null=True)
    timestamp = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"timestamp:{self.timestamp}\nfrom:{self.sender}\nto:{self.receiver}\nsubject:{self.subject}\ncontent: {self.content}\n\n"


class ScheduledMessage(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    draft_content = models.TextField()
    draft_subject = models.CharField(max_length=512)
    created_at = models.DateTimeField(auto_now_add=True)
    scheduled_send_time = models.DateTimeField()
    sent = models.BooleanField(default=False)
    canceled = models.BooleanField(default=False)

    def __str__(self):
        return f"Response to {self.conversation.contact.email} at {self.scheduled_send_time}"
