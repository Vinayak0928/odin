"""
index_documents.py

A standalone script to index documents from the personal_docs directory
into the vector database using RAGManager. This script scans for text files,
processes them with proper chunking, and adds them to the vector database
with progress reporting and final statistics.

Features:
1. Imports RAGManager from rag_manager
2. Scans personal_docs directory for .txt, .md, .json files
3. Reads each file, chunks it (1000 chars with 200 overlap), and adds to vector database
4. Shows progress during processing and final statistics
"""

import argparse
import os
import logging
import sys
from pathlib import Path
from typing import List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.constants import DATA_DIR, PERSONAL_DIR

# Configure logging for the script (use safe characters for Windows console)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def parse_args():
    parser = argparse.ArgumentParser(description="Index documents into ChromaDB Vector RAG.")
    default_dir = os.path.join(DATA_DIR, "knowledge_base")
    if not os.path.exists(default_dir) and os.path.exists(PERSONAL_DIR):
        default_dir = PERSONAL_DIR
    parser.add_argument(
        "--dir",
        dest="directory",
        default=default_dir,
        help=f"Directory to index (default: {default_dir})",
    )
    parser.add_argument(
        "--owner",
        dest="owner",
        default=None,
        help="Optional owner username for document isolation",
    )
    parser.add_argument(
        "--reindex",
        action="store_true",
        help="Remove existing directory entries before indexing",
    )
    return parser.parse_args()

def main():
    """Main function to index documents into the vector database."""
    args = parse_args()

    # Import RAGManager
    try:
        from src.rag_manager import RAGManager
        logger.info("Successfully imported RAGManager")
    except ImportError as e:
        logger.error(f"Failed to import RAGManager: {e}")
        logger.error("Make sure rag_manager.py is accessible in Python path")
        return 1

    # Initialize RAGManager
    try:
        rag_manager = RAGManager()
    except Exception as e:
        logger.error(f"Failed to initialize RAGManager: {e}")
        return 1

    docs_directory = os.path.abspath(args.directory)
    directory_path = Path(docs_directory)

    # Check if directory exists
    if not directory_path.exists():
        logger.error(f"Directory '{docs_directory}' not found!")
        logger.info(f"Please create the directory and add your documents: mkdir \"{docs_directory}\"")
        return 1

    if args.reindex:
        logger.info(f"Removing prior entries for {docs_directory} before indexing...")
        rag_manager.vector_rag.remove_directory(docs_directory)

    # Supported file extensions
    supported_extensions = {'.txt', '.md', '.json', '.pdf', '.csv'}
    logger.info(f"Scanning '{docs_directory}' for {', '.join(sorted(supported_extensions))} files...")

    files_to_index = []
    for ext in supported_extensions:
        files_to_index.extend(directory_path.rglob(f"*{ext}"))

    files_to_index.sort()

    if not files_to_index:
        logger.warning(f"No supported files found in '{docs_directory}' directory.")
        return 0

    logger.info(f"Found {len(files_to_index)} file(s) to index:")
    for file_path in files_to_index:
        logger.info(f"  - {file_path}")

    logger.info("\nStarting document indexing process...")

    try:
        result = rag_manager.index_personal_documents(
            docs_directory,
            owner=args.owner,
        )

        logger.info("\n" + "="*50)
        if result.get("success"):
            logger.info("[SUCCESS] Document indexing completed successfully!")
            logger.info(f"   Indexed {result.get('indexed_count', 0)} document chunks")
            if result.get("failed_count", 0) > 0:
                logger.warning(f"   Failed to process {result['failed_count']} chunks/files")
        else:
            logger.error("[FAILED] Document indexing failed!")
            if "message" in result:
                logger.error(f"   Error: {result['message']}")

        # Show final statistics
        logger.info("\n" + "-"*30)
        logger.info("Database Statistics:")

        stats = rag_manager.get_stats()
        if "error" not in stats:
            for key, value in stats.items():
                logger.info(f"   {key}: {value}")
        else:
            logger.error(f"   Failed to retrieve statistics: {stats['error']}")

        logger.info("="*50)
        return 0 if result.get("success") else 1

    except Exception as e:
        logger.error(f"Failed to index documents: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main() or 0)
