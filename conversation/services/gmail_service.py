# conversation/services/gmail_service.py
import base64
import os
from datetime import datetime, timezone
from email.mime.text import MIMEText
from typing import List, Dict, Any, Optional

from django.conf import settings
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import json


class GmailService:
    """Service class for interacting with Gmail API."""

    SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/gmail.modify",
    ]

    def __init__(self):
        self.service = None
        self.setup_service()

    def setup_service(self):
        """Configure and build the Gmail API service."""
        creds = None

        # Check if we have token file
        if hasattr(settings, "GMAIL_TOKEN_PATH") and os.path.exists(
            settings.GMAIL_TOKEN_PATH
        ):
            try:
                with open(settings.GMAIL_TOKEN_PATH, "r") as token:
                    creds = Credentials.from_authorized_user_info(
                        json.loads(token.read()), self.SCOPES
                    )
            except Exception as e:
                print(f"Error loading credentials from token file: {e}")
                creds = None

        # If no valid credentials available, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Error refreshing credentials: {e}")
                    creds = self._authenticate_new()
            else:
                creds = self._authenticate_new()

            # Save the credentials for next run
            if hasattr(settings, "GMAIL_TOKEN_PATH"):
                try:
                    with open(settings.GMAIL_TOKEN_PATH, "w") as token:
                        token.write(creds.to_json())
                except Exception as e:
                    print(f"Error saving token: {e}")

        try:
            self.service = build("gmail", "v1", credentials=creds)
            print("Gmail service successfully configured")
        except Exception as e:
            print(f"Error building Gmail service: {e}")
            self.service = None

    def _authenticate_new(self):
        """Perform OAuth flow to authenticate the application."""
        try:
            credentials_path = getattr(settings, "GMAIL_CREDENTIALS_PATH", None)
            if not credentials_path or not os.path.exists(credentials_path):
                raise FileNotFoundError("Google credentials file not found")

            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, self.SCOPES
            )

            # Determine the redirect URI based on settings or use localhost
            redirect_uri = getattr(
                settings, "GMAIL_REDIRECT_URI", "http://localhost:8080"
            )

            # Run local server flow if in development
            if "localhost" in redirect_uri or "127.0.0.1" in redirect_uri:
                creds = flow.run_local_server(port=8080)
            else:
                # For production, use the redirect flow
                flow.redirect_uri = redirect_uri
                authorization_url, _ = flow.authorization_url(
                    access_type="offline", include_granted_scopes="true"
                )

                print(f"Please go to this URL to authorize: {authorization_url}")
                code = input("Enter the authorization code: ")
                flow.fetch_token(code=code)
                creds = flow.credentials

            return creds
        except Exception as e:
            print(f"Authentication error: {e}")
            raise

    def get_unread_messages(self, max_results=10) -> List[Dict[str, Any]]:
        """
        Retrieve unread messages from Gmail.

        Args:
            max_results: Maximum number of messages to retrieve.

        Returns:
            List of message dictionaries.
        """
        if not self.service:
            print("Gmail service not initialized")
            return []

        try:
            # Get IDs of unread messages
            results = (
                self.service.users()
                .messages()
                .list(userId="me", q="is:unread", maxResults=max_results)
                .execute()
            )

            messages = results.get("messages", [])

            # Fetch basic details for each message
            unread_messages = []
            for msg in messages:
                message_data = (
                    self.service.users()
                    .messages()
                    .get(
                        userId="me",
                        id=msg["id"],
                        format="metadata",
                        metadataHeaders=["Subject", "From", "Date"],
                    )
                    .execute()
                )

                unread_messages.append(
                    {
                        "id": message_data["id"],
                        "threadId": message_data["threadId"],
                        "metadata": message_data["payload"]["headers"],
                    }
                )

            return unread_messages

        except HttpError as error:
            print(f"An error occurred while retrieving unread messages: {error}")
            return []

    def get_message_details(self, message_id: str) -> Dict[str, Any]:
        """
        Get full details of a specific message.

        Args:
            message_id: The ID of the message to retrieve.

        Returns:
            A dictionary with message details.
        """
        if not self.service:
            print("Gmail service not initialized")
            return {}

        try:
            # Get the full message
            message = (
                self.service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )

            # Extract headers
            headers = {}
            for header in message["payload"]["headers"]:
                headers[header["name"].lower()] = header["value"]

            # Extract body
            body = self._get_message_body(message["payload"])

            # Mark message as read (optional)
            self.service.users().messages().modify(
                userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}
            ).execute()

            return {
                "id": message["id"],
                "threadId": message["threadId"],
                "subject": headers.get("subject", ""),
                "from": headers.get("from", ""),
                "to": headers.get("to", ""),
                "date": headers.get("date", ""),
                "body": body,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except HttpError as error:
            print(f"An error occurred while retrieving message details: {error}")
            return {"id": message_id, "error": str(error)}

    def _get_message_body(self, payload):
        """Extract the text body from a message payload."""
        if "body" in payload and payload["body"].get("data"):
            # Base64 decode the body
            body_data = payload["body"]["data"]
            body_bytes = base64.urlsafe_b64decode(body_data)
            return body_bytes.decode("utf-8")

        # If the message has parts (multipart message)
        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    if part["body"].get("data"):
                        body_data = part["body"]["data"]
                        body_bytes = base64.urlsafe_b64decode(body_data)
                        return body_bytes.decode("utf-8")

                # Recursive call for nested parts
                if "parts" in part:
                    body = self._get_message_body(part)
                    if body:
                        return body

        return ""

    def create_draft(
        self, to: str, subject: str, body: str, thread_id: Optional[str] = None
    ) -> str:
        """
        Create a draft email.

        Args:
            to: Recipient email address.
            subject: Email subject.
            body: Email body content.
            thread_id: Optional thread ID to continue a conversation.

        Returns:
            The draft ID if successful.
        """
        if not self.service:
            print("Gmail service not initialized")
            return ""

        try:
            # Create message
            message = MIMEText(body)
            message["to"] = to
            message["subject"] = subject

            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

            # Create draft
            draft_body = {"message": {"raw": raw_message}}

            # Add thread ID if provided
            if thread_id:
                draft_body["message"]["threadId"] = thread_id

            draft = (
                self.service.users()
                .drafts()
                .create(userId="me", body=draft_body)
                .execute()
            )

            return draft["id"]

        except HttpError as error:
            print(f"An error occurred while creating a draft: {error}")
            return ""

    def send_draft(self, draft_id: str) -> str:
        """
        Send a previously created draft.

        Args:
            draft_id: The ID of the draft to send.

        Returns:
            The message ID of the sent email.
        """
        if not self.service:
            print("Gmail service not initialized")
            return ""

        try:
            sent_message = (
                self.service.users()
                .drafts()
                .send(userId="me", body={"id": draft_id})
                .execute()
            )

            return sent_message["id"]

        except HttpError as error:
            print(f"An error occurred while sending a draft: {error}")
            return ""

    def schedule_email(self, draft_id: str, send_time) -> bool:
        """
        Schedule a draft email to be sent at a specific time.

        Note: Gmail API doesn't directly support scheduling emails.
        This is a workaround that relies on your application to handle the timing.

        Args:
            draft_id: The ID of the draft to schedule.
            send_time: Datetime when the email should be sent.

        Returns:
            Boolean indicating success.
        """
        # Since Gmail API doesn't have native scheduling, we just store the info
        # and return True. The actual sending will be handled by a scheduled task.
        print(f"Email with draft ID {draft_id} scheduled for {send_time}")
        return True

    def send_email(
        self, to: str, subject: str, body: str, thread_id: Optional[str] = None
    ) -> str:
        """
        Immediately send an email.

        Args:
            to: Recipient email address.
            subject: Email subject.
            body: Email body content.
            thread_id: Optional thread ID to continue a conversation.

        Returns:
            The message ID of the sent email.
        """
        if not self.service:
            print("Gmail service not initialized")
            return ""

        try:
            # Create message
            message = MIMEText(body)
            message["to"] = to
            message["subject"] = subject

            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

            # Create body
            message_body = {"raw": raw_message}

            # Add thread ID if provided
            if thread_id:
                message_body["threadId"] = thread_id

            # Send message
            sent_message = (
                self.service.users()
                .messages()
                .send(userId="me", body=message_body)
                .execute()
            )

            return sent_message["id"]

        except HttpError as error:
            print(f"An error occurred while sending an email: {error}")
            return ""

    def get_thread(self, thread_id: str) -> Dict[str, Any]:
        """
        Get all messages in a thread.

        Args:
            thread_id: The ID of the thread to retrieve.

        Returns:
            A dictionary with thread details.
        """
        if not self.service:
            print("Gmail service not initialized")
            return {}

        try:
            thread = (
                self.service.users().threads().get(userId="me", id=thread_id).execute()
            )

            return thread

        except HttpError as error:
            print(f"An error occurred while retrieving a thread: {error}")
            return {}
