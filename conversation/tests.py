from django.test import TestCase
from unittest.mock import patch, MagicMock
import datetime
from conversation.models import Contact, Conversation, Message
import conversation.services.latency_determination
from conversation.services.latency_determination import HumanLatencyAgent


class HumanLatencyAgentTestCase(TestCase):
    def setUp(self):
        self.contact = Contact.objects.create(
            email="test@example.com", name="Test User"
        )

        self.conversation = Conversation.objects.create(
            contact=self.contact, thread_id="test-thread-123"
        )

        # Create a few sample messages in the conversation
        # Use timezone-aware datetimes to avoid warnings
        from django.utils import timezone

        current_time = timezone.now()

        self.message1 = Message.objects.create(
            conversation=self.conversation,
            message_id="msg-1",
            message_type="INCOMING",
            subject="Initial inquiry",
            content="Hello, I'm interested in your services.",
            sender="test@example.com",
            receiver="support@company.com",
            timestamp=current_time - datetime.timedelta(days=1),
        )

        self.message2 = Message.objects.create(
            conversation=self.conversation,
            message_id="msg-2",
            message_type="OUTGOING",
            subject="Re: Initial inquiry",
            content="Thank you for your interest. How can we help?",
            sender="support@company.com",
            receiver="test@example.com",
            timestamp=current_time - datetime.timedelta(hours=23),
        )

        self.latest_message = Message.objects.create(
            conversation=self.conversation,
            message_id="msg-3",
            message_type="INCOMING",
            subject="Re: Initial inquiry",
            content="I need urgent assistance with my account.",
            sender="test@example.com",
            receiver="support@company.com",
            timestamp=current_time - datetime.timedelta(hours=2),
        )

    def test_determine_latency_mocked_llm(self):
        latency_agent = HumanLatencyAgent()

        # Configure the agent's run_sync method
        mock_response = MagicMock()
        mock_response.data.urgent = True
        mock_response.data.stuck = False
        mock_response.data.days = 0
        mock_response.data.hours = 0
        mock_response.data.minutes = 5
        latency_agent.agent.run_sync = MagicMock()
        latency_agent.agent.run_sync.return_value = mock_response

        urgent, stuck, latency_minutes = latency_agent.determine_latency(
            self.latest_message
        )

        # Verify results
        self.assertTrue(urgent)
        self.assertFalse(stuck)
        self.assertEqual(latency_minutes, 5)  # 5 minutes

        # Verify the agent was called with expected parameters
        latency_agent.agent.run_sync.assert_called_once()
        # Extract the call argument
        formatted_prompt = latency_agent.agent.run_sync.call_args[0][0]

        # Check if prompt contains key elements
        expected_strings = [
            "You determine how long a person should wait before responding to an email, to maintain natural communication rhythm or meet the other person's expectations.",
            "timestamp:",
            "from:test@example.com",
            "to:support@company.com",
            "to:support@company.com",
            "Conversation History",
            "Current Message",
            "Business hours:",
            "Weekend:",
        ]

        for s in expected_strings:
            self.assertIn(s, formatted_prompt)
