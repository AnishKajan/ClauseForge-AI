"""
Virus scanning service using ClamAV
"""

import os
import tempfile
import logging
import subprocess
import asyncio
import json
from typing import Optional, Dict, Any
from pathlib import Path
import boto3
from botocore.exceptions import ClientError

from core.config import settings

logger = logging.getLogger(__name__)


class VirusScanResult:
    """Result of virus scan operation"""
    
    def __init__(self, is_clean: bool, threat_name: Optional[str] = None, details: Optional[str] = None):
        self.is_clean = is_clean
        self.threat_name = threat_name
        self.details = details
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_clean": self.is_clean,
            "threat_name": self.threat_name,
            "details": self.details
        }


class ClamAVScanner:
    """Local ClamAV scanner for development and testing"""
    
    def __init__(self):
        self.clamav_available = self._check_clamav_availability()
    
    def _check_clamav_availability(self) -> bool:
        """Check if ClamAV is available on the system"""
        try:
            result = subprocess.run(
                ["clamscan", "--version"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.warning("ClamAV not available on system")
            return False
    
    async def scan_file(self, file_path: str) -> VirusScanResult:
        """Scan a file using ClamAV"""
        if not self.clamav_available:
            logger.warning("ClamAV not available, skipping virus scan")
            return VirusScanResult(is_clean=True, details="ClamAV not available")
        
        try:
            # Run clamscan in a subprocess
            process = await asyncio.create_subprocess_exec(
                "clamscan",
                "--no-summary",
                "--infected",
                file_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                # File is clean
                return VirusScanResult(is_clean=True)
            elif process.returncode == 1:
                # Virus found
                output = stdout.decode() if stdout else ""
                threat_name = self._extract_threat_name(output)
                return VirusScanResult(
                    is_clean=False, 
                    threat_name=threat_name,
                    details=output.strip()
                )
            else:
                # Error occurred
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"ClamAV scan error: {error_msg}")
                return VirusScanResult(
                    is_clean=True,  # Fail open
                    details=f"Scan error: {error_msg}"
                )
                
        except Exception as e:
            logger.error(f"Exception during virus scan: {str(e)}")
            return VirusScanResult(is_clean=True, details=f"Scan exception: {str(e)}")
    
    def _extract_threat_name(self, output: str) -> Optional[str]:
        """Extract threat name from ClamAV output"""
        lines = output.strip().split('\n')
        for line in lines:
            if 'FOUND' in line:
                # Format: /path/to/file: ThreatName FOUND
                parts = line.split(': ')
                if len(parts) >= 2:
                    threat_part = parts[1].replace(' FOUND', '')
                    return threat_part
        return None


class LambdaVirusScanner:
    """AWS Lambda-based virus scanner for production"""
    
    def __init__(self):
        self.lambda_client = boto3.client(
            'lambda',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        self.function_name = settings.VIRUS_SCANNER_LAMBDA_FUNCTION
    
    async def scan_s3_object(self, bucket: str, key: str) -> VirusScanResult:
        """Scan an S3 object using Lambda function"""
        try:
            payload = {
                "bucket": bucket,
                "key": key
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if response['StatusCode'] == 200:
                return VirusScanResult(
                    is_clean=result.get('is_clean', True),
                    threat_name=result.get('threat_name'),
                    details=result.get('details')
                )
            else:
                logger.error(f"Lambda virus scan failed: {result}")
                return VirusScanResult(is_clean=True, details="Lambda scan failed")
                
        except Exception as e:
            logger.error(f"Exception during Lambda virus scan: {str(e)}")
            return VirusScanResult(is_clean=True, details=f"Lambda scan exception: {str(e)}")


class VirusScannerService:
    """Main virus scanner service that chooses appropriate scanner"""
    
    def __init__(self):
        if settings.ENVIRONMENT == "production" and hasattr(settings, 'VIRUS_SCANNER_LAMBDA_FUNCTION'):
            self.scanner = LambdaVirusScanner()
            self.scanner_type = "lambda"
        else:
            self.scanner = ClamAVScanner()
            self.scanner_type = "clamav"
        
        logger.info(f"Initialized virus scanner: {self.scanner_type}")
    
    async def scan_uploaded_file(self, file_content: bytes, filename: str) -> VirusScanResult:
        """Scan uploaded file content"""
        if self.scanner_type == "lambda":
            # For Lambda scanner, we need to upload to S3 first
            return await self._scan_via_s3(file_content, filename)
        else:
            # For ClamAV, scan local temporary file
            return await self._scan_local_file(file_content, filename)
    
    async def scan_s3_object(self, bucket: str, key: str) -> VirusScanResult:
        """Scan an existing S3 object"""
        if self.scanner_type == "lambda":
            return await self.scanner.scan_s3_object(bucket, key)
        else:
            # Download from S3 and scan locally
            return await self._download_and_scan(bucket, key)
    
    async def _scan_local_file(self, file_content: bytes, filename: str) -> VirusScanResult:
        """Scan file content using local ClamAV"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as temp_file:
            try:
                temp_file.write(file_content)
                temp_file.flush()
                
                result = await self.scanner.scan_file(temp_file.name)
                return result
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_file.name)
                except OSError:
                    pass
    
    async def _scan_via_s3(self, file_content: bytes, filename: str) -> VirusScanResult:
        """Upload to S3 and scan via Lambda"""
        s3_client = boto3.client(
            's3',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        
        # Upload to temporary S3 location
        temp_key = f"virus-scan-temp/{filename}"
        
        try:
            s3_client.put_object(
                Bucket=settings.S3_BUCKET_NAME,
                Key=temp_key,
                Body=file_content
            )
            
            # Scan the uploaded file
            result = await self.scanner.scan_s3_object(settings.S3_BUCKET_NAME, temp_key)
            
            return result
            
        except Exception as e:
            logger.error(f"Error uploading file for virus scan: {str(e)}")
            return VirusScanResult(is_clean=True, details=f"Upload error: {str(e)}")
        
        finally:
            # Clean up temporary S3 object
            try:
                s3_client.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=temp_key)
            except Exception:
                pass
    
    async def _download_and_scan(self, bucket: str, key: str) -> VirusScanResult:
        """Download S3 object and scan locally"""
        s3_client = boto3.client(
            's3',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            try:
                s3_client.download_fileobj(bucket, key, temp_file)
                temp_file.flush()
                
                result = await self.scanner.scan_file(temp_file.name)
                return result
                
            except Exception as e:
                logger.error(f"Error downloading file for virus scan: {str(e)}")
                return VirusScanResult(is_clean=True, details=f"Download error: {str(e)}")
            
            finally:
                try:
                    os.unlink(temp_file.name)
                except OSError:
                    pass


# Global virus scanner instance
virus_scanner = VirusScannerService()


async def scan_file_for_viruses(file_content: bytes, filename: str) -> VirusScanResult:
    """Convenience function to scan file content for viruses"""
    return await virus_scanner.scan_uploaded_file(file_content, filename)


async def scan_s3_file_for_viruses(bucket: str, key: str) -> VirusScanResult:
    """Convenience function to scan S3 object for viruses"""
    return await virus_scanner.scan_s3_object(bucket, key)