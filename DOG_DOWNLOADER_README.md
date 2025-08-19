# GenBank Dog Sequence Downloader

Tool for automatically downloading FASTA files from GenBank for dogs (Canis lupus familiaris) with mitochondrial sequences in the range 16500-17000 bp.

## Features

- Automatic search for dog sequences in GenBank
- Download FASTA files for each sequence
- Extract breed and origin information from BioSample
- Save metadata to CSV file
- Download all found sequences (no filtering by access number)

## Requirements

```bash
pip install -r requirements.txt
```

## Usage

### Basic usage

```bash
python wdna/tools/download_fasta_gmbank.py /path/to/output/directory
```

### Limit number of sequences

```bash
python wdna/tools/download_fasta_gmbank.py /path/to/output/directory --max-sequences 100
```

### Example

```bash
python wdna/tools/download_fasta_gmbank.py ./dog_sequences --max-sequences 50
```

### Debug mode (verbose logging)

```bash
python wdna/tools/download_fasta_gmbank.py ./dog_sequences --verbose
```

### Skip existing files

```bash
python wdna/tools/download_fasta_gmbank.py ./dog_sequences --skip-existing
```

### Custom number of threads

```bash
python wdna/tools/download_fasta_gmbank.py ./dog_sequences --max-workers 20
```

### Download only FASTA files

```bash
python wdna/tools/download_fasta_gmbank.py ./dog_sequences --fasta-only --max-sequences 100
```

### Combined options

```bash
python wdna/tools/download_fasta_gmbank.py ./dog_sequences --max-sequences 100 --skip-existing --max-workers 15 --verbose
```

### Two-step process (recommended for large datasets)

```bash
# Step 1: Download FASTA files only
python wdna/tools/download_fasta_gmbank.py ./dog_sequences --fasta-only --max-sequences 500 --skip-existing

# Step 2: Get BioSample information for existing files
python wdna/tools/download_fasta_gmbank.py ./dog_sequences --skip-existing --max-sequences 500
```

## Output structure

After running the tool, you will find in the output directory:

1. **FASTA files** - individual files for each sequence (e.g., `OQ340782.fasta`)
2. **CSV file** - `dog_sequences_metadata.csv` containing metadata for each sequence

## Metadata

For each sequence, the following information is collected:

- **accession** - GenBank access number
- **fasta_file** - path to FASTA file
- **breed** - dog breed (if available)
- **origin** - country/place of origin
- **provider** - institution providing the sample

## Search criteria

The tool searches for sequences according to the following criteria:
- Organism: Canis lupus familiaris
- Type: mitochondrial DNA
- Sequence length: 16500-17000 bp
- Downloads all found sequences (no access number filtering)

## Technical notes

- The tool uses delays between requests (0.3s) to be respectful to the GenBank server
- In case of download errors, the tool continues with the next sequence
- All files are saved with UTF-8 encoding
- CSV file can be easily opened in Excel or other spreadsheet applications
- SSL certificate verification is disabled to handle corporate proxies (like Zscaler)
- Multi-threaded downloads for faster processing (default: 10 threads)
- Can skip existing files to avoid re-downloading
- Extracts breed, origin, and provider information from BioSample pages
- Handles rate limiting (429 errors) with automatic retry and exponential backoff
- Supports two-step process: FASTA download first, then BioSample information

## Testing

To test the tool with a small number of sequences:

```bash
python test_download.py
```

## Troubleshooting

### "No sequences found" error
- Check internet connection
- Make sure GenBank is accessible
- May need to adjust search parameters

### File download error
- Check write permissions in the output directory
- Make sure you have enough disk space

### Missing breed information
- Not all sequences have available BioSample information
- Some sequences may not have BioSample links

### SSL Certificate errors (corporate proxy)
- The tool automatically handles SSL certificate issues with corporate proxies
- If you still have issues, check your proxy settings
- Make sure your corporate firewall allows access to ncbi.nlm.nih.gov

## Dependencies

The tool uses only basic Python libraries:
- `requests` - for downloading data from the internet
- `beautifulsoup4` - for parsing HTML
- `lxml` - XML/HTML parser (used by BeautifulSoup)

## Author

Tool created for the WDNA project - analysis of dog mitochondrial sequences. 