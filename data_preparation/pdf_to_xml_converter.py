#!/usr/bin/env python3
"""
PDF to XML Converter using GROBID
Tool for converting PDF files to XML format

Usage:
python pdf_to_xml_converter.py input_folder output_folder

Dependencies:
- requests (for communicating with GROBID API)
- pathlib (for file path handling)
- tqdm (for progress bar display)
"""

import os
import sys
import requests
import time
from pathlib import Path
from typing import List, Optional
import argparse
from tqdm import tqdm
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pdf_conversion.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class GROBIDConverter:
    """GROBID PDF to XML converter"""
    
    def __init__(self, grobid_url: str = "http://localhost:8070"):
        """
        Initialize GROBID converter
        
        Args:
            grobid_url: GROBID service URL address
        """
        self.grobid_url = grobid_url
        self.api_endpoint = f"{grobid_url}/api/processFulltextDocument"
        
    def check_grobid_service(self) -> bool:
        """
        Check if GROBID service is available
        
        Returns:
            bool: Whether the service is available
        """
        try:
            response = requests.get(f"{self.grobid_url}/api/isalive", timeout=10)
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            logger.error(f"Cannot connect to GROBID service: {e}")
            return False
    
    def convert_pdf_to_xml(self, pdf_path: Path, output_path: Path) -> bool:
        """
        Convert a single PDF file to XML
        
        Args:
            pdf_path: PDF file path
            output_path: Output XML file path
            
        Returns:
            bool: Whether conversion was successful
        """
        try:
            # Check if PDF file exists
            if not pdf_path.exists():
                logger.error(f"PDF file does not exist: {pdf_path}")
                return False
            
            # Prepare file upload
            with open(pdf_path, 'rb') as pdf_file:
                files = {'input': (pdf_path.name, pdf_file, 'application/pdf')}
                
                # Send request to GROBID
                response = requests.post(
                    self.api_endpoint,
                    files=files,
                    timeout=300  # 5 minutes timeout
                )
            
            if response.status_code == 200:
                # Save XML content
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as xml_file:
                    xml_file.write(response.text)
                
                logger.info(f"Successfully converted: {pdf_path.name} -> {output_path.name}")
                return True
            else:
                logger.error(f"Conversion failed for {pdf_path.name}: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error occurred while converting {pdf_path.name}: {e}")
            return False
    
    def batch_convert(self, input_folder: Path, output_folder: Path) -> dict:
        """
        Batch convert PDF files
        
        Args:
            input_folder: Input PDF folder path
            output_folder: Output XML folder path
            
        Returns:
            dict: Conversion result statistics
        """
        # Check GROBID service
        if not self.check_grobid_service():
            logger.error("GROBID service is not available, please ensure the service is running")
            return {"success": 0, "failed": 0, "total": 0}
        
        # Find all PDF files
        pdf_files = list(input_folder.glob("**/*.pdf"))
        
        if not pdf_files:
            logger.warning(f"No PDF files found in {input_folder}")
            return {"success": 0, "failed": 0, "total": 0}
        
        logger.info(f"Found {len(pdf_files)} PDF files")
        
        # Create output folder
        output_folder.mkdir(parents=True, exist_ok=True)
        
        # Statistics
        stats = {"success": 0, "failed": 0, "total": len(pdf_files)}
        
        # Batch conversion
        for pdf_file in tqdm(pdf_files, desc="Converting PDF files"):
            # Calculate relative path to maintain folder structure
            relative_path = pdf_file.relative_to(input_folder)
            xml_file = output_folder / relative_path.with_suffix('.xml')
            
            # Convert file
            if self.convert_pdf_to_xml(pdf_file, xml_file):
                stats["success"] += 1
            else:
                stats["failed"] += 1
            
            # Add small delay to avoid overload
            time.sleep(0.1)
        
        return stats

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Convert PDF files to XML using GROBID")
    parser.add_argument("input_folder", help="Input folder path containing PDF files")
    parser.add_argument("output_folder", help="Output folder path for XML files")
    parser.add_argument("--grobid-url", default="http://localhost:8070", 
                       help="GROBID service URL (default: http://localhost:8070)")
    parser.add_argument("--check-only", action="store_true", 
                       help="Only check GROBID service status")
    
    args = parser.parse_args()
    
    # Check GROBID service
    converter = GROBIDConverter(args.grobid_url)
    
    if args.check_only:
        if converter.check_grobid_service():
            logger.info("GROBID service is running normally")
        else:
            logger.error("GROBID service is not available")
        return
    
    # Validate input folder
    input_path = Path(args.input_folder)
    if not input_path.exists():
        logger.error(f"Input folder does not exist: {args.input_folder}")
        sys.exit(1)
    
    if not input_path.is_dir():
        logger.error(f"Input path is not a folder: {args.input_folder}")
        sys.exit(1)
    
    # Start conversion
    output_path = Path(args.output_folder)
    logger.info(f"Starting PDF file conversion...")
    logger.info(f"Input folder: {input_path}")
    logger.info(f"Output folder: {output_path}")
    
    stats = converter.batch_convert(input_path, output_path)
    
    # Output statistics
    logger.info("Conversion completed!")
    logger.info(f"Total: {stats['total']} files")
    logger.info(f"Success: {stats['success']} files")
    logger.info(f"Failed: {stats['failed']} files")
    
    if stats['failed'] > 0:
        sys.exit(1)

if __name__ == "__main__":
    main() 