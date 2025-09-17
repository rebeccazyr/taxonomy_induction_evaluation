#!/usr/bin/env python3
"""
Complete EMNLP 2022 PDF download script
Supports resume and progress saving
"""

import os
import time
import requests
from pathlib import Path
import re

# Configuration
BASE_URL = "https://aclanthology.org/2022.emnlp-main."
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR = os.path.join(BASE_DIR, "data", "emnlp2022", "pdf")

# Create save directory
os.makedirs(SAVE_DIR, exist_ok=True)

def scan_existing_files():
    """Scan existing files in the directory to determine progress"""
    existing_files = []
    if os.path.exists(SAVE_DIR):
        for filename in os.listdir(SAVE_DIR):
            if filename.endswith('.pdf') and filename.startswith('2022.emnlp-main.'):
                # Extract paper number from filename
                match = re.search(r'2022\.emnlp-main\.(\d+)\.pdf', filename)
                if match:
                    paper_num = int(match.group(1))
                    existing_files.append(paper_num)
    
    return sorted(existing_files)

def get_download_progress():
    """Get download progress by scanning existing files"""
    existing_files = scan_existing_files()
    
    if not existing_files:
        return {
            "last_attempted": 0,
            "successful_downloads": 0,
            "failed_downloads": 0,
            "existing_files": []
        }
    
    # Find the highest numbered file
    max_file_num = max(existing_files)
    
    return {
        "last_attempted": max_file_num,
        "successful_downloads": len(existing_files),
        "failed_downloads": 0,  # We don't track failed downloads in file system
        "existing_files": existing_files
    }

def load_progress():
    """Load download progress from file system scan"""
    return get_download_progress()


def download_pdf(paper_num: int, retries: int = 3) -> bool:
    """Download PDF file with specified number"""
    pdf_url = f"{BASE_URL}{paper_num}.pdf"
    filename = f"2022.emnlp-main.{paper_num}.pdf"
    filepath = os.path.join(SAVE_DIR, filename)
    
    # Skip if file already exists
    if os.path.exists(filepath):
        return True
    
    for attempt in range(retries):
        try:
            print(f"[{paper_num:3d}] Downloading: {filename}")
            
            response = requests.get(pdf_url, stream=True, timeout=30)
            
            # Check response status
            if response.status_code == 404:
                print(f"[{paper_num:3d}] File not found (404)")
                return False
            elif response.status_code != 200:
                print(f"[{paper_num:3d}] HTTP error: {response.status_code}")
                return False
            
            # Download file
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = os.path.getsize(filepath)
            print(f"[{paper_num:3d}] ✓ Download successful: {filename} ({file_size:,} bytes)")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"[{paper_num:3d}] Attempt {attempt + 1}/{retries} failed: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
        except Exception as e:
            print(f"[{paper_num:3d}] Unknown error: {e}")
            return False
    
    print(f"[{paper_num:3d}] ✗ Download failed: {filename}")
    return False

def main():
    """Main function: resume download from where it stopped"""
    print("Starting download of EMNLP 2022 main conference papers...")
    print(f"Save directory: {SAVE_DIR}")
    print("=" * 50)
    
    # Load progress by scanning existing files
    progress = load_progress()
    existing_files = progress["existing_files"]
    
    if existing_files:
        # Find gaps in the sequence and start from the first missing number
        max_existing = max(existing_files)
        start_num = 1
        for i in range(1, max_existing + 2):
            if i not in existing_files:
                start_num = i
                break
    else:
        start_num = 1
    
    print(f"Found {len(existing_files)} existing files")
    print(f"Starting download from number {start_num}...")
    print(f"Successfully downloaded: {progress['successful_downloads']} papers")
    print("=" * 50)
    
    paper_num = start_num
    consecutive_failures = 0
    max_consecutive_failures = 20  # Stop after 20 consecutive failures
    
    while consecutive_failures < max_consecutive_failures:
        success = download_pdf(paper_num)
        
        if success:
            progress["successful_downloads"] += 1
            consecutive_failures = 0
        else:
            progress["failed_downloads"] += 1
            consecutive_failures += 1
            print(f"[{paper_num:3d}] Consecutive failures: {consecutive_failures}/{max_consecutive_failures}")
        
        progress["last_attempted"] = paper_num
        paper_num += 1
        
        # Print progress every 10 files
        if paper_num % 10 == 0:
            print(f"Progress: {progress['successful_downloads']} successful downloads")
        
        # Add delay to avoid too frequent requests
        time.sleep(0.3)
    
    
    print("=" * 50)
    print(f"Download completed!")
    print(f"Successfully downloaded: {progress['successful_downloads']} papers")
    print(f"Failed: {progress['failed_downloads']} papers")
    print(f"Last attempted number: {progress['last_attempted']}")
    print(f"Save location: {SAVE_DIR}")

if __name__ == "__main__":
    main()
