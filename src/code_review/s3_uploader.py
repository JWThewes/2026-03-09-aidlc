import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError


class S3Uploader:
    DEFAULT_REGION = "us-east-1"

    def __init__(
        self,
        bucket: Optional[str] = None,
        region: Optional[str] = None,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
    ):
        self.bucket = bucket or os.getenv("S3_BUCKET") or os.getenv("AWS_BUCKET")
        self.region = region or os.getenv("AWS_REGION") or self.DEFAULT_REGION
        
        self.access_key_id = access_key_id or os.getenv("AWS_ACCESS_KEY_ID")
        self.secret_access_key = secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY")
        
        self._client = None

    @property
    def client(self):
        if self._client is None:
            client_kwargs = {"region_name": self.region}
            if self.access_key_id and self.secret_access_key:
                client_kwargs["aws_access_key_id"] = self.access_key_id
                client_kwargs["aws_secret_access_key"] = self.secret_access_key
            self._client = boto3.client("s3", **client_kwargs)
        return self._client

    def _build_key(self, commit_hash: str, filename: str = "findings.json") -> str:
        timestamp = datetime.utcnow().strftime("%Y-%m-%d")
        safe_commit = commit_hash[:12] if len(commit_hash) > 12 else commit_hash
        return f"analysis/{safe_commit}/{timestamp}/{filename}"

    def upload_json(
        self,
        data: Dict[str, Any],
        commit_hash: str,
        bucket: Optional[str] = None,
        filename: str = "findings.json",
    ) -> str:
        target_bucket = bucket or self.bucket
        if not target_bucket:
            raise ValueError("S3 bucket not specified. Set S3_BUCKET environment variable or pass bucket parameter.")

        key = self._build_key(commit_hash, filename)
        
        json_content = json.dumps(data, indent=2)
        
        try:
            self.client.put_object(
                Bucket=target_bucket,
                Key=key,
                Body=json_content.encode("utf-8"),
                ContentType="application/json",
            )
        except NoCredentialsError:
            raise EnvironmentError(
                "AWS credentials not found. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables."
            )
        except ClientError as e:
            raise RuntimeError(f"Failed to upload to S3: {e}")

        return f"s3://{target_bucket}/{key}"

    def upload_findings_report(
        self,
        report: Any,
        commit_hash: str,
        bucket: Optional[str] = None,
    ) -> str:
        if hasattr(report, "to_dict"):
            data = report.to_dict()
        elif isinstance(report, dict):
            data = report
        else:
            raise ValueError("report must be a FindingsReport instance or dict")

        return self.upload_json(data, commit_hash, bucket)

    def get_presigned_url(
        self,
        commit_hash: str,
        filename: str = "findings.json",
        expiration: int = 3600,
    ) -> str:
        if not self.bucket:
            raise ValueError("S3 bucket not specified. Set S3_BUCKET environment variable.")
        
        key = self._build_key(commit_hash, filename)
        
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expiration,
            )
        except ClientError as e:
            raise RuntimeError(f"Failed to generate presigned URL: {e}")
        
        return url

    def list_analysis_results(
        self,
        commit_hash: Optional[str] = None,
        bucket: Optional[str] = None,
    ) -> list:
        target_bucket = bucket or self.bucket
        if not target_bucket:
            raise ValueError("S3 bucket not specified.")

        prefix = "analysis/"
        if commit_hash:
            safe_commit = commit_hash[:12] if len(commit_hash) > 12 else commit_hash
            prefix = f"analysis/{safe_commit}/"

        try:
            response = self.client.list_objects_v2(
                Bucket=target_bucket,
                Prefix=prefix,
            )
            return [obj["Key"] for obj in response.get("Contents", [])]
        except ClientError as e:
            raise RuntimeError(f"Failed to list S3 objects: {e}")


def upload_findings(
    findings_json: Dict[str, Any],
    commit_hash: str,
    bucket: Optional[str] = None,
) -> str:
    uploader = S3Uploader(bucket=bucket)
    return uploader.upload_json(findings_json, commit_hash)
