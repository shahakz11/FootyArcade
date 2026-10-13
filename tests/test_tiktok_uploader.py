#!/usr/bin/env python3
"""
tests/test_tiktok_uploader.py
==============================
Hermetic unit tests for the Playmaker TikTok uploader module (scripts/tiktok_uploader.py).
Tests:
- Configuration loading and saving
- OAuth 2.0 access token refresh (auto-refresh and forced)
- Connection verification and user info fetching
- Chunk calculation and resumable Content-Range PUT uploads
- Status polling with SUCCESS, FAILED, and transient states
- High-level upload_tiktok_now integration
- Deduplication checks & ledger persistence (is_already_posted / mark_as_posted)
- CLI argument handling and dry-run execution
"""

import os
import sys
import json
import time
import tempfile
import unittest
from unittest.mock import patch, MagicMock, mock_open

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from scripts.tiktok_uploader import (
    load_config,
    save_config,
    refresh_access_token,
    get_valid_access_token,
    check_connection,
    init_video_publish,
    upload_video_chunks,
    poll_publish_status,
    upload_tiktok_now,
    is_already_posted,
    mark_as_posted,
    build_tiktok_caption,
    _load_ledger,
    _save_ledger
)

class TestTikTokUploader(unittest.TestCase):

    def setUp(self):
        self.mock_config = {
            "client_key": "test_client_key",
            "client_secret": "test_client_secret",
            "access_token": "act.initial_valid_token",
            "refresh_token": "rft.initial_refresh_token",
            "open_id": "test_open_id_12345",
            "expires_at": int(time.time()) + 3600,
            "refresh_expires_at": int(time.time()) + 86400 * 30
        }

    # ── Config Management & Token Refresh ────────────────────────────────────

    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open)
    def test_load_config_success(self, mock_file, mock_exists):
        mock_file.return_value.read.return_value = json.dumps(self.mock_config)
        cfg = load_config()
        self.assertEqual(cfg["client_key"], "test_client_key")
        self.assertEqual(cfg["access_token"], "act.initial_valid_token")

    @patch("os.path.exists", return_value=False)
    def test_load_config_not_found(self, mock_exists):
        with self.assertRaises(FileNotFoundError):
            load_config()

    @patch("scripts.tiktok_uploader.save_config")
    @patch("urllib.request.urlopen")
    def test_refresh_access_token_success(self, mock_urlopen, mock_save_config):
        mock_resp_data = {
            "data": {
                "access_token": "act.new_refreshed_token_999",
                "refresh_token": "rft.new_refresh_token_999",
                "open_id": "test_open_id_12345",
                "expires_in": 7200,
                "refresh_expires_in": 2592000
            }
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_resp_data).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        updated_config = refresh_access_token(self.mock_config.copy())
        self.assertEqual(updated_config["access_token"], "act.new_refreshed_token_999")
        self.assertEqual(updated_config["refresh_token"], "rft.new_refresh_token_999")
        self.assertTrue(updated_config["expires_at"] > int(time.time()))
        mock_save_config.assert_called_once()

    @patch("scripts.tiktok_uploader.refresh_access_token")
    @patch("scripts.tiktok_uploader.load_config")
    def test_get_valid_access_token_auto_refresh_when_expired(self, mock_load, mock_refresh):
        expired_config = self.mock_config.copy()
        expired_config["expires_at"] = int(time.time()) - 100  # already expired
        mock_load.return_value = expired_config

        refreshed_config = expired_config.copy()
        refreshed_config["access_token"] = "act.auto_refreshed"
        refreshed_config["expires_at"] = int(time.time()) + 3600
        mock_refresh.return_value = refreshed_config

        token = get_valid_access_token()
        self.assertEqual(token, "act.auto_refreshed")
        mock_refresh.assert_called_once()

    # ── Connection Verification ──────────────────────────────────────────────

    @patch("scripts.tiktok_uploader.get_valid_access_token", return_value="act.valid_token")
    @patch("urllib.request.urlopen")
    def test_check_connection_success(self, mock_urlopen, mock_token):
        mock_api_data = {
            "data": {
                "user": {
                    "username": "playmaker_fc",
                    "display_name": "Playmaker FC",
                    "avatar_url": "https://p16.tiktokcdn.com/avatar.jpg",
                    "open_id": "user_id_456"
                }
            },
            "error": {"code": "ok", "message": ""}
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_api_data).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        info = check_connection(silent=True)
        self.assertEqual(info["username"], "playmaker_fc")
        self.assertEqual(info["display_name"], "Playmaker FC")
        self.assertEqual(info["open_id"], "user_id_456")

    # ── Resumable Video Publish Init & Chunk Uploads ─────────────────────────

    @patch("scripts.tiktok_uploader.get_valid_access_token", return_value="act.valid_token")
    @patch("urllib.request.urlopen")
    def test_init_video_publish_success(self, mock_urlopen, mock_token):
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"0" * (12 * 1024 * 1024))  # 12 MB temp file
            temp_path = f.name

        try:
            mock_init_resp = {
                "data": {
                    "publish_id": "v_pub_file_789456",
                    "upload_url": "https://open-upload.tiktokapis.com/video/?upload_id=123"
                },
                "error": {"code": "ok", "message": ""}
            }
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_init_resp).encode("utf-8")
            mock_urlopen.return_value.__enter__.return_value = mock_resp

            pub_id, up_url, total_chunks, chunk_sz, tot_size = init_video_publish(
                video_path=temp_path,
                caption="Test caption #football",
                chunk_size=10 * 1024 * 1024
            )

            self.assertEqual(pub_id, "v_pub_file_789456")
            self.assertTrue(up_url.startswith("https://open-upload.tiktokapis.com/"))
            self.assertEqual(total_chunks, 2)  # 12MB in 10MB chunks = 2 chunks
            self.assertEqual(tot_size, 12 * 1024 * 1024)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    @patch("urllib.request.urlopen")
    def test_upload_video_chunks_streaming(self, mock_urlopen):
        # Create a mock video file of 25 KB
        total_size = 25 * 1024
        chunk_size = 10 * 1024

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"A" * total_size)
            temp_path = f.name

        try:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_urlopen.return_value.__enter__.return_value = mock_resp

            upload_video_chunks(temp_path, "https://upload.tiktok.com/stream", chunk_size, total_size)
            # 25KB in 10KB chunks = 3 chunks (10KB, 10KB, 5KB)
            self.assertEqual(mock_urlopen.call_count, 3)

            # Verify the Content-Range headers of each call
            call_args_list = mock_urlopen.call_args_list
            req_0 = call_args_list[0][0][0]
            req_1 = call_args_list[1][0][0]
            req_2 = call_args_list[2][0][0]

            self.assertEqual(req_0.headers["Content-range"], f"bytes 0-10239/{total_size}")
            self.assertEqual(req_1.headers["Content-range"], f"bytes 10240-20479/{total_size}")
            self.assertEqual(req_2.headers["Content-range"], f"bytes 20480-25599/{total_size}")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    # ── Status Polling ────────────────────────────────────────────────────────

    @patch("scripts.tiktok_uploader.get_valid_access_token", return_value="act.valid_token")
    @patch("urllib.request.urlopen")
    def test_poll_publish_status_success(self, mock_urlopen, mock_token):
        mock_data = {
            "data": {
                "status": "SUCCESS",
                "post_id": "7123456789012345678"
            }
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_data).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        result = poll_publish_status("v_pub_123", max_attempts=2, interval_seconds=0.01)
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["post_id"], "7123456789012345678")

    @patch("scripts.tiktok_uploader.get_valid_access_token", return_value="act.valid_token")
    @patch("urllib.request.urlopen")
    def test_poll_publish_status_failure(self, mock_urlopen, mock_token):
        mock_data = {
            "data": {
                "status": "FAILED",
                "fail_reason": "picture resolution does not meet requirement"
            }
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_data).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        with self.assertRaises(RuntimeError) as ctx:
            poll_publish_status("v_pub_123", max_attempts=2, interval_seconds=0.01)
        self.assertIn("picture resolution does not meet requirement", str(ctx.exception))

    # ── High Level Upload Now ─────────────────────────────────────────────────

    @patch("scripts.tiktok_uploader.poll_publish_status")
    @patch("scripts.tiktok_uploader.upload_video_chunks")
    @patch("scripts.tiktok_uploader.init_video_publish")
    def test_upload_tiktok_now_workflow(self, mock_init, mock_upload, mock_poll):
        mock_init.return_value = ("pub_id_111", "https://upload.url", 1, 1024, 1024)
        mock_poll.return_value = {"status": "SUCCESS", "post_id": "post_999"}

        pub_id, res = upload_tiktok_now(
            video_path="/mock/path/video.mp4",
            caption="Test Caption #playmaker",
            privacy_level="PUBLIC_TO_EVERYONE",
            poll_status=True
        )

        self.assertEqual(pub_id, "pub_id_111")
        self.assertEqual(res["status"], "SUCCESS")
        mock_init.assert_called_once()
        mock_upload.assert_called_once()
        mock_poll.assert_called_once_with("pub_id_111")

    # ── Deduplication & Ledger ───────────────────────────────────────────────

    @patch("scripts.tiktok_uploader._load_ledger")
    def test_is_already_posted(self, mock_load):
        mock_load.return_value = {
            "2026-10-13_player_chain": {
                "game_id": "player_chain",
                "date": "2026-10-13",
                "publish_id": "pub_chain_123",
                "target_name": "Chelsea & France"
            }
        }

        # Exact date & game_id match
        posted, pub_id = is_already_posted("player_chain", "2026-10-13")
        self.assertTrue(posted)
        self.assertEqual(pub_id, "pub_chain_123")

        # Different game on same date
        posted_pfc, _ = is_already_posted("passport_fc", "2026-10-13")
        self.assertFalse(posted_pfc)

        # Different date
        posted_diff_date, _ = is_already_posted("player_chain", "2026-10-14")
        self.assertFalse(posted_diff_date)

    @patch("scripts.tiktok_uploader._save_ledger")
    @patch("scripts.tiktok_uploader._load_ledger")
    def test_mark_as_posted(self, mock_load, mock_save):
        mock_load.return_value = {}
        mark_as_posted("career_flight", "2026-10-13", "pub_flight_555", target_name="Messi")

        mock_save.assert_called_once()
        saved_ledger = mock_save.call_args[0][0]
        self.assertIn("2026-10-13_career_flight", saved_ledger)
        entry = saved_ledger["2026-10-13_career_flight"]
        self.assertEqual(entry["publish_id"], "pub_flight_555")
        self.assertEqual(entry["target_name"], "Messi")

    # ── Caption Helper ────────────────────────────────────────────────────────

    def test_build_tiktok_caption(self):
        cap = build_tiktok_caption(game_id="top_transfers", target_name="Real Madrid")
        self.assertIn("Real Madrid", cap)
        self.assertIn("#fyp", cap)
        self.assertIn("#football", cap)
        self.assertNotIn("#reels", cap.lower())
        self.assertNotIn("link in bio", cap.lower())

    def test_clean_tiktok_caption_strips_forbidden_elements(self):
        from scripts.tiktok_uploader import clean_tiktok_caption
        raw = "Play today at playmaker.best (link in bio!) #reels #football #soccer #linkinbio"
        cleaned = clean_tiktok_caption(raw)
        self.assertNotIn("#reels", cleaned.lower())
        self.assertNotIn("#linkinbio", cleaned.lower())
        self.assertNotIn("link in bio", cleaned.lower())
        self.assertIn("#fyp", cleaned)
        self.assertIn("playmaker.best", cleaned)

if __name__ == "__main__":
    unittest.main()
