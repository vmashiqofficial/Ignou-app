import unittest

from app import app


class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_homepage_has_responsive_upload_interface(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('upload-form', html)
        self.assertIn('status-message', html)
        self.assertIn('loading-state', html)


if __name__ == '__main__':
    unittest.main()
