import unittest
from unittest.mock import MagicMock, patch, mock_open
import sys
import os

# Mock nap module before importing s3_probe
mock_nap = MagicMock()
mock_nap.core = MagicMock()
mock_nap.OK = 0
mock_nap.WARNING = 1
mock_nap.CRITICAL = 2
sys.modules["nap"] = mock_nap
sys.modules["nap.core"] = mock_nap.core


# Setup app.metric decorator to be a pass-through
def mock_metric_decorator(*args, **kwargs):
    def wrapper(func):
        return func

    return wrapper


# When nap.core.Plugin() is called, it returns a mock (app).
# We want app.metric to be our pass-through decorator.
mock_app_instance = MagicMock()
mock_nap.core.Plugin.return_value = mock_app_instance
mock_app_instance.metric.side_effect = mock_metric_decorator

import nap

# Add plugins directory to path so we can import s3_probe
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../plugins")))

import s3_probe


class TestS3Probe(unittest.TestCase):
    def setUp(self):
        self.mock_args = MagicMock()
        self.mock_args.endpoint = "http://localhost:8080"
        self.mock_args.s3_access_key = "access"
        self.mock_args.s3_secret_key = "secret"
        self.mock_args.s3_bucket = "bucket"
        self.mock_args.read_only = False

        self.mock_io = MagicMock()
        self.mock_io.status = nap.OK

        # Reset global state if necessary (though mostly handled by mocks)
        s3_probe._fileDictionary = {}

    @patch("s3_probe.boto3")
    def test_ls_bucket_success(self, mock_boto3):
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        s3_probe.metricLsBucket(self.mock_args, self.mock_io)

        self.assertEqual(self.mock_io.status, nap.OK)
        self.assertIn("Buckets successfully listed", self.mock_io.summary)

    @patch("s3_probe.boto3")
    def test_ls_bucket_failure(self, mock_boto3):
        mock_client = MagicMock()
        mock_client.list_buckets.side_effect = Exception("S3 Error")
        mock_boto3.client.return_value = mock_client

        s3_probe.metricLsBucket(self.mock_args, self.mock_io)

        self.mock_io.set_status.assert_called_with(nap.CRITICAL, unittest.mock.ANY)

    @patch("s3_probe.boto3")
    @patch("s3_probe.open", new_callable=mock_open)
    @patch("s3_probe.app.metric_results")
    def test_put_success(self, mock_results, mock_file, mock_boto3):
        # Mock previous result (LsBucket) as OK
        mock_results.return_value = [("LsBucket", nap.OK)]

        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        s3_probe.app.s3_target = mock_client  # Manually set since parse_args might not run in this unit test isolation if we don't call it
        s3_probe.app.s3_bucket_name = "bucket"

        # We need to ensure parse_args is called or simulate its effect.
        # metricPut doesn't call parse_args, it assumes it was done or s3_target is set.
        # In the real script, metricLsBucket runs first.

        s3_probe.metricPut(self.mock_args, self.mock_io)

        self.assertEqual(self.mock_io.status, nap.OK)
        self.assertIn("File was copied to the S3 endpoint", self.mock_io.summary)
        self.assertIn(self.mock_args.endpoint, s3_probe._fileDictionary)

    @patch("s3_probe.boto3")
    @patch("s3_probe.filecmp.cmp")
    @patch("s3_probe.app.metric_results")
    def test_get_success(self, mock_results, mock_cmp, mock_boto3):
        # Mock previous results (LsBucket, Put) as OK
        mock_results.return_value = [("LsBucket", nap.OK), ("Put", nap.OK)]

        # Setup file dictionary
        s3_probe._fileDictionary = {self.mock_args.endpoint: {"fn": "testfile"}}

        mock_resource = MagicMock()
        mock_boto3.resource.return_value = mock_resource
        s3_probe.app.s3_resource = mock_resource
        s3_probe.app.s3_bucket_name = "bucket"

        # Mock file comparison to return True (files match)
        mock_cmp.return_value = True

        s3_probe.metricGet(self.mock_args, self.mock_io)

        self.assertEqual(self.mock_io.status, nap.OK)
        self.assertIn("File was copied from the S3 Storage", self.mock_io.summary)

    @patch("s3_probe.boto3")
    @patch("s3_probe.filecmp.cmp")
    @patch("s3_probe.app.metric_results")
    def test_get_failure_content_mismatch(self, mock_results, mock_cmp, mock_boto3):
        # Mock previous results (LsBucket, Put) as OK
        mock_results.return_value = [("LsBucket", nap.OK), ("Put", nap.OK)]

        # Setup file dictionary
        s3_probe._fileDictionary = {self.mock_args.endpoint: {"fn": "testfile"}}

        mock_resource = MagicMock()
        mock_boto3.resource.return_value = mock_resource
        s3_probe.app.s3_resource = mock_resource
        s3_probe.app.s3_bucket_name = "bucket"

        # Mock file comparison to return False (files do NOT match)
        mock_cmp.return_value = False

        s3_probe.metricGet(self.mock_args, self.mock_io)

        self.mock_io.set_status.assert_called_with(
            nap.CRITICAL, "Downloaded file content does not match uploaded file"
        )

    @patch("s3_probe.boto3")
    @patch("s3_probe.app.metric_results")
    def test_del_success(self, mock_results, mock_boto3):
        # Mock previous results (LsBucket, Put, Get) as OK
        mock_results.return_value = [
            ("LsBucket", nap.OK),
            ("Put", nap.OK),
            ("Get", nap.OK),
        ]

        # Setup file dictionary
        s3_probe._fileDictionary = {self.mock_args.endpoint: {"fn": "testfile"}}

        mock_resource = MagicMock()
        mock_boto3.resource.return_value = mock_resource
        s3_probe.app.s3_resource = mock_resource
        s3_probe.app.s3_bucket_name = "bucket"

        s3_probe.metricDel(self.mock_args, self.mock_io)

        self.assertEqual(self.mock_io.status, nap.OK)
        self.assertIn("File was deleted", self.mock_io.summary)


if __name__ == "__main__":
    unittest.main()
