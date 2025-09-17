# GROBID PDF to XML Converter Usage Guide

## Overview
This tool converts PDF files to XML format using GROBID (GeneRation Of BIbliographic Data), which is a machine learning library for extracting, parsing, and re-structuring raw documents such as PDF into structured XML/TEI encoded documents.

## Prerequisites

### 1. Install GROBID
You need to have GROBID running as a service. You can run it using Docker:

```bash
# Pull and run GROBID
docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.7.3

# Or build from source
git clone https://github.com/kermitt2/grobid.git
cd grobid
./gradlew clean install
java -Xmx4G -jar grobid-service/build/libs/grobid-service-0.7.3-onejar.jar server grobid-home/config.yaml
```

### 2. Install Python Dependencies
```bash
pip install -r requirements_grobid.txt
```

## Usage

### Basic Usage
```bash
python pdf_to_xml_converter.py input_folder output_folder
```

### Check GROBID Service Status
```bash
python pdf_to_xml_converter.py --check-only
```

### Custom GROBID URL
```bash
python pdf_to_xml_converter.py input_folder output_folder --grobid-url http://your-grobid-server:8070
```

## Examples

### Convert PDFs from a folder
```bash
# Convert all PDFs in ./pdfs folder to XML in ./xml_output folder
python pdf_to_xml_converter.py ./pdfs ./xml_output
```

### Convert with custom GROBID server
```bash
# Use a remote GROBID server
python pdf_to_xml_converter.py ./pdfs ./xml_output --grobid-url http://192.168.1.100:8070
```

## Features

- **Batch Processing**: Converts multiple PDF files at once
- **Folder Structure Preservation**: Maintains the original folder hierarchy in the output
- **Progress Tracking**: Shows conversion progress with a progress bar
- **Error Handling**: Comprehensive error handling and logging
- **Service Health Check**: Verifies GROBID service availability before processing
- **Logging**: Detailed logging to both console and file (`pdf_conversion.log`)

## Output

The tool will:
1. Create the output folder if it doesn't exist
2. Maintain the same folder structure as the input
3. Convert each PDF to XML with the same name (different extension)
4. Generate a detailed log file (`pdf_conversion.log`)
5. Display progress and statistics

## Troubleshooting

### Common Issues

1. **GROBID Service Not Available**
   - Ensure GROBID is running on the specified port
   - Check if the service is accessible at the URL
   - Verify firewall settings

2. **Conversion Failures**
   - Check the log file for detailed error messages
   - Ensure PDF files are not corrupted
   - Verify GROBID service has enough memory

3. **Timeout Errors**
   - Large PDF files may take longer to process
   - Increase timeout values if needed
   - Check GROBID service performance

### Log Files
- `pdf_conversion.log`: Detailed conversion log with timestamps
- Console output: Real-time progress and status information

## API Endpoints Used

- `GET /api/isalive`: Service health check
- `POST /api/processFulltextDocument`: PDF to XML conversion

## Performance Notes

- Processing time depends on PDF size and complexity
- Large batches may take significant time
- Consider running during off-peak hours for large datasets
- The tool includes a small delay between conversions to avoid overwhelming the service

## License
This tool is provided as-is for educational and research purposes. 