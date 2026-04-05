"""Gmail API client wrapper.

Provides a clean interface over the Google Gmail API for all operations
needed by the Email Patrol agent.
"""

import base64
import re
from email.mime.text import MIMEText
from typing import Optional

import httpx
from googleapiclient.discovery import build

from .auth import get_credentials


class GmailClient:
    """Wrapper around Gmail API with patrol-specific operations."""

    def __init__(self, token_path: Optional[str] = None):
        kwargs = {"token_path": token_path} if token_path else {}
        creds = get_credentials(**kwargs)
        self._service = build("gmail", "v1", credentials=creds)
        self._user = "me"

    def get_profile(self) -> dict:
        return self._service.users().getProfile(userId=self._user).execute()

    def search_emails(self, query: str, max_results: int = 50) -> list[dict]:
        response = (
            self._service.users()
            .messages()
            .list(userId=self._user, q=query, maxResults=max_results)
            .execute()
        )
        return response.get("messages", [])

    def read_email(self, message_id: str) -> dict:
        raw = (
            self._service.users()
            .messages()
            .get(userId=self._user, id=message_id, format="full")
            .execute()
        )
        headers = {h["name"]: h["value"] for h in raw["payload"].get("headers", [])}
        body = self._extract_body(raw["payload"])
        return {
            "id": raw["id"],
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "subject": headers.get("Subject", ""),
            "date": headers.get("Date", ""),
            "labels": raw.get("labelIds", []),
            "body": body,
            "headers": headers,
        }

    def read_thread(self, thread_id: str) -> list[dict]:
        response = (
            self._service.users()
            .threads()
            .get(userId=self._user, id=thread_id, format="full")
            .execute()
        )
        return [self._parse_message(m) for m in response.get("messages", [])]

    def delete_emails(self, message_ids: list[str]) -> list[dict]:
        results = []
        for mid in message_ids:
            self._service.users().messages().trash(userId=self._user, id=mid).execute()
            results.append({"id": mid, "status": "trashed"})
        return results

    def archive_emails(self, message_ids: list[str]) -> list[dict]:
        results = []
        for mid in message_ids:
            self._service.users().messages().modify(
                userId=self._user, id=mid, body={"removeLabelIds": ["INBOX"]},
            ).execute()
            results.append({"id": mid, "status": "archived"})
        return results

    def apply_label(self, message_ids: list[str], label_id: str) -> list[dict]:
        results = []
        for mid in message_ids:
            self._service.users().messages().modify(
                userId=self._user, id=mid, body={"addLabelIds": [label_id]},
            ).execute()
            results.append({"id": mid, "status": "labeled", "label": label_id})
        return results

    def remove_label(self, message_ids: list[str], label_id: str) -> list[dict]:
        results = []
        for mid in message_ids:
            self._service.users().messages().modify(
                userId=self._user, id=mid, body={"removeLabelIds": [label_id]},
            ).execute()
            results.append({"id": mid, "status": "label_removed", "label": label_id})
        return results

    def send_email(self, to: str, subject: str, body: str, thread_id: Optional[str] = None) -> dict:
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        send_body = {"raw": raw}
        if thread_id:
            send_body["threadId"] = thread_id
        return (
            self._service.users()
            .messages()
            .send(userId=self._user, body=send_body)
            .execute()
        )

    def create_draft(self, to: str, subject: str, body: str, thread_id: Optional[str] = None) -> dict:
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        draft_body = {"message": {"raw": raw}}
        if thread_id:
            draft_body["message"]["threadId"] = thread_id
        return (
            self._service.users()
            .drafts()
            .create(userId=self._user, body=draft_body)
            .execute()
        )

    def list_labels(self) -> list[dict]:
        response = self._service.users().labels().list(userId=self._user).execute()
        return response.get("labels", [])

    def unsubscribe(self, message_id: str) -> dict:
        """Multi-strategy unsubscribe. Tries: header > body link > reply."""
        msg = self.read_email(message_id)
        headers = msg["headers"]

        # Strategy 1: List-Unsubscribe header
        unsub_header = headers.get("List-Unsubscribe", "")
        if unsub_header:
            urls = re.findall(r"<(https?://[^>]+)>", unsub_header)
            for url in urls:
                try:
                    resp = httpx.get(url, follow_redirects=True, timeout=10)
                    if resp.status_code < 400:
                        return {"status": "success", "method": "header"}
                except httpx.HTTPError:
                    continue
            mailtos = re.findall(r"<mailto:([^>]+)>", unsub_header)
            if mailtos:
                self.send_email(mailtos[0].split("?")[0], "unsubscribe", "unsubscribe")
                return {"status": "success", "method": "header"}

        # Strategy 2: Scan body for unsubscribe links
        body = msg.get("body", "")
        unsub_patterns = [
            r'href=["\']?(https?://[^"\'>\s]*(?:unsub|opt.?out|manage.?pref|email.?pref)[^"\'>\s]*)',
        ]
        for pattern in unsub_patterns:
            matches = re.findall(pattern, body, re.IGNORECASE)
            for url in matches:
                try:
                    resp = httpx.get(url, follow_redirects=True, timeout=10)
                    if resp.status_code < 400:
                        return {"status": "success", "method": "body_link"}
                except httpx.HTTPError:
                    continue

        return {"status": "failed", "reason": "no_unsubscribe_mechanism_found"}

    def _extract_body(self, payload: dict) -> str:
        if "body" in payload and payload["body"].get("data"):
            return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
        parts = payload.get("parts", [])
        for part in parts:
            if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
        for part in parts:
            if part.get("mimeType") == "text/html" and part.get("body", {}).get("data"):
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
        for part in parts:
            if part.get("parts"):
                return self._extract_body(part)
        return ""

    def _parse_message(self, raw: dict) -> dict:
        headers = {h["name"]: h["value"] for h in raw["payload"].get("headers", [])}
        return {
            "id": raw["id"],
            "from": headers.get("From", ""),
            "subject": headers.get("Subject", ""),
            "date": headers.get("Date", ""),
            "body": self._extract_body(raw["payload"]),
        }
