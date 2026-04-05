"""Tests for Gmail API client wrapper."""

import pytest
from unittest.mock import MagicMock, patch
from email_patrol.gmail import GmailClient


@pytest.fixture
def mock_service():
    return MagicMock()


@pytest.fixture
def client(mock_service):
    with patch("email_patrol.gmail.build") as mock_build:
        mock_build.return_value = mock_service
        c = GmailClient.__new__(GmailClient)
        c._service = mock_service
        c._user = "me"
        return c


class TestSearchEmails:
    def test_search_returns_messages(self, client, mock_service):
        mock_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1", "threadId": "t1"}],
            "resultSizeEstimate": 1,
        }
        results = client.search_emails("is:unread", max_results=10)
        assert len(results) == 1
        assert results[0]["id"] == "msg1"

    def test_search_empty_returns_empty_list(self, client, mock_service):
        mock_service.users().messages().list().execute.return_value = {
            "resultSizeEstimate": 0,
        }
        results = client.search_emails("from:nobody@example.com")
        assert results == []


class TestReadEmail:
    def test_read_returns_parsed_message(self, client, mock_service):
        mock_service.users().messages().get().execute.return_value = {
            "id": "msg1",
            "payload": {
                "headers": [
                    {"name": "From", "value": "test@example.com"},
                    {"name": "Subject", "value": "Test Subject"},
                    {"name": "Date", "value": "Fri, 4 Apr 2026 09:00:00 +0800"},
                ],
                "body": {"data": "SGVsbG8gV29ybGQ="},
            },
            "labelIds": ["INBOX"],
        }
        msg = client.read_email("msg1")
        assert msg["from"] == "test@example.com"
        assert msg["subject"] == "Test Subject"


class TestDeleteEmails:
    def test_delete_moves_to_trash(self, client, mock_service):
        mock_service.users().messages().trash().execute.return_value = {"id": "msg1"}
        result = client.delete_emails(["msg1"])
        assert result == [{"id": "msg1", "status": "trashed"}]
        mock_service.users().messages().trash.assert_called()


class TestArchiveEmails:
    def test_archive_removes_inbox_label(self, client, mock_service):
        mock_service.users().messages().modify().execute.return_value = {"id": "msg1"}
        result = client.archive_emails(["msg1"])
        assert result == [{"id": "msg1", "status": "archived"}]


class TestSendEmail:
    def test_send_creates_and_sends_message(self, client, mock_service):
        mock_service.users().messages().send().execute.return_value = {
            "id": "sent1",
            "labelIds": ["SENT"],
        }
        result = client.send_email("to@example.com", "Subject", "Body text")
        assert result["id"] == "sent1"


class TestCreateDraft:
    def test_create_draft_returns_draft_id(self, client, mock_service):
        mock_service.users().drafts().create().execute.return_value = {
            "id": "draft1",
            "message": {"id": "msg1"},
        }
        result = client.create_draft("to@example.com", "Subject", "Body")
        assert result["id"] == "draft1"


class TestUnsubscribe:
    def test_unsubscribe_via_header(self, client, mock_service):
        mock_service.users().messages().get().execute.return_value = {
            "id": "msg1",
            "payload": {
                "headers": [
                    {"name": "List-Unsubscribe", "value": "<https://example.com/unsub>"},
                    {"name": "From", "value": "news@example.com"},
                    {"name": "Subject", "value": "Newsletter"},
                ],
                "body": {"data": ""},
            },
            "labelIds": ["INBOX"],
        }
        with patch("email_patrol.gmail.httpx") as mock_httpx:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_httpx.get.return_value = mock_response
            result = client.unsubscribe("msg1")
        assert result["status"] == "success"
        assert result["method"] == "header"

    def test_unsubscribe_no_mechanism_fails(self, client, mock_service):
        mock_service.users().messages().get().execute.return_value = {
            "id": "msg1",
            "payload": {
                "headers": [
                    {"name": "From", "value": "spam@example.com"},
                    {"name": "Subject", "value": "Buy now"},
                ],
                "body": {"data": "Tm8gdW5zdWJzY3JpYmUgbGluaw=="},
            },
            "labelIds": [],
        }
        result = client.unsubscribe("msg1")
        assert result["status"] == "failed"
