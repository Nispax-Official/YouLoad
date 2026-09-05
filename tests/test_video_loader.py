import unittest

from core.video_loader import _sanitize_text


class VideoLoaderSanitizationTests(unittest.TestCase):
    def test_strips_zero_width_space_from_titles(self):
        self.assertEqual(_sanitize_text("\u200bDrDonut\u200b"), "DrDonut")
        self.assertEqual(_sanitize_text("  Hello world  "), "Hello world")

    def test_blank_values_return_none(self):
        self.assertIsNone(_sanitize_text("\u200b \n\t"))


if __name__ == "__main__":
    unittest.main()
