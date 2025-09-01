#!/usr/bin/env python3
"""
Module for extracting metadata from GenBank sequences and saving to CSV.
This module handles BioSample information extraction and CSV export functionality.
"""

import csv
import re
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


class MetadataExtractor:
    """Extract metadata from GenBank sequences and save to CSV."""
    
    def __init__(self, output_dir, verbose=False, max_workers=3, save_interval=50):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.base_url = "https://www.ncbi.nlm.nih.gov"
        self.verbose = verbose
        self.max_workers = max_workers
        self.save_interval = save_interval  # Save CSV every N records
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Handle SSL certificate issues with corporate proxies like Zscaler
        self.session.verify = False
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Add retry adapter for better error handling
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=2,  # Reduce total retries
            backoff_factor=2,  # Increase backoff factor
            status_forcelist=[500, 502, 503, 504],  # Remove 429 from automatic retry
            allowed_methods=["HEAD", "GET", "OPTIONS"]  # Only retry safe methods
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Data storage
        self.sequence_data = []
        self.lock = threading.Lock()  # For thread-safe data access
        self.records_processed = 0  # Counter for incremental saving
    
    def _log_request(self, response, request_type="GET"):
        """Log the request details for debugging."""
        if not self.verbose:
            return
            
        try:
            from curlify import to_curl
            curl_command = to_curl(response.request)
            print(f"\n=== {request_type} REQUEST ===")
            print(f"URL: {response.url} Status: {response.status_code}")
            print(curl_command)
            print("=" * 50)
        except Exception as e:
            print(f"Error logging request: {e}")
    
    def get_biosample_info(self, accession):
        """Get BioSample information for breed and origin using E-utilities API."""
        # Clean accession number (remove any query parameters)
        clean_accession = accession.split('?')[0]
        
        try:
            if self.verbose:
                print(f"Fetching GenBank data via E-utilities for: {accession}")
            
            # Step 1: Search for the accession to get UID
            search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            search_params = {
                'db': 'nuccore',
                'term': accession,
                'retmode': 'json'
            }
            
            # Add delay to respect rate limits (3 requests per second)
            import time
            time.sleep(0.6)  # Increased delay to 600ms
            
            response = self.session.get(search_url, params=search_params)
            
            # Handle rate limiting with exponential backoff
            retry_count = 0
            max_retries = 3
            while response.status_code == 429 and retry_count < max_retries:
                wait_time = (2 ** retry_count) * 2  # 2, 4, 8 seconds
                print(f"Rate limited for {accession} (search), waiting {wait_time} seconds... (attempt {retry_count + 1}/{max_retries})")
                time.sleep(wait_time)
                response = self.session.get(search_url, params=search_params)
                retry_count += 1
            
            if response.status_code == 429:
                print(f"❌ Still rate limited after {max_retries} retries for {accession}")
                return {'breed': 'Unknown', 'origin': 'Unknown', 'provider': 'Unknown', 'authors': 'Unknown'}
            
            response.raise_for_status()
            
            # Parse JSON response
            import json
            search_data = response.json()
            
            if 'esearchresult' in search_data and 'idlist' in search_data['esearchresult']:
                uid_list = search_data['esearchresult']['idlist']
                if uid_list:
                    uid = uid_list[0]
                    print(f"Found UID: {uid}")
                else:
                    print(f"❌ No UID found for accession {accession}")
                    return {'breed': 'Unknown', 'origin': 'Unknown', 'provider': 'Unknown', 'authors': 'Unknown'}
            else:
                print(f"❌ Unexpected search response format for {accession}")
                return {'breed': 'Unknown', 'origin': 'Unknown', 'provider': 'Unknown', 'authors': 'Unknown'}
            
            # Step 2: Fetch GenBank record using UID
            fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            fetch_params = {
                'db': 'nuccore',
                'id': uid,
                'rettype': 'gb',
                'retmode': 'text'
            }
            
            # Add delay before second request
            time.sleep(0.6)  # Increased delay to 600ms
            
            response = self.session.get(fetch_url, params=fetch_params)
            
            # Handle rate limiting with exponential backoff
            retry_count = 0
            max_retries = 3
            while response.status_code == 429 and retry_count < max_retries:
                wait_time = (2 ** retry_count) * 2  # 2, 4, 8 seconds
                print(f"Rate limited for {accession} (fetch), waiting {wait_time} seconds... (attempt {retry_count + 1}/{max_retries})")
                time.sleep(wait_time)
                response = self.session.get(fetch_url, params=fetch_params)
                retry_count += 1
            
            if response.status_code == 429:
                print(f"❌ Still rate limited after {max_retries} retries for {accession}")
                return {'breed': 'Unknown', 'origin': 'Unknown', 'provider': 'Unknown', 'authors': 'Unknown'}
            
            response.raise_for_status()
            
            genbank_data = response.text
            
            # Extract authors from GenBank data
            authors = self._extract_authors_from_genbank_text(genbank_data)
            
            # Extract breed information from GenBank data first
            breed_info = self._extract_breed_from_genbank_text(genbank_data)
            
            # Extract source/title information
            source_info = self._extract_source_from_genbank_text(genbank_data)
            
            # Look for BioSample ID in GenBank data
            biosample_id = None
            
            # Method 1: Look for DBLINK section with BioSample
            dblink_match = re.search(r'DBLINK\s+BioSample:\s+([A-Z0-9]+)', genbank_data, re.IGNORECASE)
            if dblink_match:
                biosample_id = dblink_match.group(1)
                print(f"Method 1: Found BioSample ID '{biosample_id}' from DBLINK")
            
            # Method 2: Look for any text containing BioSample ID
            if not biosample_id:
                biosample_patterns = [
                    r'BioSample[:\s]+([A-Z]{3}[A-Z0-9]{8,})',  # SAMN + numbers
                    r'BioSample[:\s]+([A-Z]{2}[A-Z0-9]{6,})',  # Other patterns
                    r'BioSample[:\s]+([A-Z0-9]{8,})'           # General pattern
                ]
                for pattern in biosample_patterns:
                    biosample_match = re.search(pattern, genbank_data, re.IGNORECASE)
                    if biosample_match:
                        biosample_id = biosample_match.group(1)
                        if re.match(r'^[A-Z0-9]{8,}$', biosample_id): # Validation
                            print(f"Method 2: Found BioSample ID '{biosample_id}' with pattern '{pattern}'")
                            break
            
            if biosample_id:
                biosample_url = f"{self.base_url}/biosample/{biosample_id}"
                print(f"BioSample URL: {biosample_url}")
                
                # Add delay before BioSample request
                time.sleep(0.6)  # Increased delay to 600ms
                
                biosample_info = self._parse_biosample_page(biosample_url)
                
                # Use breed from GenBank if found, otherwise use from BioSample
                if breed_info != 'Unknown':
                    biosample_info['breed'] = breed_info
                    print(f"Using breed from GenBank: '{breed_info}'")
                
                # Use authors from GenBank if not found in BioSample
                if biosample_info['authors'] == 'Unknown' and authors != 'Unknown':
                    biosample_info['authors'] = authors
                
                # Add source information from GenBank
                biosample_info['source'] = source_info
                
                return biosample_info
            else:
                print(f"No BioSample ID found for {clean_accession}")
                # Return what we have from GenBank
                return {
                    'breed': breed_info,
                    'origin': 'Unknown', 
                    'provider': 'Unknown', 
                    'authors': authors,
                    'region': 'Unknown',  # Will be filled from BioSample
                    'subregion': 'Unknown',  # Will be filled from BioSample
                    'source': source_info
                }
                
        except Exception as e:
            print(f"Error getting BioSample info for {clean_accession}: {e}")
            return {'breed': 'Unknown', 'origin': 'Unknown', 'provider': 'Unknown', 'authors': 'Unknown', 'region': 'Unknown', 'subregion': 'Unknown', 'source': 'Unknown'}
    

    
    def _extract_source_from_genbank_text(self, genbank_text):
        """Extract source/title information from GenBank text data."""
        try:
            # Method 1: Look for TITLE in REFERENCE sections
            title_patterns = [
                r'TITLE\s+([^\n\r]+?)(?=\n\s*(?:JOURNAL|REFERENCE|$))',  # TITLE   Dog10K: Genome sequencing of 2000 canids
                r'TITLE\s+([^\n\r]+)',  # TITLE   Dog10K: Genome sequencing of 2000 canids
            ]
            
            for pattern in title_patterns:
                matches = re.findall(pattern, genbank_text, re.IGNORECASE)
                if matches:
                    title = matches[0].strip()
                    if title and title.lower() not in ['unknown', 'not specified', 'n/a', 'missing', 'none', 'direct submission']:
                        print(f"Found source/title in GenBank: '{title}'")
                        return title
            
            # Method 2: Look for source in /note fields
            source_patterns = [
                r'/note="source:\s*([^"]+)"',  # /note="source: Dog10K project"
                r'/note="Source:\s*([^"]+)"',  # /note="Source: Dog10K project"
                r'/note="project:\s*([^"]+)"',  # /note="project: Dog10K"
                r'/note="Project:\s*([^"]+)"',  # /note="Project: Dog10K"
            ]
            
            for pattern in source_patterns:
                matches = re.findall(pattern, genbank_text, re.IGNORECASE)
                if matches:
                    source = matches[0].strip()
                    if source and source.lower() not in ['unknown', 'not specified', 'n/a', 'missing', 'none']:
                        print(f"Found source in GenBank /note: '{source}'")
                        return source
            
            # Method 3: Look for source in other patterns
            other_source_patterns = [
                r'source[:\s]+([^\n\r,;]+)',  # source: Dog10K project
                r'Source[:\s]+([^\n\r,;]+)',  # Source: Dog10K project
                r'project[:\s]+([^\n\r,;]+)',  # project: Dog10K
                r'Project[:\s]+([^\n\r,;]+)',  # Project: Dog10K
            ]
            
            for pattern in other_source_patterns:
                matches = re.findall(pattern, genbank_text, re.IGNORECASE)
                if matches:
                    source = matches[0].strip()
                    source = re.sub(r'[^\w\s\-,\.]', '', source).strip()
                    if source and source.lower() not in ['unknown', 'not specified', 'n/a', 'missing', 'none']:
                        print(f"Found source in GenBank text: '{source}'")
                        return source
            
            print("No source/title information found in GenBank text")
            return 'Unknown'
            
        except Exception as e:
            print(f"Error extracting source from GenBank text: {e}")
            return 'Unknown'
    
    def _extract_breed_from_genbank_text(self, genbank_text):
        """Extract breed information from GenBank text data."""
        try:
            # Method 1: Look for breed in /note fields
            breed_patterns = [
                r'/note="breed:\s*([^"]+)"',  # /note="breed: Pekingese"
                r'/note="Breed:\s*([^"]+)"',  # /note="Breed: Pekingese"
                r'/note="dog breed:\s*([^"]+)"',  # /note="dog breed: Pekingese"
                r'/note="Dog breed:\s*([^"]+)"',  # /note="Dog breed: Pekingese"
                r'/note="canine breed:\s*([^"]+)"',  # /note="canine breed: Pekingese"
                r'/note="Canine breed:\s*([^"]+)"',  # /note="Canine breed: Pekingese"
            ]
            
            for pattern in breed_patterns:
                matches = re.findall(pattern, genbank_text, re.IGNORECASE)
                if matches:
                    breed = matches[0].strip()
                    if breed and breed.lower() not in ['unknown', 'not specified', 'n/a', 'missing', 'none']:
                        print(f"Found breed in GenBank /note: '{breed}'")
                        return breed
            
            # Method 2: Look for breed in other patterns
            other_breed_patterns = [
                r'breed[:\s]+([^\n\r,;]+)',  # breed: Pekingese
                r'Breed[:\s]+([^\n\r,;]+)',  # Breed: Pekingese
                r'dog breed[:\s]+([^\n\r,;]+)',  # dog breed: Pekingese
                r'canine breed[:\s]+([^\n\r,;]+)',  # canine breed: Pekingese
            ]
            
            for pattern in other_breed_patterns:
                matches = re.findall(pattern, genbank_text, re.IGNORECASE)
                if matches:
                    breed = matches[0].strip()
                    # Clean up breed name
                    breed = re.sub(r'[^\w\s\-]', '', breed).strip()
                    if breed and breed.lower() not in ['unknown', 'not specified', 'n/a', 'missing', 'none']:
                        print(f"Found breed in GenBank text: '{breed}'")
                        return breed
            
            print("No breed information found in GenBank text")
            return 'Unknown'
            
        except Exception as e:
            print(f"Error extracting breed from GenBank text: {e}")
            return 'Unknown'
    
    def _extract_authors_from_genbank_text(self, genbank_text):
        """Extract authors information from GenBank text data."""
        try:
            # Method 1: Look for AUTHORS in REFERENCE sections
            authors_patterns = [
                r'AUTHORS\s+([^\n\r]+?)(?=\n\s*(?:TITLE|JOURNAL|REFERENCE|$))',  # AUTHORS   Kidd,J.M. (until next field)
                r'AUTHORS\s+([^\n\r]+)',  # AUTHORS   Kidd,J.M. (until newline)
                r'AUTHORS\s+([^.\n\r]+)',  # AUTHORS   Kidd.J.M. (fallback)
                r'AUTHORS\s+([^;\n\r]+)',  # AUTHORS   Kidd;J.M. (fallback)
            ]
            
            for pattern in authors_patterns:
                matches = re.findall(pattern, genbank_text, re.IGNORECASE)
                if matches:
                    # Take the first author found
                    authors = matches[0].strip()
                    print(f"DEBUG: Raw authors match: '{authors}'")
                    # Clean up authors name (keep commas, dots, and hyphens)
                    authors = re.sub(r'[^\w\s\-,\.]', '', authors).strip()
                    print(f"DEBUG: Cleaned authors: '{authors}'")
                    if authors and authors.lower() not in ['unknown', 'not specified', 'n/a', 'missing']:
                        print(f"Found authors in REFERENCE: '{authors}'")
                        return authors
            
            # Method 2: Look for authors in other patterns
            other_patterns = [
                r'authors[:\s]+([^,\n\r]+)',
                r'author[:\s]+([^,\n\r]+)',
                r'contact[:\s]+([^,\n\r]+)',
                r'principal[:\s]+([^,\n\r]+)',
                r'investigator[:\s]+([^,\n\r]+)',
                r'submitter[:\s]+([^,\n\r]+)',
                r'organization[:\s]+([^,\n\r]+)',
                r'institution[:\s]+([^,\n\r]+)'
            ]
            
            for pattern in other_patterns:
                match = re.search(pattern, genbank_text, re.IGNORECASE)
                if match:
                    authors = match.group(1).strip()
                    # Clean up authors name (keep commas, dots, and hyphens)
                    authors = re.sub(r'[^\w\s\-,\.]', '', authors).strip()
                    if authors and authors.lower() not in ['unknown', 'not specified', 'n/a', 'missing']:
                        print(f"Found authors in other pattern: '{authors}'")
                        return authors
            
            print("No authors found in GenBank text")
            return 'Unknown'
            
        except Exception as e:
            print(f"Error extracting authors from GenBank text: {e}")
            return 'Unknown'
    
    def _extract_authors_from_genbank(self, soup):
        """Extract authors information from GenBank page (legacy method)."""
        try:
            page_text = soup.get_text()
            return self._extract_authors_from_genbank_text(page_text)
        except Exception as e:
            print(f"Error extracting authors from GenBank: {e}")
            return 'Unknown'
    
    def _parse_biosample_page(self, biosample_url):
        """Parse BioSample page for breed and origin information."""
        try:
            response = self.session.get(biosample_url)
            
            # Handle rate limiting with exponential backoff
            retry_count = 0
            max_retries = 3
            while response.status_code == 429 and retry_count < max_retries:
                wait_time = (2 ** retry_count) * 2  # 2, 4, 8 seconds
                print(f"Rate limited for BioSample page, waiting {wait_time} seconds... (attempt {retry_count + 1}/{max_retries})")
                import time
                time.sleep(wait_time)
                response = self.session.get(biosample_url)
                retry_count += 1
            
            if response.status_code == 429:
                print(f"❌ Still rate limited after {max_retries} retries for BioSample page")
                return {'breed': 'Unknown', 'origin': 'Unknown', 'provider': 'Unknown', 'authors': 'Unknown'}
            
            response.raise_for_status()
            
            # Log the request for debugging
            self._log_request(response, f"BIOSAMPLE_PAGE_{biosample_url.split('/')[-1]}")
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            breed = 'Unknown'
            origin = 'Unknown'
            provider = 'Unknown'
            authors = 'Unknown'
            region = 'Unknown'  # ecotype
            subregion = 'Unknown'
            
            # Method 1: Parse table structure (most reliable for BioSample pages)
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        key = cells[0].get_text().strip().lower()
                        value = cells[1].get_text().strip()
                        
                        if 'breed' in key and value and value.lower() not in ['missing', 'unknown', 'not specified', 'n/a']:
                            breed = value
                        elif 'biomaterial provider' in key and value and value.lower() not in ['missing', 'unknown', 'not specified', 'n/a']:
                            provider = value
                        elif 'country' in key and value and value.lower() not in ['missing', 'unknown', 'not specified', 'n/a']:
                            origin = value
                        elif 'isolate' in key and value and value.lower() not in ['missing', 'unknown', 'not specified', 'n/a']:
                            # Sometimes isolate contains location info
                            if not origin or origin == 'Unknown':
                                origin = value
                        elif 'ecotype' in key and value and value.lower() not in ['missing', 'unknown', 'not specified', 'n/a']:
                            region = value  # ecotype becomes region
                        elif 'geographic location' in key and value and value.lower() not in ['missing', 'unknown', 'not specified', 'n/a']:
                            subregion = value
                        elif 'location' in key and value and value.lower() not in ['missing', 'unknown', 'not specified', 'n/a']:
                            if region == 'Unknown':
                                region = value
                            elif subregion == 'Unknown':
                                subregion = value
            
            # Method 2: Look for specific patterns in text (fallback)
            page_text = soup.get_text()
            
            # Look for breed information in text
            if breed == 'Unknown':
                breed_patterns = [
                    r'breed[:\s]+([^,\n\r]+)',
                    r'strain[:\s]+([^,\n\r]+)',
                    r'isolate[:\s]+([^,\n\r]+)'
                ]
                
                for pattern in breed_patterns:
                    match = re.search(pattern, page_text, re.IGNORECASE)
                    if match:
                        breed = match.group(1).strip()
                        # Clean up breed name
                        breed = re.sub(r'[^\w\s\-]', '', breed).strip()
                        if breed and breed.lower() not in ['unknown', 'not specified', 'n/a', 'missing']:
                            break
            
            # Look for provider information in text
            if provider == 'Unknown':
                provider_patterns = [
                    r'biomaterial provider[:\s]+([^,\n\r]+)',
                    r'provider[:\s]+([^,\n\r]+)',
                    r'submitter[:\s]+([^,\n\r]+)',
                    r'contact[:\s]+([^,\n\r]+)',
                    r'organization[:\s]+([^,\n\r]+)',
                    r'institution[:\s]+([^,\n\r]+)'
                ]
                
                for pattern in provider_patterns:
                    match = re.search(pattern, page_text, re.IGNORECASE)
                    if match:
                        provider = match.group(1).strip()
                        # Clean up provider name
                        provider = re.sub(r'[^\w\s\-]', '', provider).strip()
                        if provider and provider.lower() not in ['unknown', 'not specified', 'n/a', 'missing']:
                            break
            
            # Look for origin/location information in text
            if origin == 'Unknown':
                origin_patterns = [
                    r'country[:\s]+([^,\n\r]+)',
                    r'location[:\s]+([^,\n\r]+)',
                    r'geographic[:\s]+([^,\n\r]+)',
                    r'collected[:\s]+([^,\n\r]+)',
                    r'isolation[:\s]+([^,\n\r]+)',
                    r'source[:\s]+([^,\n\r]+)'
                ]
                
                for pattern in origin_patterns:
                    match = re.search(pattern, page_text, re.IGNORECASE)
                    if match:
                        origin = match.group(1).strip()
                        # Clean up origin name
                        origin = re.sub(r'[^\w\s\-]', '', origin).strip()
                        if origin and origin.lower() not in ['unknown', 'not specified', 'n/a', 'missing']:
                            break
            
            # Look for authors information in text
            if authors == 'Unknown':
                authors_patterns = [
                    r'authors[:\s]+([^,\n\r]+)',
                    r'author[:\s]+([^,\n\r]+)',
                    r'contact[:\s]+([^,\n\r]+)',
                    r'principal[:\s]+([^,\n\r]+)',
                    r'investigator[:\s]+([^,\n\r]+)'
                ]
                
                for pattern in authors_patterns:
                    match = re.search(pattern, page_text, re.IGNORECASE)
                    if match:
                        authors = match.group(1).strip()
                        # Clean up authors name
                        authors = re.sub(r'[^\w\s\-]', '', authors).strip()
                        if authors and authors.lower() not in ['unknown', 'not specified', 'n/a', 'missing']:
                            break
            
            # Look for ecotype/region information in text
            if region == 'Unknown':
                ecotype_patterns = [
                    r'ecotype[:\s]+([^,\n\r]+)',
                    r'Ecotype[:\s]+([^,\n\r]+)',
                    r'strain[:\s]+([^,\n\r]+)',
                    r'Strain[:\s]+([^,\n\r]+)'
                ]
                
                for pattern in ecotype_patterns:
                    match = re.search(pattern, page_text, re.IGNORECASE)
                    if match:
                        region = match.group(1).strip()
                        # Clean up region name
                        region = re.sub(r'[^\w\s\-]', '', region).strip()
                        if region and region.lower() not in ['unknown', 'not specified', 'n/a', 'missing']:
                            break
            
            # Look for subregion/geographic location information in text
            if subregion == 'Unknown':
                subregion_patterns = [
                    r'geographic location[:\s]+([^,\n\r]+)',
                    r'Geographic location[:\s]+([^,\n\r]+)',
                    r'location[:\s]+([^,\n\r]+)',
                    r'Location[:\s]+([^,\n\r]+)'
                ]
                
                for pattern in subregion_patterns:
                    match = re.search(pattern, page_text, re.IGNORECASE)
                    if match:
                        subregion = match.group(1).strip()
                        # Clean up subregion name
                        subregion = re.sub(r'[^\w\s\-]', '', subregion).strip()
                        if subregion and subregion.lower() not in ['unknown', 'not specified', 'n/a', 'missing']:
                            break
            
            # Save BioSample HTML for debugging if verbose
            if self.verbose:
                biosample_file = self.output_dir / f"biosample_{biosample_url.split('/')[-1]}.html"
                with open(biosample_file, 'w', encoding='utf-8') as f:
                    f.write(soup.prettify())
                print(f"Saved BioSample HTML to: {biosample_file}")
            
            print(f"Extracted: breed='{breed}', origin='{origin}', provider='{provider}', authors='{authors}'")
            
            return {
                'breed': breed,
                'origin': origin,
                'provider': provider,
                'authors': authors,
                'region': region,
                'subregion': subregion
            }
            
        except requests.RequestException as e:
            print(f"Error parsing BioSample page: {e}")
            return {'breed': 'Unknown', 'origin': 'Unknown', 'provider': 'Unknown', 'authors': 'Unknown'}
    
    def process_sequences(self, accessions, max_sequences=None):
        """Process all sequences and extract metadata."""
        if max_sequences:
            accessions = accessions[:max_sequences]
        
        total = len(accessions)
        print(f"Processing {total} sequences for BioSample information...")
        
        def process_single_sequence(accession):
            """Process a single sequence to get BioSample information."""
            # Check if FASTA file exists
            fasta_file = self.output_dir / f"{accession}.fasta"
            if not fasta_file.exists():
                print(f"Warning: FASTA file not found for {accession}, skipping BioSample info")
                return None
            
            # Get BioSample information
            biosample_info = self.get_biosample_info(accession)
            
            # Store data thread-safely
            with self.lock:
                self.sequence_data.append({
                    'accession': accession,
                    'fasta_file': str(fasta_file),
                    'breed': biosample_info['breed'],
                    'origin': biosample_info['origin'],
                    'provider': biosample_info['provider'],
                    'authors': biosample_info['authors'],
                    'region': biosample_info.get('region', 'Unknown'),
                    'subregion': biosample_info.get('subregion', 'Unknown'),
                    'source': biosample_info.get('source', 'Unknown')
                })
                self.records_processed += 1
                
                # Check if we should save incrementally
                if self.records_processed % self.save_interval == 0:
                    self._save_incremental_csv()
            
            print(f"Processed BioSample info for: {accession}")
            
            # Add delay between sequences to respect rate limits
            import time
            time.sleep(0.2)  # 200ms delay between sequences
            
            return accession
        
        # Use threading for BioSample information gathering
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_acc = {executor.submit(process_single_sequence, acc): acc for acc in accessions}
            
            completed = 0
            for future in as_completed(future_to_acc):
                result = future.result()
                if result:
                    completed += 1
                    if completed % 10 == 0:
                        print(f"Progress: {completed}/{total} ({completed/total*100:.1f}%)")
    
    def save_metadata_to_csv(self, filename="sequences_metadata.csv"):
        """Save metadata to CSV file."""
        if not self.sequence_data:
            print("No data to save")
            return
        
        csv_file = self.output_dir / filename
        
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['accession', 'fasta_file', 'breed', 'origin', 'provider', 'authors', 'region', 'subregion', 'source']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            writer.writeheader()
            for row in self.sequence_data:
                writer.writerow(row)
        
        print(f"Metadata saved to: {csv_file}")
        print(f"Total sequences processed: {len(self.sequence_data)}")
        return csv_file
    
    def _save_incremental_csv(self, filename="sequences_metadata.csv"):
        """Save current data to CSV file (incremental save)."""
        if not self.sequence_data:
            return
        
        csv_file = self.output_dir / filename
        
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['accession', 'fasta_file', 'breed', 'origin', 'provider', 'authors', 'region', 'subregion', 'source']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            writer.writeheader()
            for row in self.sequence_data:
                writer.writerow(row)
        
        print(f"💾 Incremental save: {len(self.sequence_data)} records saved to {csv_file}")
    
    def extract_metadata_only(self, accessions, max_sequences=None, output_filename="sequences_metadata.csv"):
        """Extract metadata for existing FASTA files and save to CSV."""
        print("Starting metadata extraction...")
        print(f"Output directory: {self.output_dir}")
        
        if not accessions:
            print("No accessions provided")
            return None
        
        # Process sequences (get BioSample info)
        self.process_sequences(accessions, max_sequences)
        
        # Save metadata
        csv_file = self.save_metadata_to_csv(output_filename)
        
        print(f"Metadata extraction completed! {len(self.sequence_data)} sequences processed.")
        return csv_file


def main():
    """Main function for standalone metadata extraction."""
    import argparse
    import glob
    import os
    
    parser = argparse.ArgumentParser(
        description="Extract metadata from GenBank sequences and save to CSV"
    )
    parser.add_argument(
        'output_dir',
        help='Directory containing FASTA files and where to save CSV'
    )
    parser.add_argument(
        '--accessions',
        nargs='+',
        help='List of accession numbers to process'
    )
    parser.add_argument(
        '--accessions-file',
        help='File containing accession numbers (one per line)'
    )
    parser.add_argument(
        '--auto-detect',
        action='store_true',
        help='Auto-detect FASTA files from directory (default behavior)'
    )
    parser.add_argument(
        '--max-sequences',
        type=int,
        default=None,
        help='Maximum number of sequences to process (default: all provided)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging of all HTTP requests'
    )
    parser.add_argument(
        '--max-workers',
        type=int,
        default=10,
        help='Maximum number of worker threads (default: 10)'
    )
    parser.add_argument(
        '--output-filename',
        default='sequences_metadata.csv',
        help='Output CSV filename (default: sequences_metadata.csv)'
    )
    
    args = parser.parse_args()
    
    # Get accessions from arguments, file, or auto-detect
    accessions = []
    
    if args.accessions:
        accessions = args.accessions
        print(f"Using {len(accessions)} specified accessions")
    elif args.accessions_file:
        with open(args.accessions_file, 'r') as f:
            accessions = [line.strip() for line in f if line.strip()]
        print(f"Using {len(accessions)} accessions from file")
    elif args.auto_detect or (not args.accessions and not args.accessions_file):
        # Auto-detect from FASTA files
        fasta_files = glob.glob(os.path.join(args.output_dir, "*.fasta"))
        for fasta_file in fasta_files:
            filename = os.path.basename(fasta_file)
            accession = filename.replace('.fasta', '')
            accessions.append(accession)
        print(f"Auto-detected {len(accessions)} FASTA files")
    else:
        print("Error: Must provide --accessions, --accessions-file, or use --auto-detect")
        return
    
    if not accessions:
        print(f"Error: No accessions found in {args.output_dir}")
        return
    
    # Show sample accessions
    sample_count = min(5, len(accessions))
    print(f"Sample accessions: {', '.join(accessions[:sample_count])}")
    if len(accessions) > sample_count:
        print(f"... and {len(accessions) - sample_count} more")
    
    # Create extractor and run
    extractor = MetadataExtractor(
        args.output_dir, 
        verbose=args.verbose,
        max_workers=args.max_workers
    )
    extractor.extract_metadata_only(accessions, args.max_sequences, args.output_filename)


if __name__ == "__main__":
    main()
