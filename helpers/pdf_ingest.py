"""
-----------------------------------------------------------------
(C) 2024 Prof. Tiran Dagan, FDU University. All rights reserved.
-----------------------------------------------------------------

PDF Ingestion Module

This module provides functions to ingest PDF files using the Unstructured.io API.
It processes PDFs to extract structured data and save it in a specified output directory.
"""

import logging
import os
from dataclasses import dataclass
from typing import List, Optional

from .config import global_config
from .pdf_annotation import annotate_pdf_pages
from .enrichments import enrich_json_with_summaries
from .file_and_folder import get_files_with_extension, get_pdf_page_count

from rich.console import Console
from unstructured_ingest.v2.pipeline.pipeline import Pipeline
from unstructured_ingest.v2.interfaces import ProcessorConfig
from unstructured_ingest.v2.processes.connectors.local import (LocalIndexerConfig,LocalDownloaderConfig,LocalConnectionConfig,LocalUploaderConfig)
from unstructured_ingest.v2.processes.partitioner import PartitionerConfig
from unstructured_ingest.v2.processes.chunker import ChunkerConfig
from unstructured_ingest.v2.logger import logger as unstructured_logger

@dataclass
class PipelineConfigs:
    """Configuration container for Unstructured.io pipeline"""
    processor_config: ProcessorConfig
    partitioner_config: PartitionerConfig
    indexer_config: LocalIndexerConfig
    downloader_config: LocalDownloaderConfig
    connection_config: LocalConnectionConfig
    uploader_config: LocalUploaderConfig
    chunker_config: Optional[ChunkerConfig] = None

class PDFProcessor:
    def __init__(self):
        self.console = Console()
        self.setup_logging()
        self.setup_directories()

    def setup_logging(self):
        """Configure logging settings"""
        unstructured_logger.setLevel(logging.CRITICAL)
        unstructured_logger.disabled = False
    def setup_directories(self):
        """Create necessary output directories"""
        self.output_dir = os.path.realpath(global_config.directories.output_dir)
        self.partitioned_dir = os.path.join(self.output_dir, '01_partitioned')
        self.chunked_dir = os.path.join(self.output_dir, '02_chunked')
        self.work_dir = os.path.join(self.output_dir, 'temp')
        
        for directory in [self.work_dir, self.partitioned_dir, self.chunked_dir]:
            os.makedirs(directory, exist_ok=True)

    def create_pipeline_configs(self, input_dir: str, output_dir: str, is_chunking: bool = False) -> PipelineConfigs:
        
        """Create pipeline configurations for processing"""
        processor_config = ProcessorConfig(
            num_processes=3,
            verbose=False,
            tqdm=True,
            work_dir=self.work_dir
        )
        
        partitioner_config = PartitionerConfig(
            partition_by_api=True,
            strategy="hi_res",
            api_key=global_config.api_keys.unstructured_api_key,
            partition_endpoint=global_config.api_keys.unstructured_url,
            extract_image_block_to_payload=True,
            additional_partition_args={
                "coordinates": True,
                "extract_image_block_types": ["Image", "Table"],
                "split_pdf_page": True,
                "split_pdf_allow_failed": True,
                "split_pdf_concurrency_level": 15
            }
        )
        
        configs = PipelineConfigs(
            processor_config=processor_config,
            partitioner_config=partitioner_config,
            indexer_config=LocalIndexerConfig(input_path=input_dir),
            downloader_config=LocalDownloaderConfig(),
            connection_config=LocalConnectionConfig(),
            uploader_config=LocalUploaderConfig(output_dir=output_dir)
        )
        
        if is_chunking:
            configs.chunker_config = ChunkerConfig(
                chunking_strategy="by_title",
                chunk_by_api=True,
                chunk_api_key=global_config.api_keys.unstructured_api_key,
                similarity_threshold=0.3,
                chunk_max_characters=2500,
                chunk_overlap=150
            )
            
        return configs

    def process_pdfs(self, input_dir: str, pdf_files: List[str]):
        """Main method to process PDF files"""
        self.console.print(f"Processing {len(pdf_files)} PDF files...", style="blue")
        
        # 1. Run partitioning pipeline
        self.console.print("Starting partitioning...", style="blue")
        configs = self.create_pipeline_configs(input_dir, self.partitioned_dir)
        self._run_pipeline(configs)
        
        # 2. Enrich partitions
        #
        # Currently we enhance image partitions using LLM summaries
        # To Do: Enhance table partitions using LLM summaries
        # To Do: Enhance text partitions adding tags such as [address:], [company name:], [product name:], etc
        
        self.enrich_partitions()
        
        # 3. Chunk partitions
        self.console.print("Starting chunking...", style="blue")
        chunking_configs = self.create_pipeline_configs(
            self.partitioned_dir, 
            self.chunked_dir, 
            is_chunking=True
        )
        self._run_pipeline(chunking_configs)

        self.cleanup_file_extensions()
        
        # 4. Annotate PDF pages using coordinates found in partitioned JSON files
        for pdf_file in pdf_files:
            basename = os.path.basename(pdf_file)
            pdf_path = os.path.join(input_dir, basename)
            try:
                num_pages = get_pdf_page_count(pdf_path)
                annotate_pdf_pages(basename, num_pages)
            except FileNotFoundError:
                self.console.print(f"Error: Could not find PDF file at {pdf_path}", style="red")
                logging.error(f"PDF file not found: {pdf_path}")
            except Exception as e:
                self.console.print(f"Error processing {pdf_file}: {str(e)}", style="red")
                logging.error(f"Error processing {pdf_file}: {str(e)}")

    def enrich_partitions(self):
        """Enhance partitionJSON metadata with summaries"""
        self.console.print("Enhancing image metadata...", style="blue")
        json_files = get_files_with_extension(self.partitioned_dir, '.json')
        
        for json_file in json_files:
            try:
                enrich_json_with_summaries(json_file)
            except Exception as e:
                self.console.print(f"Error processing {json_file}: {str(e)}", style="red")
                logging.error(f"Error processing {json_file}: {str(e)}")

    def cleanup_file_extensions(self):
        """Clean up duplicate .json extensions"""
        chunked_files = [
            f for f in os.listdir(self.chunked_dir) 
            if f.endswith('.json.json')
        ]
        
        for file in chunked_files:
            old_path = os.path.join(self.chunked_dir, file)
            new_path = os.path.join(self.chunked_dir, file.replace('.json.json', '.json'))
            os.rename(old_path, new_path)
            
        self.console.print(
            f"Renamed {len(chunked_files)} files to remove duplicate .json extension", 
            style="green"
        )

    def _run_pipeline(self, configs: PipelineConfigs):
        """Run the Unstructured.io pipeline with given configurations"""

        Pipeline.from_configs(
            context=configs.processor_config,
            indexer_config=configs.indexer_config,
            downloader_config=configs.downloader_config,
            source_connection_config=configs.connection_config,
            partitioner_config=configs.partitioner_config,
            chunker_config=configs.chunker_config,
            uploader_config=configs.uploader_config
        ).run()