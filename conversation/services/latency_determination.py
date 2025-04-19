from pydantic_ai import Agent
from pydantic import BaseModel, Field, field_validator
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from typing import Optional, List, Dict, Any
import random
import datetime
from conversation.models import Message
from django.conf import settings

import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


model = OpenAIModel(
    "google/gemini-2.0-flash-lite-001",
    provider=OpenAIProvider(
        base_url="https://openrouter.ai/api/v1", api_key=settings.OPENROUTER_API_KEY
    ),
)


class LatencyDetermination(BaseModel):
    """Model for determining appropriate response latency."""

    reasoning: str = Field(
        ..., description="The reasoning behind this latency determination"
    )
    days: int = Field(..., ge=0, description="The determined response time in days")
    hours: int = Field(..., ge=0, description="The determined response time in hours")
    minutes: int = Field(
        ..., ge=0, description="The determined response time in minutes (minimum 1)"
    )
    urgent: bool = Field(
        ...,
        description="Whether the response is urgent and requires immediate action (yes/no)",
    )
    stuck: bool = Field(
        ...,
        description="Whether the conversation needs waiting for a followup or an external event",
    )


class LatencyConfig(BaseModel):
    """Configuration for latency determination"""

    business_hours_start: int = 9  # 9 AM
    business_hours_end: int = 17  # 5 PM


class HumanLatencyAgent:
    """Agent for determining human-like response latency."""

    def __init__(self, config: Optional[LatencyConfig] = None):
        """
        Initialize the agent with the specified model and configuration.

        Args:
            model_name: The name of the LLM model to use
            config: Optional configuration for latency determination
        """
        self.agent = Agent(model=model, result_type=LatencyDetermination)
        self.config = config or LatencyConfig()
        logger.info(f"HumanLatencyAgent initialized.")

    def determine_latency(self, message: Message):
        now = datetime.datetime.now()
        business_hours = (
            self.config.business_hours_start
            <= int(now.hour)
            < self.config.business_hours_end
        )
        weekend = now.weekday() >= 5  # 5 and 6 are saturday and sunday

        try:
            # Format conversation history
            conversation_history = ""

            # Get messages in chronological order
            messages = message.conversation.messages.all()
            # Sort in Python to avoid database ordering issues
            print(message)
            messages_sorted = sorted(
                messages,
                key=lambda m: m.timestamp if m.timestamp else datetime.datetime.min,
            )

            for msg in messages_sorted:
                conversation_history += str(msg)

            time = str(datetime.datetime.now())
            business_hours_yn = "yes" if business_hours else "no"
            weekend_yn = "yes" if weekend else "no"

            # Get response from agent
            with open("conversation/prompts/determine_latency.prompt", "r") as p_file:
                prompt = p_file.read()

            # Format prompt
            prompt = prompt.format(
                conversation_history=conversation_history,
                message=str(message),
                time=time,
                business_hours_yn=business_hours_yn,
                weekend_yn=weekend_yn,
            )

            response = self.agent.run_sync(prompt)
            print("HERE")
            print(response)

            return (
                response.data.urgent,
                response.data.stuck,
                response.data.days * 24 * 60
                + response.data.hours * 60
                + response.data.minutes,
            )
        except Exception as e:
            logger.error(f"Error determining latency: {e}", exc_info=True)
            # Fallback to reasonable default in case of any errors
            # Since the message content appears to indicate urgency, default to urgent
            return (False, False, random.randint(30, 60))
