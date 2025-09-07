"""Jinja2-based prompt builder implementation."""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Union
from jinja2 import Environment, FileSystemLoader, Template
from .base import PromptBuilder
from ..core.schemas import Item, VLMRequest


class JinjaPromptBuilder(PromptBuilder):
    """Jinja2-based prompt builder for creating VLM requests.
    
    Uses Jinja2 templates to generate prompts from schemas and items.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the Jinja prompt builder.
        
        Args:
            config: Configuration containing template_path and other settings
        """
        super().__init__(config)
        self.template_path = config.get("template_path", "config/prompts")
        self._setup_jinja_env()
    
    def _setup_jinja_env(self) -> None:
        """Set up Jinja2 environment with file system loader."""
        template_dir = Path(self.template_path)
        if not template_dir.exists():
            template_dir.mkdir(parents=True, exist_ok=True)
        
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=False,  # We're not dealing with HTML
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    def build_request(
        self, 
        item: Item, 
        schema: Dict[str, Any], 
        model: str,
        max_tokens: int = 1000,
        temperature: float = 0.1
    ) -> VLMRequest:
        """Build a VLM request from an item and schema.
        
        Args:
            item: Item containing images and metadata
            schema: Schema definition for attribute extraction
            model: VLM model to use
            max_tokens: Maximum tokens for the response
            temperature: Temperature for generation
            
        Returns:
            VLMRequest ready to send to VLM provider
        """
        # Load the template
        template_name = self.config.get("template_name", "default.jinja")
        template = self.jinja_env.get_template(template_name)
        
        # Prepare template context
        context = self._prepare_context(item, schema)
        
        # Render the prompt
        prompt_content = template.render(**context)
        
        # Create messages for the VLM
        messages = self._create_messages(prompt_content, item.images)
        
        return VLMRequest(
            model=model,
            messages=messages,
            images=item.images,
            max_tokens=max_tokens,
            temperature=temperature
        )
    
    def load_schema(self, schema_path: str) -> Dict[str, Any]:
        """Load schema from YAML file.
        
        Args:
            schema_path: Path to schema file
            
        Returns:
            Schema dictionary
        """
        schema_file = Path(schema_path)
        if not schema_file.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")
        
        with open(schema_file, 'r') as f:
            if schema_file.suffix.lower() in ['.yaml', '.yml']:
                return yaml.safe_load(f)
            elif schema_file.suffix.lower() == '.json':
                return json.load(f)
            else:
                raise ValueError(f"Unsupported schema file format: {schema_file.suffix}")
    
    def get_schema_fields(self, schema: Dict[str, Any]) -> List[str]:
        """Get list of field names from schema.
        
        Args:
            schema: Schema dictionary
            
        Returns:
            List of field names
        """
        fields = []
        for key, value in schema.items():
            if isinstance(value, dict) and "value" in value:
                fields.append(key)
            elif isinstance(value, list) and len(value) > 0:
                # Handle list fields (like primary_colors, materials)
                fields.append(key)
            elif isinstance(value, str):
                # Handle string fields (like notes)
                fields.append(key)
        return fields
    
    def _prepare_context(self, item: Item, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare context for template rendering.
        
        Args:
            item: Item containing images and metadata
            schema: Schema definition
            
        Returns:
            Context dictionary for template
        """
        # Get schema fields
        fields = self.get_schema_fields(schema)
        
        # Prepare schema description for the template
        schema_description = self._format_schema_description(schema, fields)
        
        # Prepare example output format
        example_output = self._create_example_output(schema, fields)
        
        return {
            "item_id": item.item_id,
            "item_meta": item.meta,
            "num_images": len(item.images),
            "schema": schema,
            "schema_fields": fields,
            "schema_description": schema_description,
            "example_output": example_output,
            "output_format": "JSON"
        }
    
    def _format_schema_description(self, schema: Dict[str, Any], fields: List[str]) -> str:
        """Format schema description for the template.
        
        Args:
            schema: Schema dictionary
            fields: List of field names
            
        Returns:
            Formatted schema description
        """
        descriptions = []
        
        for field in fields:
            field_def = schema[field]
            
            if isinstance(field_def, dict) and "value" in field_def:
                # Single value field
                descriptions.append(f"- {field}: single value")
            elif isinstance(field_def, list):
                # List field
                descriptions.append(f"- {field}: list of items")
            elif isinstance(field_def, str):
                # String field
                descriptions.append(f"- {field}: text string")
        
        return "\n".join(descriptions)
    
    def _create_example_output(self, schema: Dict[str, Any], fields: List[str]) -> str:
        """Create example output format for the template.
        
        Args:
            schema: Schema dictionary
            fields: List of field names
            
        Returns:
            Example JSON output
        """
        example = {}
        
        for field in fields:
            field_def = schema[field]
            
            if isinstance(field_def, dict) and "value" in field_def:
                # Single value field with confidence
                example[field] = {
                    "value": "example_value",
                    "confidence": 0.85
                }
            elif isinstance(field_def, list):
                # List field
                example[field] = [
                    {"name": "example_item", "confidence": 0.80},
                    {"name": "another_item", "confidence": 0.75}
                ]
            elif isinstance(field_def, str):
                # String field
                example[field] = "example text"
        
        return json.dumps(example, indent=2)
    
    def _create_messages(self, prompt_content: str, images: List[Union[bytes, str]]) -> List[Dict[str, Any]]:
        """Create messages array for VLM request.
        
        Args:
            prompt_content: Rendered prompt content
            images: List of images
            
        Returns:
            Messages array for VLM
        """
        if not images:
            # No images, just text message
            return [{"role": "user", "content": prompt_content}]
        
        # Create multimodal message with text and images
        content = [{"type": "text", "text": prompt_content}]
        
        for image in images:
            if isinstance(image, bytes):
                # Convert bytes to base64 data URL
                import base64
                base64_image = base64.b64encode(image).decode('utf-8')
                content.append({
                    "type": "image_url",
                    "image_url": f"data:image/jpeg;base64,{base64_image}"
                })
            elif isinstance(image, str):
                # Assume it's a URL
                content.append({
                    "type": "image_url",
                    "image_url": image
                })
        
        return [{"role": "user", "content": content}]
