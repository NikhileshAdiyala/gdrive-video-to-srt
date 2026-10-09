import unittest
from utils import extract_gdrive_file_id, format_timestamp_srt, generate_srt_content

class TestGdriveToSrt(unittest.TestCase):
    def test_extract_file_id(self):
        urls = [
            ("https://drive.google.com/file/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs/view?usp=sharing", "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"),
            ("https://drive.google.com/open?id=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs", "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"),
            ("https://drive.google.com/uc?id=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs", "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"),
            ("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs", "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs")
        ]
        for url, expected in urls:
            self.assertEqual(extract_gdrive_file_id(url), expected)

    def test_timestamp_formatting(self):
        self.assertEqual(format_timestamp_srt(0.0), "00:00:00,000")
        self.assertEqual(format_timestamp_srt(65.42), "00:01:05,420")
        self.assertEqual(format_timestamp_srt(3661.055), "01:01:01,055")

    def test_srt_generation(self):
        segments = [
            {"start": 1.25, "end": 4.5, "text": "Hello, welcome to CRAMSN."},
            {"start": 5.0, "end": 8.2, "text": "Advancing molecules, enabling medicines."}
        ]
        srt = generate_srt_content(segments)
        expected = (
            "1\n00:00:01,250 --> 00:00:04,500\nHello, welcome to CRAMSN.\n\n"
            "2\n00:00:05,000 --> 00:00:08,200\nAdvancing molecules, enabling medicines.\n"
        )
        self.assertEqual(srt.strip(), expected.strip())

if __name__ == '__main__':
    unittest.main()
