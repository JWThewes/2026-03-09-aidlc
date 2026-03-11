import json
import os
from unittest.mock import MagicMock, patch

import pytest

from src.code_review.s3_uploader import S3Uploader, upload_findings


class TestS3Uploader:
    def test_init_with_env_vars(self, monkeypatch):
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-key")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret")
        monkeypatch.setenv("AWS_REGION", "us-west-2")
        monkeypatch.setenv("S3_BUCKET", "test-bucket")

        uploader = S3Uploader()

        assert uploader.access_key_id == "test-key"
        assert uploader.secret_access_key == "test-secret"
        assert uploader.region == "us-west-2"
        assert uploader.bucket == "test-bucket"

    def test_init_with_params(self):
        uploader = S3Uploader(
            bucket="my-bucket",
            region="eu-west-1",
            access_key_id="key",
            secret_access_key="secret",
        )

        assert uploader.bucket == "my-bucket"
        assert uploader.region == "eu-west-1"
        assert uploader.access_key_id == "key"
        assert uploader.secret_access_key == "secret"

    def test_build_key_with_long_commit(self):
        uploader = S3Uploader(bucket="test-bucket")
        key = uploader._build_key("abc123def456789", "findings.json")

        assert key == "analysis/abc123def456/2026-03-11/findings.json"
        assert key.startswith("analysis/")
        assert "abc123def456" in key

    def test_build_key_with_short_commit(self):
        uploader = S3Uploader(bucket="test-bucket")
        key = uploader._build_key("abc", "report.json")

        assert key == "analysis/abc/2026-03-11/report.json"

    def test_upload_json_without_bucket_raises(self):
        uploader = S3Uploader()
        
        with pytest.raises(ValueError, match="S3 bucket not specified"):
            uploader.upload_json({}, "abc123")

    @patch("src.code_review.s3_uploader.boto3.client")
    def test_upload_json_success(self, mock_boto_client):
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client

        uploader = S3Uploader(bucket="test-bucket", region="us-east-1")
        result = uploader.upload_json({"test": "data"}, "abc123def456")

        mock_client.put_object.assert_called_once()
        call_kwargs = mock_client.put_object.call_args[1]
        assert call_kwargs["Bucket"] == "test-bucket"
        assert call_kwargs["ContentType"] == "application/json"
        assert "analysis/abc123def456" in call_kwargs["Key"]
        assert result == f"s3://test-bucket/{call_kwargs['Key']}"

    @patch("src.code_review.s3_uploader.boto3.client")
    def test_upload_json_no_credentials_raises(self, mock_boto_client):
        from botocore.exceptions import NoCredentialsError

        mock_client = MagicMock()
        mock_client.put_object.side_effect = NoCredentialsError()
        mock_boto_client.return_value = mock_client

        uploader = S3Uploader(bucket="test-bucket")

        with pytest.raises(EnvironmentError, match="AWS credentials not found"):
            uploader.upload_json({}, "abc123")

    @patch("src.code_review.s3_uploader.boto3.client")
    def test_upload_findings_report_with_to_dict(self, mock_boto_client):
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client

        uploader = S3Uploader(bucket="test-bucket")
        
        mock_report = MagicMock()
        mock_report.to_dict.return_value = {"findings": [], "metadata": {}}

        result = uploader.upload_findings_report(mock_report, "abc123")

        mock_report.to_dict.assert_called_once()
        mock_client.put_object.assert_called_once()

    def test_upload_findings_report_with_dict(self):
        uploader = S3Uploader(bucket="test-bucket")
        
        with patch.object(uploader, "upload_json") as mock_upload:
            mock_upload.return_value = "s3://test-bucket/test"
            
            result = uploader.upload_findings_report({"key": "value"}, "abc123")
            
            mock_upload.assert_called_once()
            assert result == "s3://test-bucket/test"

    def test_upload_findings_report_invalid_input(self):
        uploader = S3Uploader(bucket="test-bucket")
        
        with pytest.raises(ValueError, match="must be a FindingsReport"):
            uploader.upload_findings_report("invalid", "abc123")

    @patch("src.code_review.s3_uploader.boto3.client")
    def test_get_presigned_url(self, mock_boto_client):
        mock_client = MagicMock()
        mock_client.generate_presigned_url.return_value = "https://presigned.url"
        mock_boto_client.return_value = mock_client

        uploader = S3Uploader(bucket="test-bucket")
        url = uploader.get_presigned_url("abc123def456")

        mock_client.generate_presigned_url.assert_called_once()
        assert url == "https://presigned.url"

    def test_get_presigned_url_no_bucket(self):
        uploader = S3Uploader()
        
        with pytest.raises(ValueError, match="S3 bucket not specified"):
            uploader.get_presigned_url("abc123")

    @patch("src.code_review.s3_uploader.boto3.client")
    def test_list_analysis_results(self, mock_boto_client):
        mock_client = MagicMock()
        mock_client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "analysis/abc123/2026-03-11/findings.json"},
                {"Key": "analysis/abc123/2026-03-11/summary.json"},
            ]
        }
        mock_boto_client.return_value = mock_client

        uploader = S3Uploader(bucket="test-bucket")
        results = uploader.list_analysis_results("abc123")

        assert len(results) == 2
        assert "analysis/abc123" in results[0]

    @patch("src.code_review.s3_uploader.boto3.client")
    def test_list_analysis_results_all(self, mock_boto_client):
        mock_client = MagicMock()
        mock_client.list_objects_v2.return_value = {"Contents": []}
        mock_boto_client.return_value = mock_client

        uploader = S3Uploader(bucket="test-bucket")
        results = uploader.list_analysis_results()

        mock_client.list_objects_v2.assert_called_once()
        call_kwargs = mock_client.list_objects_v2.call_args[1]
        assert call_kwargs["Prefix"] == "analysis/"


class TestUploadFindings:
    @patch("src.code_review.s3_uploader.S3Uploader")
    def test_upload_findings_function(self, mock_uploader_class):
        mock_instance = MagicMock()
        mock_instance.upload_json.return_value = "s3://bucket/key"
        mock_uploader_class.return_value = mock_instance

        result = upload_findings({"test": "data"}, "abc123", "my-bucket")

        mock_uploader_class.assert_called_once_with(bucket="my-bucket")
        mock_instance.upload_json.assert_called_once()
        assert result == "s3://bucket/key"
