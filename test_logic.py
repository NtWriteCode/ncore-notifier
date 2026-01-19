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
        
        # Reset config for testing
        main.CONFIG.update({
            "TYPES": {"hd_hun", "hdser"},
            "TG_TOKEN": "test_token",
            "TG_CHAT": "test_chat",
            "SILENT_START": True,
            "ONLY_RECENT": True,
            "LINK_TYPE": "both"
        })

    def tearDown(self):
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

    @patch('main.get_client')
    @patch('main.send_tg')
    def test_silent_first_run(self, mock_notify, mock_client_factory):
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client
        main.CONFIG["SILENT_START"] = True

        mock_client.get_recommended.return_value = [
            self.create_mock_torrent(1, "Movie 1", "HD_HUN"),
            self.create_mock_torrent(2, "Series 1", "HDSER")
        ]
        
        main.run_tracker()
        self.assertEqual(mock_notify.call_count, 0)
        
        with open(main.SEEN_FILE, 'r') as f:
            seen = json.load(f)
            self.assertIn("1", seen)
            self.assertIn("2", seen)

        mock_client.get_recommended.return_value.append(
            self.create_mock_torrent(3, "Movie 2", "HD_HUN")
        )
        
        main.run_tracker()
        self.assertEqual(mock_notify.call_count, 1)

    @patch('main.get_client')
    @patch('main.send_tg')
    def test_year_filtering(self, mock_notify, mock_client_factory):
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client
        with open(main.SEEN_FILE, 'w') as f:
            json.dump([], f)
        
        cur_year = datetime.datetime.now().year
        mock_client.get_recommended.return_value = [
            self.create_mock_torrent(1, "New", "HD_HUN", datetime.datetime(cur_year, 1, 1)),
            self.create_mock_torrent(2, "Old", "HD_HUN", datetime.datetime(cur_year - 5, 1, 1))
        ]
        
        main.CONFIG["ONLY_RECENT"] = True
        main.run_tracker()
        self.assertEqual(mock_notify.call_count, 1)
        self.assertIn("New", mock_notify.call_args[0][0])

    @patch('main.get_client')
    @patch('main.send_tg')
    def test_category_filtering(self, mock_notify, mock_client_factory):
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client
        with open(main.SEEN_FILE, 'w') as f:
            json.dump([], f)
            
        main.CONFIG["TYPES"] = {"hd_hun"}
        mock_client.get_recommended.return_value = [
            self.create_mock_torrent(1, "Matched", "HD_HUN"),
            self.create_mock_torrent(2, "Unmatched", "GAME_ISO")
        ]
        
        main.run_tracker()
        self.assertEqual(mock_notify.call_count, 1)
        self.assertIn("Matched", mock_notify.call_args[0][0])

    @patch('main.get_client')
    @patch('main.send_tg')
    def test_link_configuration(self, mock_notify, mock_client_factory):
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client
        with open(main.SEEN_FILE, 'w') as f:
            json.dump([], f)

        mock_client.get_recommended.return_value = [self.create_mock_torrent(1, "Test", "HD_HUN")]

        # Test 'url' only
        main.CONFIG["LINK_TYPE"] = "url"
        main.run_tracker()
        self.assertIn("🔗 Details", mock_notify.call_args[0][0])
        self.assertNotIn("⬇️ Download", mock_notify.call_args[0][0])

        # Test 'download' only
        with open(main.SEEN_FILE, 'w') as f:
            json.dump([], f)
        mock_notify.reset_mock()
        main.CONFIG["LINK_TYPE"] = "download"
        main.run_tracker()
        self.assertNotIn("🔗 Details", mock_notify.call_args[0][0])
        self.assertIn("⬇️ Download", mock_notify.call_args[0][0])

if __name__ == '__main__':
    unittest.main()
