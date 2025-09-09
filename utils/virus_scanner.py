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
            'apikey': self.api_key
        }
        self.base_url = 'https://www.virustotal.com/vtapi/v2'
        self.scan_cache = {}  # Cache scan results
        self.error_count = 0
        self.max_errors = 3

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

    def scan_file(self, file_path):
        """
        Safely scan a file and handle all potential errors
        """
        try:
            # Basic file checks
            if not os.path.exists(file_path):
                self.scan_progress.emit(os.path.basename(file_path), 0, "File not found")
                return False, "File not found"
                
            if not os.path.isfile(file_path):
                self.scan_progress.emit(os.path.basename(file_path), 0, "Not a valid file")
                return False, "Not a valid file"
                
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            # Size check - VirusTotal has a 32MB limit for the free API
            if file_size > 32 * 1024 * 1024:
                self.scan_progress.emit(file_name, 100, "File too large for scanning")
                return True, "File too large for scanning (>32MB) - Skipped"
                
            # Calculate file hash
            try:
                self.scan_progress.emit(file_name, 10, "Calculating file hash...")
                file_hash = self._calculate_file_hash(file_path)
            except Exception as e:
                self.scan_progress.emit(file_name, 0, f"Hash calculation error: {e}")
                return False, f"Hash calculation failed: {str(e)}"
                
            # Check cache
            self.scan_progress.emit(file_name, 20, "Checking cache...")
            cached_result = self._check_cached_result(file_hash)
            if cached_result:
                self.scan_progress.emit(file_name, 100, "Retrieved from cache")
                return cached_result
                
            # Check if file has been scanned before
            self.scan_progress.emit(file_name, 30, "Checking VirusTotal...")
            try:
                params = {'apikey': self.api_key, 'resource': file_hash}
                response = requests.get(f"{self.base_url}/file/report", params=params)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # If file was previously scanned
                    if result.get('response_code') == 1:
                        positives = result.get('positives', 0)
                        total = result.get('total', 0)
                        self.scan_progress.emit(file_name, 100, f"Scan complete: {positives}/{total} detections")
                        
                        is_safe = positives == 0
                        details = {
                            'positives': positives,
                            'total': total,
                            'scan_date': result.get('scan_date', 'Unknown'),
                            'permalink': result.get('permalink', '')
                        }
                        
                        # Cache the result
                        self.scan_cache[file_hash] = (time.time(), (is_safe, details))
                        return is_safe, details
                
                # If file needs to be scanned
                self.scan_progress.emit(file_name, 50, "Uploading file for scanning...")
                
                # Upload file
                files = {'file': (file_name, open(file_path, 'rb'))}
                upload_response = requests.post(
                    f"{self.base_url}/file/scan",
                    files=files,
                    params={'apikey': self.api_key}
                )
                
                if upload_response.status_code == 200:
                    upload_result = upload_response.json()
                    scan_id = upload_result.get('scan_id')
                    
                    # Wait for scan results
                    max_checks = 10
                    checks = 0
                    
                    while checks < max_checks:
                        self.scan_progress.emit(file_name, 60 + (checks * 4), f"Checking scan results ({checks + 1}/{max_checks})...")
                        time.sleep(15)  # Wait between checks
                        
                        check_response = requests.get(
                            f"{self.base_url}/file/report",
                            params={'apikey': self.api_key, 'resource': scan_id}
                        )
                        
                        if check_response.status_code == 200:
                            result = check_response.json()
                            if result.get('response_code') == 1:
                                positives = result.get('positives', 0)
                                total = result.get('total', 0)
                                
                                is_safe = positives == 0
                                details = {
                                    'positives': positives,
                                    'total': total,
                                    'scan_date': result.get('scan_date', 'Unknown'),
                                    'permalink': result.get('permalink', '')
                                }
                                
                                # Cache the result
                                self.scan_cache[file_hash] = (time.time(), (is_safe, details))
                                self.scan_progress.emit(file_name, 100, f"Scan complete: {positives}/{total} detections")
                                return is_safe, details
                        
                        checks += 1
                    
                    # If we get here, scan didn't complete in time
                    return True, "Scan timeout - assuming safe"
                    
            except requests.exceptions.RequestException as e:
                self.error_count += 1
                if self.error_count >= self.max_errors:
                    self.scan_progress.emit(file_name, 100, "API error - skipping future scans")
                    return True, "API error - scanning disabled"
                return True, f"API error: {str(e)} - assuming safe"
                
            except Exception as e:
                self.scan_progress.emit(file_name, 0, f"Unexpected error: {e}")
                return False, f"Scan error: {str(e)}"
                
        except Exception as e:
            # Catch any unexpected errors
            print(f"Critical error in virus scan: {e}")
            return True, "Error during scan - assuming safe"
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
