import random
from datetime import datetime, timedelta
from conversation.services.latency_determination import determine_latency


class EmailConversationAgent:
    """The main agent for interacting with users via email."""

    def generate_response(self, incoming_message: str, contact_history=None) -> str:
        """Generate a response to an incoming message"""
        # Dummy implementation
        templates = [
            "Thanks for your message. Could you tell me more about that?",
            "I appreciate you sharing this. What else is important to you?",
            "That's interesting. How does this impact your daily life?",
            "I'd like to understand better. Can you elaborate on your goals?",
        ]
        return random.choice(templates)

    def determine_latency(self, message_content: str, contact_history=None) -> int:
        """Determine appropriate response latency in minutes"""
        return determine_latency(message_content, contact_history)

    def determine_followup_time(
        self, message_content: str, contact_history=None
    ) -> datetime:
        """Determine when to follow up if no response is received"""
        # Dummy implementation - follow up in 2-5 days
        days = random.randint(2, 5)
        return datetime.now() + timedelta(days=days)

    def generate_followup_message(self, conversation_history=None) -> tuple:
        """Generate a follow-up message when no response has been received"""
        # Dummy implementation
        subject = "Checking in"
        templates = [
            "I wanted to follow up on our conversation. How are you doing?",
            "Just checking in to see if you had any thoughts on our last exchange.",
            "Hope you're well. I'm following up on our previous conversation.",
            "I was thinking about our discussion and wanted to check in with you.",
        ]
        return subject, random.choice(templates)
