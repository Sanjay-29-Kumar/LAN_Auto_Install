"""
Virus scanning utility using VirusTotal API
"""
import os
import hashlib
import requests
import time
from PyQt5.QtCore import QObject, pyqtSignal

class VirusScanner(QObject):
    # Signals for UI updates
    scan_started = pyqtSignal(str)  # Emits filename when scan starts
    scan_progress = pyqtSignal(str, int, str)  # Emits filename, progress %, status
    scan_complete = pyqtSignal(str, bool, str)  # Emits filename, is_safe, result_details

    def __init__(self, api_key="a828b8fdc2b8115bf8b3147dccfcffa28d0ff7aa5c07ea94f1b2ec1c474fc92c"):
        super().__init__()
        self.api_key = api_key
        self.headers = {
            'x-apikey': self.api_key
        }
        self.base_url = 'https://www.virustotal.com/vtapi/v3'
        self.scan_cache = {}  # Cache scan results

    def _calculate_file_hash(self, file_path):
        """Calculate SHA-256 hash of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _check_cached_result(self, file_hash):
        """Check if we have a cached scan result"""
        if file_hash in self.scan_cache:
            cache_time, result = self.scan_cache[file_hash]
            if time.time() - cache_time < 3600:  # Cache valid for 1 hour
                return result
        return None

    def _upload_file(self, file_path):
        """Upload file to VirusTotal"""
        upload_url = f"{self.base_url}/files"
        with open(file_path, 'rb') as file:
            files = {'file': file}
            response = requests.post(upload_url, headers=self.headers, files=files)
            return response.json()

    def _get_scan_results(self, file_hash):
        """Get scan results from VirusTotal"""
        url = f"{self.base_url}/files/{file_hash}"
        response = requests.get(url, headers=self.headers)
        return response.json()

    def scan_file(self, file_path):
        """
        Scan a file using VirusTotal API
        Returns: (is_safe, details)
        """
        if not os.path.exists(file_path):
            return False, "File not found"

        file_name = os.path.basename(file_path)
        self.scan_started.emit(file_name)

        # Calculate file hash
        file_hash = self._calculate_file_hash(file_path)
        
        # Check cache first
        cached_result = self._check_cached_result(file_hash)
        if cached_result:
            self.scan_complete.emit(file_name, cached_result[0], cached_result[1])
            return cached_result

        try:
            # First check if the file has been scanned before
            self.scan_progress.emit(file_name, 25, "Checking file status...")
            try:
                result = self._get_scan_results(file_hash)
                if 'data' in result:
                    analysis = result['data']['attributes']['last_analysis_stats']
                else:
                    # File needs to be uploaded
                    self.scan_progress.emit(file_name, 50, "Uploading file for scanning...")
                    upload_result = self._upload_file(file_path)
                    time.sleep(3)  # Wait for processing
                    result = self._get_scan_results(file_hash)
                    analysis = result['data']['attributes']['last_analysis_stats']

            except Exception as e:
                return False, f"Scan error: {str(e)}"

            # Check results
            self.scan_progress.emit(file_name, 90, "Analyzing results...")
            malicious = analysis.get('malicious', 0)
            suspicious = analysis.get('suspicious', 0)
            total = sum(analysis.values())

            is_safe = malicious == 0 and suspicious == 0
            details = f"Scan complete: {malicious} malicious, {suspicious} suspicious out of {total} scans"

            # Cache the result
            self.scan_cache[file_hash] = (time.time(), (is_safe, details))
            
            self.scan_complete.emit(file_name, is_safe, details)
            return is_safe, details

        except Exception as e:
            error_msg = f"Error scanning file: {str(e)}"
            self.scan_complete.emit(file_name, False, error_msg)
            return False, error_msg
