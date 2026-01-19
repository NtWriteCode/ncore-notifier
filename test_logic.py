import unittest
from unittest.mock import MagicMock, patch
import json
import os
import sys
import datetime
from enum import Enum

# Add the directory to path so we can import main
sys.path.append('/home/roland/Repos/ncore-tracker')

import main

class MockSearchParamType(Enum):
    HD_HUN = "hd_hun"
    HDSER = "hdser"
    GAME_ISO = "game_iso"

class TestTracker(unittest.TestCase):
    def setUp(self):
        # Setup temp data directory
        self.test_dir = "/tmp/ncore_test_data"
        os.makedirs(self.test_dir, exist_ok=True)
        main.DATA_DIR = self.test_dir
        main.SEEN_FILE = os.path.join(self.test_dir, "seen.json")
        main.COOKIE_FILE = os.path.join(self.test_dir, "cookies.json")
        
        # Reset environment/config to defaults for testing
        main.NCORE_TYPES_STR = "HD_HUN,HDSER"
        main.TELEGRAM_TOKEN = "test_token"
        main.TELEGRAM_CHAT_ID = "test_chat"
        main.SILENT_FIRST_RUN = True
        main.ONLY_RECENT_YEARS = True
        main.NOTIFICATION_LINK_TYPE = "both"

    def tearDown(self):
        # Cleanup
        if os.path.exists(self.test_dir):
            import shutil
            shutil.rmtree(self.test_dir)

    def create_mock_torrent(self, t_id, title, t_type, date=None):
        if date is None:
            date = datetime.datetime.now()
        return {
            'id': t_id,
            'title': title,
            'type': MockSearchParamType[t_type],
            'size': '10GB',
            'date': date,
            'url': f'https://ncore.pro/details/{t_id}',
            'download': f'https://ncore.pro/download/{t_id}'
        }

    @patch('main.get_ncore_client')
    @patch('main.send_telegram_notification')
    def test_silent_first_run(self, mock_notify, mock_client_factory):
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client
        
        main.SILENT_FIRST_RUN = True
        # Initial run with 2 torrents
        mock_client.get_recommended.return_value = [
            self.create_mock_torrent(1, "Movie 1", "HD_HUN"),
            self.create_mock_torrent(2, "Series 1", "HDSER")
        ]
        
        main.check_for_new_torrents()
        
        # Should NOT notify on first run if silent
        self.assertEqual(mock_notify.call_count, 0)
        
        # Should have saved them to seen.json
        with open(main.SEEN_FILE, 'r') as f:
            seen = json.load(f)
            self.assertIn("1", seen)
            self.assertIn("2", seen)

        # Second run with a brand new torrent
        mock_client.get_recommended.return_value.append(
            self.create_mock_torrent(3, "Movie 2", "HD_HUN")
        )
        
        main.check_for_new_torrents()
        # Should notify only for the 3rd one
        self.assertEqual(mock_notify.call_count, 1)

    @patch('main.get_ncore_client')
    @patch('main.send_telegram_notification')
    def test_year_filtering(self, mock_notify, mock_client_factory):
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client
        
        # Set database exists to avoid silent first run
        os.makedirs(self.test_dir, exist_ok=True)
        with open(main.SEEN_FILE, 'w') as f:
            json.dump([], f)
        
        current_year = datetime.datetime.now().year
        
        mock_client.get_recommended.return_value = [
            self.create_mock_torrent(1, "New Movie", "HD_HUN", datetime.datetime(current_year, 1, 1)),
            self.create_mock_torrent(2, "Old Movie", "HD_HUN", datetime.datetime(current_year - 5, 1, 1))
        ]
        
        main.ONLY_RECENT_YEARS = True
        main.check_for_new_torrents()
        
        # Only notify for the new one
        self.assertEqual(mock_notify.call_count, 1)
        self.assertIn("New Movie", mock_notify.call_args[0][0])

    @patch('main.get_ncore_client')
    @patch('main.send_telegram_notification')
    def test_category_filtering(self, mock_notify, mock_client_factory):
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client
        
        # Set database exists
        with open(main.SEEN_FILE, 'w') as f:
            json.dump([], f)
            
        main.NCORE_TYPES_STR = "HD_HUN" # Only interested in HD Movies
        
        mock_client.get_recommended.return_value = [
            self.create_mock_torrent(1, "Matched", "HD_HUN"),
            self.create_mock_torrent(2, "Unmatched", "GAME_ISO")
        ]
        
        main.check_for_new_torrents()
        
        # Only notify for the matched one
        self.assertEqual(mock_notify.call_count, 1)
        self.assertIn("Matched", mock_notify.call_args[0][0])

    @patch('main.get_ncore_client')
    @patch('main.send_telegram_notification')
    def test_link_configuration(self, mock_notify, mock_client_factory):
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client
        with open(main.SEEN_FILE, 'w') as f:
            json.dump([], f)

        torrent = self.create_mock_torrent(1, "Test", "HD_HUN")
        mock_client.get_recommended.return_value = [torrent]

        # Test 'url' only
        main.NOTIFICATION_LINK_TYPE = "url"
        main.check_for_new_torrents()
        msg = mock_notify.call_args[0][0]
        self.assertIn("🔗 Details", msg)
        self.assertNotIn("⬇️ Download", msg)

        # Clear seen for next subtest
        with open(main.SEEN_FILE, 'w') as f:
            json.dump([], f)
        mock_notify.reset_mock()

        # Test 'download' only
        main.NOTIFICATION_LINK_TYPE = "download"
        main.check_for_new_torrents()
        msg = mock_notify.call_args[0][0]
        self.assertNotIn("🔗 Details", msg)
        self.assertIn("⬇️ Download", msg)

if __name__ == '__main__':
    unittest.main()
