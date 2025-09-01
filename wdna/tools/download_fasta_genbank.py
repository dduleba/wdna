#!/usr/bin/env python3
"""
Tool for downloading FASTA files from GenBank for dogs (Canis lupus familiaris)
with mitochondrial DNA in range 16500-17000.
"""

import os
import sys
import time
import argparse
import requests
import urllib3
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import re
from pathlib import Path
from curlify import to_curl
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Import metadata extraction functionality
try:
    from .csv_metadata_extractor import MetadataExtractor
except ImportError:
    from csv_metadata_extractor import MetadataExtractor


class GenBankDownloader:
    """Download FASTA files from GenBank for dog mitochondrial sequences."""
    
    def __init__(self, output_dir, verbose=False, skip_existing=False, max_workers=10, fasta_only=False):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.base_url = "https://www.ncbi.nlm.nih.gov"
        self.verbose = verbose
        self.skip_existing = skip_existing
        self.max_workers = max_workers
        self.fasta_only = fasta_only
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Handle SSL certificate issues with corporate proxies like Zscaler
        self.session.verify = False
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Initialize metadata extractor for CSV functionality
        self.metadata_extractor = MetadataExtractor(output_dir, verbose, max_workers)
        
    def _log_request(self, response, request_type="GET"):
        """Log the request details for debugging."""
        if not self.verbose:
            return
            
        try:
            curl_command = to_curl(response.request)
            print(f"\n=== {request_type} REQUEST ===")
            print(f"URL: {response.url} Status: {response.status_code}")
            print(curl_command)
            print("=" * 50)
        except Exception as e:
            print(f"Error logging request: {e}")
        
    def search_dog_sequences(self, max_results=2500):
        """Search for dog mitochondrial sequences in GenBank."""
        print("Searching for dog mitochondrial sequences...")
        
        # Process page by page: get UIDs, convert to accessions, check if need to download
        all_accessions = []
        page = 1
        page_size = 20  # Smaller batches for better control
        retstart = 0
        consecutive_empty_pages = 0
        max_empty_pages = 3
        total_skipped = 0
        
        term = 'Canis lupus familiaris[Organism] AND mitochondrion[All Fields] AND 16500:17000[Sequence Length]'
        
        while len(all_accessions) < max_results:
            print(f"\n=== Processing page {page} (retstart={retstart}) ===")
            
            # Step 1: Get UIDs for this page
            uids, total_count = self._api_esearch_ids(term, retstart=retstart, retmax=page_size)
            
            if page == 1 and total_count:
                print(f"Total results available (API): {total_count}")
            
            if not uids:
                consecutive_empty_pages += 1
                print(f"Warning: No UIDs returned by API on page {page} (empty page #{consecutive_empty_pages})")
                if consecutive_empty_pages >= max_empty_pages:
                    print(f"Error: Stopping after {max_empty_pages} consecutive empty API pages")
                    break
            else:
                consecutive_empty_pages = 0
                
                # Step 2: Convert UIDs to accessions for this page
                print(f"Converting {len(uids)} UIDs to accessions...")
                page_accessions = self._api_esummary_accessions(uids)
                
                # Step 3: Process each accession (check if exists, download if needed)
                page_downloaded = 0
                page_skipped = 0
                
                for accession in page_accessions:
                    if not accession:
                        continue
                        
                    # Check if file already exists
                    fasta_file = self.output_dir / f"{accession}.fasta"
                    
                    if self.skip_existing and fasta_file.exists():
                        print(f"  Skipping existing: {accession}.fasta")
                        page_skipped += 1
                        total_skipped += 1
                        continue
                    
                    # Download FASTA file
                    print(f"  Downloading: {accession}.fasta")
                    success = self._download_single_fasta(accession)
                    
                    if success:
                        page_downloaded += 1
                        all_accessions.append(accession)
                    else:
                        print(f"  Failed to download: {accession}")
                
                print(f"Page {page} results: {len(page_accessions)} accessions, {page_downloaded} downloaded, {page_skipped} skipped")
                print(f"Total downloaded so far: {len(all_accessions)}, {total_skipped} skipped")
            
            # Next page
            page += 1
            retstart += page_size
            time.sleep(0.5)  # Rate limiting between pages
        
        print(f"\n=== Search completed ===")
        print(f"Total sequences downloaded: {len(all_accessions)}, {total_skipped} skipped")
        return all_accessions[:max_results]
    
    def download_fasta_files_only(self, accessions, max_sequences=None):
        """Download only FASTA files without BioSample information."""
        if max_sequences:
            accessions = accessions[:max_sequences]
        
        total = len(accessions)
        print(f"Downloading {total} FASTA files...")
        
        completed = 0
        skipped = 0
        
        for i, accession in enumerate(accessions, 1):
            # Check if file already exists and skip if requested
            fasta_file = self.output_dir / f"{accession}.fasta"
            if self.skip_existing and fasta_file.exists():
                print(f"[{i}/{total}] Skipping existing: {accession}.fasta")
                skipped += 1
                continue
            
            # Download FASTA file
            print(f"[{i}/{total}] Downloading: {accession}.fasta")
            success = self._download_single_fasta(accession)
            
            if success:
                completed += 1
            else:
                print(f"  Failed to download: {accession}")
            
            # Progress update
            if i % 10 == 0 or i == total:
                print(f"Progress: {completed}/{total} downloaded, {skipped} skipped ({completed/total*100:.1f}%)")
            
            # Rate limiting
            time.sleep(0.1)
        
        print(f"FASTA download completed: {completed}/{total} files downloaded, {skipped} skipped")
    
    def _extract_accessions(self, soup):
        """Extract accession numbers from search results."""
        accessions = []
        
        print("Analyzing search results page...")
        
        # Look for accession links
        accession_links = soup.find_all('a', href=re.compile(r'/nuccore/[A-Z0-9]+'))
        print(f"Found {len(accession_links)} total accession links")
        
        # Also try alternative patterns
        alternative_links = soup.find_all('a', href=re.compile(r'[A-Z]{2}[0-9]{6,}'))
        print(f"Found {len(alternative_links)} alternative pattern links")
        
        # Check page title and content
        title = soup.find('title')
        if title:
            print(f"Page title: {title.get_text()}")
        
        # Look for any text containing accession patterns
        page_text = soup.get_text()
        
        # Look for "Accession: XXXX.XX" patterns (more specific)
        accession_matches = re.findall(r'Accession:\s+([A-Z0-9]+\.[0-9]+)', page_text)
        print(f"Found {len(accession_matches)} specific accession patterns in page text")
        if accession_matches:
            print(f"Sample matches: {accession_matches[:10]}")
        
        # Also look for general accession patterns
        general_matches = re.findall(r'[A-Z]{2}[0-9]{6,}', page_text)
        print(f"Found {len(general_matches)} general accession patterns in page text")
        
        # Save all found links for debugging
        all_links = []
        unique_accessions = set()  # Use set to avoid duplicates
        
        for link in accession_links:
            href = link.get('href')
            if href:
                accession = href.split('/')[-1]
                all_links.append(accession)
                
                # Clean accession number (remove query parameters)
                clean_accession = accession.split('?')[0]
                unique_accessions.add(clean_accession)
        
        # Use specific accession matches if available, otherwise fall back to links
        if accession_matches:
            # Use the specific "Accession: XXXX.XX" matches
            accessions = list(set(accession_matches))  # Remove duplicates
            print(f"Using specific accession matches: {len(accessions)} accessions")
        else:
            # Fall back to link-based extraction
            accessions = list(unique_accessions)
            print(f"Using link-based extraction: {len(accessions)} accessions")
        
        print(f"All found accessions: {all_links[:10]}...")  # Show first 10
        print(f"Total accessions: {len(accessions)}")
        
        # Save all found accessions to file for analysis
        accessions_file = self.output_dir / "all_accessions.txt"
        with open(accessions_file, 'w', encoding='utf-8') as f:
            f.write("All found accessions:\n")
            for acc in all_links:
                f.write(f"{acc}\n")
            f.write(f"\nTotal accessions ({len(accessions)}):\n")
            for acc in accessions:
                f.write(f"{acc}\n")
            f.write(f"\nAlternative pattern links ({len(alternative_links)}):\n")
            for link in alternative_links:
                f.write(f"{link.get('href')} - {link.get_text()}\n")
            f.write(f"\nText pattern matches ({len(accession_matches)}):\n")
            for match in accession_matches:
                f.write(f"{match}\n")
        print(f"Accessions saved to: {accessions_file}")
        
        return accessions
    
    def _extract_total_results(self, soup):
        """Extract total number of results from the search page."""
        try:
            # Look for patterns like "1-20 of 3310 results"
            result_text = soup.get_text()
            patterns = [
                r'(\d+)\s+results?',
                r'of\s+(\d+)\s+results?',
                r'(\d+)\s+entries?'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, result_text, re.IGNORECASE)
                if match:
                    return int(match.group(1))
            
            return None
        except Exception as e:
            print(f"Error extracting total results: {e}")
            return None

    def _api_esearch_ids(self, term: str, retstart: int, retmax: int):
        """Use NCBI ESearch API to get UIDs for nuccore entries matching term."""
        api_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        params = {
            'db': 'nuccore',
            'term': term,
            'retmode': 'json',
            'retstart': retstart,
            'retmax': retmax,
        }
        try:
            response = self.session.get(api_url, params=params)
            response.raise_for_status()
            self._log_request(response, f"API_ESEARCH_{retstart}_{retmax}")
            data = response.json()
            id_list = data.get('esearchresult', {}).get('idlist', [])
            count = int(data.get('esearchresult', {}).get('count', 0))
            return id_list, count
        except requests.RequestException as e:
            print(f"Error in ESearch API: {e}")
            return [], 0
        except ValueError:
            print("Error parsing ESearch JSON response")
            return [], 0

    def _api_esummary_accessions(self, uids: list[str]) -> list[str]:
        """Get accessions for a batch of UIDs using ESummary API."""
        api_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        params = {
            'db': 'nuccore',
            'id': ','.join(uids),
            'retmode': 'json'
        }
        
        try:
            response = self.session.get(api_url, params=params)
            response.raise_for_status()
            self._log_request(response, f"API_ESUMMARY_BATCH_{len(uids)}")
            
            data = response.json()
            result = data.get('result', {})
            
            accessions = []
            for uid in uids:
                if uid in result:
                    uid_data = result[uid]
                    accession = uid_data.get('accessionversion', '')
                    if accession:
                        accessions.append(accession)
            
            return accessions
            
        except requests.RequestException as e:
            print(f"Error in ESummary API: {e}")
            return []
        except ValueError:
            print("Error parsing ESummary JSON response")
            return []

    def _api_fetch_fasta_by_id(self, uid: str, max_retries=3) -> str | None:
        """Fetch FASTA by numeric UID using EFetch API and return raw FASTA text."""
        api_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        params = {
            'db': 'nuccore',
            'id': uid,
            'rettype': 'fasta',
            'retmode': 'text'
        }
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(api_url, params=params)
                
                # Handle rate limiting (429 errors)
                if response.status_code == 429:
                    wait_time = (attempt + 1) * 2  # Exponential backoff: 2s, 4s, 6s
                    print(f"Rate limited (429), waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                    time.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                self._log_request(response, f"API_EFETCH_FASTA_UID_{uid}")
                text = response.text
                if text and text.startswith('>'):
                    return text
                return None
                
            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 1
                    print(f"Error fetching FASTA for UID {uid} (attempt {attempt + 1}/{max_retries}): {e}")
                    print(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    print(f"Failed to fetch FASTA for UID {uid} after {max_retries} attempts: {e}")
                    return None
        
        return None

    def _download_single_fasta(self, accession: str) -> bool:
        """Download a single FASTA file by accession number."""
        try:
            api_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            params = {
                'db': 'nuccore',
                'id': accession,
                'rettype': 'fasta',
                'retmode': 'text'
            }
            
            response = self.session.get(api_url, params=params)
            
            # Handle rate limiting
            if response.status_code == 429:
                print(f"    Rate limited (429) for {accession}, waiting 3s...")
                time.sleep(3)
                response = self.session.get(api_url, params=params)
            
            response.raise_for_status()
            content = response.text
            
            if content.startswith('>'):
                # Remove empty lines from FASTA content
                cleaned_content = '\n'.join(line for line in content.split('\n') if line.strip())
                
                fasta_file = self.output_dir / f"{accession}.fasta"
                with open(fasta_file, 'w') as f:
                    f.write(cleaned_content)
                
                return True
            else:
                print(f"    Invalid FASTA format for {accession}")
                return False
                
        except requests.RequestException as e:
            print(f"    Error downloading FASTA for {accession}: {e}")
            return False

    def _parse_accession_from_fasta(self, fasta_text: str) -> str:
        """Parse accession from FASTA header line (>ACCESSION description)."""
        try:
            first_line = fasta_text.splitlines()[0].strip()
            if first_line.startswith('>'):
                token = first_line[1:].split()[0].strip()
                return token
            return ""
        except Exception:
            return ""
    
    def _extract_fasta_from_html(self, soup, accession):
        """Extract FASTA sequence from HTML page."""
        try:
            # Look for the sequence content in various possible locations
            fasta_content = None
            
            # Method 1: Look for pre tags containing sequence data
            pre_tags = soup.find_all('pre')
            for pre in pre_tags:
                text = pre.get_text()
                if text.startswith(f'>{accession}') or text.startswith('>'):
                    fasta_content = text
                    break
            
            # Method 2: Look for textarea with sequence data
            if not fasta_content:
                textarea = soup.find('textarea')
                if textarea:
                    text = textarea.get_text()
                    if text.startswith(f'>{accession}') or text.startswith('>'):
                        fasta_content = text
            
            # Method 3: Look for div with sequence data
            if not fasta_content:
                sequence_divs = soup.find_all('div', class_=re.compile(r'sequence|fasta', re.IGNORECASE))
                for div in sequence_divs:
                    text = div.get_text()
                    if text.startswith(f'>{accession}') or text.startswith('>'):
                        fasta_content = text
                        break
            
            # Method 4: Look for any text containing the accession and sequence
            if not fasta_content:
                page_text = soup.get_text()
                # Find pattern: >ACCESSION description\nSEQUENCE
                pattern = rf'>({accession}[^\n]*)\n([A-Z\n]+)'
                match = re.search(pattern, page_text)
                if match:
                    header = match.group(1)
                    sequence = match.group(2).replace('\n', '')
                    fasta_content = f">{header}\n{sequence}"
            
            if fasta_content:
                print(f"Successfully extracted FASTA for {accession}")
                return fasta_content
            else:
                print(f"Could not find FASTA content for {accession}")
                # Save the HTML for debugging
                debug_file = self.output_dir / f"{accession}_debug.html"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(soup.prettify())
                print(f"Saved debug HTML to: {debug_file}")
                return None
                
        except Exception as e:
            print(f"Error extracting FASTA from HTML for {accession}: {e}")
            return None
    
    def download_fasta(self, accession):
        """Download FASTA file for given accession number."""
        # Clean accession number (remove any query parameters)
        clean_accession = accession.split('?')[0]
        
        # Try E-utilities API first (most reliable)
        try:
            api_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            params = {
                'db': 'nuccore',
                'id': clean_accession,
                'rettype': 'fasta',
                'retmode': 'text'
            }
            
            response = self.session.get(api_url, params=params)
            response.raise_for_status()
            
            # Log the request for debugging
            self._log_request(response, f"API_FASTA_{clean_accession}")
            
            content = response.text
            if content.startswith('>'):
                # Normalize accession from header
                normalized_acc = self._parse_accession_from_fasta(content) or clean_accession
                fasta_file = self.output_dir / f"{normalized_acc}.fasta"
                # Remove empty lines from FASTA content
                cleaned_content = '\n'.join(line for line in content.split('\n') if line.strip())
                with open(fasta_file, 'w') as f:
                    f.write(cleaned_content)
                
                print(f"Downloaded: {normalized_acc}.fasta (API)")
                return fasta_file
            else:
                print(f"API returned non-FASTA content for {clean_accession}")
                
        except requests.RequestException as e:
            print(f"Error with API for {clean_accession}: {e}")
        
        # Add delay for API requests
        time.sleep(0.1)
        
        # Fallback to web interface
        urls_to_try = [
            f"{self.base_url}/nuccore/{clean_accession}?report=fasta",
            f"{self.base_url}/nuccore/{clean_accession}?report=fasta&format=text",
            f"{self.base_url}/nuccore/{clean_accession}?report=fasta&retmode=text"
        ]
        
        for url in urls_to_try:
            try:
                response = self.session.get(url)
                response.raise_for_status()
                
                # Log the request for debugging
                self._log_request(response, f"WEB_FASTA_{clean_accession}")
                
                # Check if response is already FASTA format
                content = response.text
                if content.startswith(f'>{clean_accession}') or content.startswith('>'):
                    # Direct FASTA format
                    fasta_file = self.output_dir / f"{clean_accession}.fasta"
                    # Remove empty lines from FASTA content
                    cleaned_content = '\n'.join(line for line in content.split('\n') if line.strip())
                    with open(fasta_file, 'w') as f:
                        f.write(cleaned_content)
                    
                    print(f"Downloaded: {clean_accession}.fasta (web direct)")
                    return fasta_file
                else:
                    # HTML format, need to extract FASTA
                    soup = BeautifulSoup(response.content, 'html.parser')
                    fasta_content = self._extract_fasta_from_html(soup, clean_accession)
                    
                    if fasta_content:
                        fasta_file = self.output_dir / f"{clean_accession}.fasta"
                        # Remove empty lines from FASTA content
                        cleaned_content = '\n'.join(line for line in fasta_content.split('\n') if line.strip())
                        with open(fasta_file, 'w') as f:
                            f.write(cleaned_content)
                        
                        print(f"Downloaded: {clean_accession}.fasta (web extracted)")
                        return fasta_file
                
            except requests.RequestException as e:
                print(f"Error with URL {url}: {e}")
                continue
        
        print(f"Could not download FASTA for {clean_accession} from any source")
        return None
    
    def get_biosample_info(self, accession):
        """Get BioSample information for breed and origin."""
        return self.metadata_extractor.get_biosample_info(accession)
    
    def process_sequences(self, accessions, max_sequences=None):
        """Process all sequences and download FASTA files with metadata."""
        return self.metadata_extractor.process_sequences(accessions, max_sequences)
    
    def save_metadata_to_csv(self, filename="dog_sequences_metadata.csv"):
        """Save metadata to CSV file."""
        return self.metadata_extractor.save_metadata_to_csv(filename)
    
    def run(self, max_sequences=None):
        """Main method to run the downloader."""
        print("Starting GenBank dog sequence downloader...")
        print(f"Output directory: {self.output_dir}")
        
        # Search for sequences
        accessions = self.search_dog_sequences()
        
        if not accessions:
            print("No sequences found")
            return
        
        # If fasta_only mode, just download FASTA files and exit
        if self.fasta_only:
            print("FASTA-only mode: Downloading FASTA files only...")
            self.download_fasta_files_only(accessions, max_sequences)
            print(f"FASTA download completed! {len(accessions)} sequences processed.")
            return
        
        # Process sequences (download FASTA + get BioSample info)
        self.process_sequences(accessions, max_sequences)
        
        # Save metadata
        self.save_metadata_to_csv()
        
        print(f"Download completed! {len(self.metadata_extractor.sequence_data)} sequences processed.")


def main():
    """Main function with command line interface."""
    parser = argparse.ArgumentParser(
        description="Download FASTA files from GenBank for dog mitochondrial sequences"
    )
    parser.add_argument(
        'output_dir',
        help='Directory to save FASTA files and metadata'
    )
    parser.add_argument(
        '--max-sequences',
        type=int,
        default=None,
        help='Maximum number of sequences to download (default: all found)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging of all HTTP requests'
    )
    parser.add_argument(
        '--skip-existing',
        action='store_true',
        help='Skip downloading FASTA files that already exist'
    )
    parser.add_argument(
        '--max-workers',
        type=int,
        default=10,
        help='Maximum number of worker threads (default: 10)'
    )
    parser.add_argument(
        '--fasta-only',
        action='store_true',
        help='Download only FASTA files without BioSample information'
    )
    parser.add_argument(
        '--metadata-only',
        action='store_true',
        help='Extract metadata only for existing FASTA files (no downloading)'
    )
    parser.add_argument(
        '--accessions-file',
        help='File containing accession numbers for metadata extraction (one per line)'
    )
    
    args = parser.parse_args()
    
    # Handle metadata-only mode
    if args.metadata_only:
        if not args.accessions_file:
            print("Error: --metadata-only requires --accessions-file")
            return
        
        # Read accessions from file
        with open(args.accessions_file, 'r') as f:
            accessions = [line.strip() for line in f if line.strip()]
        
        # Create extractor and run metadata extraction only
        extractor = MetadataExtractor(
            args.output_dir, 
            verbose=args.verbose,
            max_workers=args.max_workers
        )
        extractor.extract_metadata_only(accessions, args.max_sequences)
        return
    
    # Create downloader and run
    downloader = GenBankDownloader(
        args.output_dir, 
        verbose=args.verbose,
        skip_existing=args.skip_existing,
        max_workers=args.max_workers,
        fasta_only=args.fasta_only
    )
    downloader.run(args.max_sequences)


if __name__ == "__main__":
    main()
