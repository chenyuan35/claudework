"""配图下载与文件校验测试。"""
import base64
import io
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import scripts.generate_images as images


class TestGenerateImages(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tempdir, ignore_errors=True)

    @staticmethod
    def valid_png():
        buf = io.BytesIO()
        Image.new("RGB", (512, 512), "white").save(buf, format="PNG")
        return buf.getvalue()

    @patch("scripts.generate_images.requests.get")
    @patch("scripts.generate_images.requests.post")
    def test_agens_rejects_html_download(self, post, get):
        post.return_value.json.return_value = {"data": [{"url": "https://example/image"}]}
        response = Mock()
        response.headers = {"Content-Type": "text/html"}
        response.content = b"<html>not image</html>"
        response.raise_for_status.return_value = None
        get.return_value = response
        result = images.call_agens("prompt", self.tempdir, 1)
        self.assertFalse(result["ok"])
        self.assertIn("invalid_content_type", result["error"])

    @patch("scripts.generate_images.requests.post")
    def test_sese_rejects_non_image_base64(self, post):
        post.return_value.json.return_value = {
            "images": [{"ok": True, "b64": base64.b64encode(b"not image").decode()}]
        }
        result = images.call_sese("prompt", self.tempdir, 1)
        self.assertFalse(result["ok"])
        self.assertIn("invalid_image", result["error"])

    @patch("scripts.generate_images.requests.post")
    def test_sese_accepts_valid_image(self, post):
        post.return_value.json.return_value = {
            "images": [{"ok": True, "b64": base64.b64encode(self.valid_png()).decode()}]
        }
        result = images.call_sese("prompt", self.tempdir, 1)
        self.assertTrue(result["ok"])
        self.assertTrue(os.path.isfile(result["path"]))


if __name__ == "__main__":
    unittest.main()
