"""Main pipeline service for orchestrating the vis2attr analysis workflow."""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

from ..core.config import Config, ConfigWrapper
from ..core.schemas import Item, VLMRequest, VLMRaw, Attributes, Decision
from ..core.constants import (
    DEFAULT_MAX_IMAGES_PER_ITEM,
    DEFAULT_MAX_RESOLUTION,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    SECONDS_TO_MILLISECONDS
)
from ..core.exceptions import (
    PipelineError, ConfigurationError, ResourceError, ProcessingError,
    wrap_exception, create_pipeline_error
)
from ..ingest.fs import FileSystemIngestor
from ..prompt.builder import JinjaPromptBuilder
from ..providers.factory import create_provider
from ..parse.service import ParseService
from ..storage.factory import create_storage_backend


class PipelineResult:
    """Result of a pipeline execution."""
    
    def __init__(
        self,
        item_id: str,
        success: bool,
        attributes: Optional[Attributes] = None,
        raw_response: Optional[VLMRaw] = None,
        decision: Optional[Decision] = None,
        error: Optional[str] = None,
        processing_time_ms: Optional[float] = None,
        storage_ids: Optional[Dict[str, str]] = None
    ):
        self.item_id = item_id
        self.success = success
        self.attributes = attributes
        self.raw_response = raw_response
        self.decision = decision
        self.error = error
        self.processing_time_ms = processing_time_ms
        self.storage_ids = storage_ids or {}
        self.timestamp = datetime.now()


class PipelineService:
    """Main pipeline service for orchestrating the vis2attr analysis workflow.
    
    This service coordinates all components in the pipeline:
    1. Image ingestion
    2. Prompt building
    3. VLM provider calls
    4. Response parsing
    5. Decision making
    6. Storage
    """
    
    def __init__(self, config: Config):
        """Initialize the pipeline service.
        
        Args:
            config: Configuration object containing all pipeline settings
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self._setup_ingestor()
        self._setup_prompt_builder()
        self._setup_provider()
        self._setup_parser()
        self._setup_storage()
        
        self.logger.info("Pipeline service initialized successfully")
    
    def _setup_ingestor(self) -> None:
        """Set up the image ingestor."""
        try:
            if self.config.ingestor == "ingest.fs":
                io_config = self.config.io
                io_wrapper = ConfigWrapper(io_config)
                security_wrapper = ConfigWrapper(self.config.security)
                self.ingestor = FileSystemIngestor(
                    supported_formats=io_wrapper.get_list("supported_formats", [".jpg", ".jpeg", ".png", ".webp"]),
                    max_images_per_item=io_wrapper.get_int("max_images_per_item", DEFAULT_MAX_IMAGES_PER_ITEM),
                    max_resolution=io_wrapper.get_int("max_resolution", DEFAULT_MAX_RESOLUTION),
                    strip_exif=security_wrapper.get_bool("strip_exif", True)
                )
            else:
                raise PipelineError(f"Unsupported ingestor: {self.config.ingestor}")
            
            self.logger.info(f"Ingestor initialized: {self.config.ingestor}")
        except Exception as e:
            raise wrap_exception(e, "Failed to initialize ingestor", 
                               {"ingestor": self.config.ingestor})
    
    def _setup_prompt_builder(self) -> None:
        """Set up the prompt builder."""
        try:
            prompt_config = {
                "template_path": str(Path(self.config.prompt_template).parent),
                "template_name": Path(self.config.prompt_template).name
            }
            self.prompt_builder = JinjaPromptBuilder(prompt_config)
            self.logger.info(f"Prompt builder initialized with template: {self.config.prompt_template}")
        except Exception as e:
            raise wrap_exception(e, "Failed to initialize prompt builder", 
                               {"template": self.config.prompt_template})
    
    def _setup_provider(self) -> None:
        """Set up the VLM provider."""
        try:
            provider_name = self.config.provider.replace("providers.", "")
            provider_config = self.config.get_provider_config(provider_name)
            
            self.provider = create_provider(provider_name, provider_config)
            self.logger.info(f"Provider initialized: {provider_name}")
        except Exception as e:
            raise wrap_exception(e, "Failed to initialize provider", 
                               {"provider": provider_name})
    
    def _setup_parser(self) -> None:
        """Set up the response parser."""
        try:
            self.parser = ParseService()
            self.logger.info("Parser service initialized")
        except Exception as e:
            raise wrap_exception(e, "Failed to initialize parser")
    
    def _setup_storage(self) -> None:
        """Set up the storage backend."""
        try:
            storage_name = self.config.storage.replace("storage.", "")
            storage_config = self.config.get_storage_config()
            
            self.storage = create_storage_backend(storage_name, storage_config)
            self.logger.info(f"Storage backend initialized: {storage_name}")
        except Exception as e:
            raise wrap_exception(e, "Failed to initialize storage", 
                               {"storage": storage_name})
    
    def analyze_item(self, input_path: Union[str, Path]) -> PipelineResult:
        """Analyze a single item through the complete pipeline.
        
        Args:
            input_path: Path to image file or directory containing images
            
        Returns:
            PipelineResult: Complete analysis result with attributes and metadata
        """
        start_time = datetime.now()
        item_id = None
        
        try:
            self.logger.info(f"Starting analysis for: {input_path}")
            
            # Step 1: Ingest images
            self.logger.debug("Step 1: Ingesting images")
            item = self.ingestor.load(input_path)
            item_id = item.item_id
            self.logger.info(f"Loaded item {item_id} with {len(item.images)} images")
            
            # Step 2: Load schema
            self.logger.debug("Step 2: Loading schema")
            schema = self.prompt_builder.load_schema(self.config.schema_path)
            self.logger.debug(f"Loaded schema with {len(schema)} fields")
            
            # Step 3: Build VLM request
            self.logger.debug("Step 3: Building VLM request")
            provider_config = self.config.get_provider_config(
                self.config.provider.replace("providers.", "")
            )
            provider_wrapper = ConfigWrapper(provider_config)
            vlm_request = self.prompt_builder.build_request(
                item=item,
                schema=schema,
                model=provider_wrapper.get("model", "gpt-4-vision-preview"),
                max_tokens=provider_wrapper.get_int("max_tokens", DEFAULT_MAX_TOKENS),
                temperature=provider_wrapper.get("temperature", DEFAULT_TEMPERATURE)
            )
            self.logger.debug(f"Built VLM request for model: {vlm_request.model}")
            
            # Step 4: Call VLM provider
            self.logger.debug("Step 4: Calling VLM provider")
            raw_response = self.provider.predict(vlm_request)
            self.logger.info(f"Received response from {raw_response.provider} in {raw_response.latency_ms}ms")
            
            # Step 5: Parse response
            self.logger.debug("Step 5: Parsing VLM response")
            attributes = self.parser.parse_response(raw_response, schema)
            self.logger.info(f"Parsed attributes with {len(attributes.data)} fields")
            
            # Step 6: Make decision
            self.logger.debug("Step 6: Making decision")
            decision = self._make_decision(attributes, schema)
            self.logger.info(f"Decision: {'accepted' if decision.accepted else 'rejected'} (confidence: {decision.confidence_score:.3f})")
            
            # Step 7: Store results
            self.logger.debug("Step 7: Storing results")
            storage_ids = self._store_results(item_id, attributes, raw_response, decision)
            self.logger.info(f"Stored results with IDs: {storage_ids}")
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * SECONDS_TO_MILLISECONDS
            
            self.logger.info(f"Analysis completed successfully for {item_id} in {processing_time:.1f}ms")
            
            return PipelineResult(
                item_id=item_id,
                success=True,
                attributes=attributes,
                raw_response=raw_response,
                decision=decision,
                processing_time_ms=processing_time,
                storage_ids=storage_ids
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * SECONDS_TO_MILLISECONDS
            wrapped_error = wrap_exception(e, "Pipeline analysis failed", 
                                         {"item_id": item_id, "input_path": str(input_path)})
            self.logger.error(str(wrapped_error), exc_info=True)
            
            return PipelineResult(
                item_id=item_id or "unknown",
                success=False,
                error=str(wrapped_error),
                processing_time_ms=processing_time
            )
    
    def analyze_batch(self, input_paths: List[Union[str, Path]]) -> List[PipelineResult]:
        """Analyze multiple items in batch.
        
        Args:
            input_paths: List of paths to image files or directories
            
        Returns:
            List[PipelineResult]: Results for each item
        """
        self.logger.info(f"Starting batch analysis of {len(input_paths)} items")
        
        results = []
        for i, input_path in enumerate(input_paths, 1):
            self.logger.info(f"Processing item {i}/{len(input_paths)}: {input_path}")
            result = self.analyze_item(input_path)
            results.append(result)
            
            if not result.success:
                self.logger.warning(f"Item {i} failed: {result.error}")
        
        successful = sum(1 for r in results if r.success)
        self.logger.info(f"Batch analysis completed: {successful}/{len(results)} successful")
        
        return results
    
    def _make_decision(self, attributes: Attributes, schema: Dict[str, Any]) -> Decision:
        """Make a decision about whether to accept the extracted attributes.
        
        Args:
            attributes: Extracted attributes
            schema: Schema definition
            
        Returns:
            Decision: Decision with acceptance status and reasoning
        """
        # For now, implement a simple threshold-based decision
        # TODO: Implement more sophisticated decision rules engine
        
        field_flags = {}
        reasons = []
        overall_confidence = 0.0
        field_count = 0
        
        for field_name, field_value in attributes.data.items():
            if field_name in attributes.confidences:
                confidence = attributes.confidences[field_name]
                threshold = self.config.get_threshold(field_name)
                
                if confidence >= threshold:
                    field_flags[field_name] = "accepted"
                else:
                    field_flags[field_name] = "low_confidence"
                    reasons.append(f"{field_name} confidence {confidence:.3f} below threshold {threshold:.3f}")
                
                overall_confidence += confidence
                field_count += 1
        
        if field_count > 0:
            overall_confidence /= field_count
        
        # Accept if overall confidence is above default threshold
        accepted = overall_confidence >= self.config.get_threshold("default")
        
        if not accepted:
            reasons.append(f"Overall confidence {overall_confidence:.3f} below default threshold {self.config.get_threshold('default'):.3f}")
        
        return Decision(
            accepted=accepted,
            field_flags=field_flags,
            reasons=reasons,
            confidence_score=overall_confidence
        )
    
    def _store_results(
        self, 
        item_id: str, 
        attributes: Attributes, 
        raw_response: VLMRaw, 
        decision: Decision
    ) -> Dict[str, str]:
        """Store all pipeline results.
        
        Args:
            item_id: Item identifier
            attributes: Extracted attributes
            raw_response: Raw VLM response
            decision: Decision result
            
        Returns:
            Dict[str, str]: Storage IDs for each stored component
        """
        storage_ids = {}
        
        try:
            # Store attributes
            attr_id = self.storage.store_attributes(
                item_id=item_id,
                attributes=attributes,
                metadata={"decision": decision.__dict__}
            )
            storage_ids["attributes"] = attr_id
            
            # Store raw response
            raw_id = self.storage.store_raw_response(
                item_id=item_id,
                raw_response=raw_response,
                metadata={"decision": decision.__dict__}
            )
            storage_ids["raw_response"] = raw_id
            
            # Store lineage
            lineage = {
                "pipeline_version": "1.0.0",
                "config": {
                    "provider": self.config.provider,
                    "model": raw_response.model,
                    "schema_path": self.config.schema_path
                },
                "processing": {
                    "images_processed": len(attributes.lineage.get("images", [])),
                    "decision": decision.__dict__
                }
            }
            lineage_id = self.storage.store_lineage(
                item_id=item_id,
                lineage=lineage,
                metadata={"timestamp": datetime.now().isoformat()}
            )
            storage_ids["lineage"] = lineage_id
            
        except Exception as e:
            wrapped_error = wrap_exception(e, "Failed to store results", 
                                         {"item_id": item_id})
            self.logger.error(str(wrapped_error))
            raise wrapped_error
        
        return storage_ids
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline status and component health.
        
        Returns:
            Dict[str, Any]: Pipeline status information
        """
        return {
            "pipeline_version": "1.0.0",
            "components": {
                "ingestor": self.config.ingestor,
                "provider": self.config.provider,
                "storage": self.config.storage,
                "parser": "json"
            },
            "config": {
                "schema_path": self.config.schema_path,
                "prompt_template": self.config.prompt_template,
                "thresholds": self.config.thresholds
            },
            "timestamp": datetime.now().isoformat()
        }
