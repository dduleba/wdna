#!/usr/bin/env python3
"""
Simple script to extract metadata from GenBank sequences and save to CSV.
This is a convenience wrapper around the MetadataExtractor class.
"""

import sys
import os
from pathlib import Path
import glob

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.csv_metadata_extractor import MetadataExtractor


def extract_accessions_from_fasta_files(directory):
    """Extract accession numbers from FASTA files in directory."""
    fasta_files = glob.glob(os.path.join(directory, "*.fasta"))
    accessions = []
    
    for fasta_file in fasta_files:
        # Extract accession from filename (remove .fasta extension)
        filename = os.path.basename(fasta_file)
        accession = filename.replace('.fasta', '')
        accessions.append(accession)
    
    return accessions


def main():
    """Main function for metadata extraction."""
    if len(sys.argv) < 2:
        print("Usage: python extract_metadata.py <output_dir> [accessions] [max_sequences] [save_interval]")
        print("")
        print("Arguments:")
        print("  output_dir      - Directory containing FASTA files and where to save CSV")
        print("  accessions      - Optional: Comma-separated accession numbers or 'auto' for auto-detect")
        print("  max_sequences   - Optional: Maximum number of sequences to process")
        print("  save_interval   - Optional: Save CSV every N records (default: 50)")
        print("")
        print("Examples:")
        print("  # Auto-detect FASTA files from directory")
        print("  python extract_metadata.py ./dog_sequences")
        print("")
        print("  # Auto-detect with limit")
        print("  python extract_metadata.py ./dog_sequences auto 100")
        print("")
        print("  # Specific accessions")
        print("  python extract_metadata.py ./dog_sequences AY656737.1,AY656738.1,AY656739.1")
        print("")
        print("  # Specific accessions with limit")
        print("  python extract_metadata.py ./dog_sequences AY656737.1,AY656738.1 50")
        print("")
        print("  # With custom save interval (save every 25 records)")
        print("  python extract_metadata.py ./dog_sequences auto 100 25")
        return
    
    output_dir = sys.argv[1]
    
    # Check if output directory exists
    if not os.path.exists(output_dir):
        print(f"Error: Directory '{output_dir}' not found")
        return
    
    # Handle accessions argument
    accessions = []
    max_sequences = None
    
    if len(sys.argv) > 2:
        accessions_arg = sys.argv[2]
        
        if accessions_arg.lower() == 'auto' or accessions_arg == '':
            # Auto-detect from FASTA files
            accessions = extract_accessions_from_fasta_files(output_dir)
            print(f"Auto-detected {len(accessions)} FASTA files in {output_dir}")
        else:
            # Parse comma-separated accessions
            accessions = [acc.strip() for acc in accessions_arg.split(',') if acc.strip()]
            print(f"Using {len(accessions)} specified accessions")
    else:
        # Default: auto-detect
        accessions = extract_accessions_from_fasta_files(output_dir)
        print(f"Auto-detected {len(accessions)} FASTA files in {output_dir}")
    
    # Handle max_sequences argument
    if len(sys.argv) > 3:
        try:
            max_sequences = int(sys.argv[3])
        except ValueError:
            print("Error: max_sequences must be a number")
            return
    
    # Handle save_interval argument
    save_interval = 50  # Default value
    if len(sys.argv) > 4:
        try:
            save_interval = int(sys.argv[4])
            if save_interval < 1:
                print("Error: save_interval must be at least 1")
                return
        except ValueError:
            print("Error: save_interval must be a number")
            return
    
    if not accessions:
        print(f"Error: No FASTA files found in {output_dir}")
        print("Make sure you have .fasta files in the directory")
        return
    
    if max_sequences:
        print(f"Will process up to {max_sequences} sequences")
    
    print(f"Will save CSV every {save_interval} records")
    
    # Show sample accessions
    sample_count = min(5, len(accessions))
    print(f"Sample accessions: {', '.join(accessions[:sample_count])}")
    if len(accessions) > sample_count:
        print(f"... and {len(accessions) - sample_count} more")
    
    # Create extractor and run
    extractor = MetadataExtractor(output_dir, verbose=True, max_workers=3, save_interval=save_interval)
    csv_file = extractor.extract_metadata_only(accessions, max_sequences)
    
    if csv_file:
        print(f"\n✅ Metadata extraction completed successfully!")
        print(f"📁 CSV file saved to: {csv_file}")
        print(f"📊 Processed {len(extractor.sequence_data)} sequences")
    else:
        print("\n❌ Metadata extraction failed")


if __name__ == "__main__":
    main()
