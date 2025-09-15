# API Reference

## Data Models

### Core Data Structures

#### `Item`

Represents an item with images to be processed.

```python
@dataclass
class Item:
    item_id: str
    images: List[Union[bytes, str]]  # Image data or URIs
    meta: Dict[str, Any] = None
```

**Fields:**
- `item_id` (str): Unique identifier for the item
- `images` (List[Union[bytes, str]]): List of image data or URIs
- `meta` (Dict[str, Any], optional): Additional metadata

**Example:**
```python
item = Item(
    item_id="item_001",
    images=[b"image_data", "path/to/image.jpg"],
    meta={"source": "catalog", "category": "electronics"}
)
```

#### `VLMRequest`

Request to be sent to a VLM provider.

```python
@dataclass
class VLMRequest:
    model: str
    messages: List[Dict[str, Any]]
    images: List[Union[bytes, str]]
    max_tokens: int = 1000
    temperature: float = 0.1
```

**Fields:**
- `model` (str): VLM model identifier
- `messages` (List[Dict[str, Any]]): Conversation messages
- `images` (List[Union[bytes, str]]): Images to analyze
- `max_tokens` (int): Maximum tokens in response (default: 1000)
- `temperature` (float): Response randomness (default: 0.1)

**Example:**
```python
request = VLMRequest(
    model="mistral-small-latest",
    messages=[{"role": "user", "content": "Analyze this image"}],
    images=[b"image_data"],
    max_tokens=1500,
    temperature=0.2
)
```

#### `VLMRaw`

Raw response from a VLM provider.

```python
@dataclass
class VLMRaw:
    content: str
    usage: Dict[str, Any]  # Token usage, cost, etc.
    latency_ms: float
    provider: str
    model: str
    timestamp: datetime = None
```

**Fields:**
- `content` (str): Raw response content
- `usage` (Dict[str, Any]): Token usage and cost information
- `latency_ms` (float): Response latency in milliseconds
- `provider` (str): Provider name (e.g., "mistral")
- `model` (str): Model name used
- `timestamp` (datetime, optional): Response timestamp

**Example:**
```python
response = VLMRaw(
    content='{"brand": "Apple", "confidence": 0.95}',
    usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
    latency_ms=1250.5,
    provider="mistral",
    model="mistral-small-latest",
    timestamp=datetime.now()
)
```

#### `Attributes`

Structured attributes extracted from images.

```python
@dataclass
class Attributes:
    data: Dict[str, Any]           # Schema-driven attributes
    confidences: Dict[str, float]  # Per-field confidence scores
    tags: set = None               # Quality tags
    notes: str = ""                # Additional notes
    lineage: Dict[str, Any] = None # Processing metadata
```

**Fields:**
- `data` (Dict[str, Any]): The actual attribute values
- `confidences` (Dict[str, float]): Confidence scores per field
- `tags` (set, optional): Quality classification tags
- `notes` (str): Additional notes or observations
- `lineage` (Dict[str, Any], optional): Processing metadata

**Example:**
```python
attributes = Attributes(
    data={
        "brand": "Apple",
        "model_or_type": "iPhone 13",
        "primary_colors": [{"name": "Blue", "confidence": 0.9}],
        "materials": [{"name": "Glass", "confidence": 0.8}],
        "condition": "Excellent"
    },
    confidences={
        "brand": 0.95,
        "model_or_type": 0.88,
        "primary_colors": 0.9,
        "materials": 0.8,
        "condition": 0.85
    },
    tags={"high_confidence", "clear_image"},
    notes="Item appears to be in excellent condition",
    lineage={"processing_time_ms": 1250, "provider": "mistral"}
)
```

#### `Decision`

Decision made about the quality and acceptance of attributes.

```python
@dataclass
class Decision:
    accepted: bool                 # Overall acceptance
    field_flags: Dict[str, str] = None  # Per-field status
    reasons: List[str] = None     # Rejection reasons
    confidence_score: float = 0.0 # Overall confidence
```

**Fields:**
- `accepted` (bool): Whether the item is accepted
- `field_flags` (Dict[str, str], optional): Field-specific status flags
- `reasons` (List[str], optional): Reasons for rejection
- `confidence_score` (float): Overall confidence score

**Example:**
```python
decision = Decision(
    accepted=True,
    field_flags={
        "brand": "accepted",
        "model_or_type": "accepted",
        "primary_colors": "low_confidence"
    },
    reasons=[],
    confidence_score=0.87
)
```

### Pipeline Results

#### `PipelineResult`

Result of a pipeline execution.

```python
@dataclass
class PipelineResult:
    item_id: str
    success: bool
    attributes: Optional[Attributes] = None
    raw_response: Optional[VLMRaw] = None
    decision: Optional[Decision] = None
    error: Optional[str] = None
    processing_time_ms: Optional[float] = None
    storage_ids: Optional[Dict[str, str]] = None
    timestamp: datetime = None
```

**Fields:**
- `item_id` (str): Item identifier
- `success` (bool): Whether processing succeeded
- `attributes` (Attributes, optional): Extracted attributes
- `raw_response` (VLMRaw, optional): Raw VLM response
- `decision` (Decision, optional): Quality decision
- `error` (str, optional): Error message if failed
- `processing_time_ms` (float, optional): Processing time
- `storage_ids` (Dict[str, str], optional): Storage identifiers
- `timestamp` (datetime, optional): Processing timestamp

## Core Classes

### `Config`

Configuration management class.

```python
class Config:
    def __init__(self, config_dict: Dict[str, Any])
    def from_file(cls, file_path: str) -> Config
    def get_threshold(self, field_name: str) -> float
    def get_provider_config(self, provider_name: str) -> Dict[str, Any]
    def get_storage_config(self) -> Dict[str, Any]
```

**Methods:**
- `from_file(file_path)`: Load configuration from YAML file
- `get_threshold(field_name)`: Get confidence threshold for field
- `get_provider_config(provider_name)`: Get provider-specific config
- `get_storage_config()`: Get storage configuration

### `PipelineService`

Main pipeline orchestration service.

```python
class PipelineService:
    def __init__(self, config: Config)
    def analyze_item(self, input_path: Union[str, Path]) -> PipelineResult
    def analyze_batch(self, input_paths: List[Union[str, Path]]) -> List[PipelineResult]
    def get_pipeline_status(self) -> Dict[str, Any]
```

**Methods:**
- `analyze_item(input_path)`: Analyze single item
- `analyze_batch(input_paths)`: Analyze multiple items
- `get_pipeline_status()`: Get pipeline status information

## Provider Interface

### `Provider`

Abstract base class for VLM providers.

```python
class Provider(ABC):
    def __init__(self, config: Dict[str, Any])
    def predict(self, request: VLMRequest) -> VLMRaw
    def get_available_models(self) -> List[str]
    def estimate_cost(self, request: VLMRequest) -> float
    @property
    def provider_name(self) -> str
    @property
    def max_images_per_request(self) -> int
    @property
    def max_tokens_per_request(self) -> int
```

**Methods:**
- `predict(request)`: Make prediction request
- `get_available_models()`: Get available models
- `estimate_cost(request)`: Estimate request cost
- `provider_name`: Provider identifier
- `max_images_per_request`: Image limit per request
- `max_tokens_per_request`: Token limit per request

## Storage Interface

### `StorageBackend`

Abstract base class for storage backends.

```python
class StorageBackend(ABC):
    def __init__(self, config: Optional[Dict[str, Any]] = None)
    def store_attributes(self, item_id: str, attributes: Attributes, 
                        metadata: Optional[Dict[str, Any]] = None) -> str
    def store_raw_response(self, item_id: str, raw_response: VLMRaw,
                          metadata: Optional[Dict[str, Any]] = None) -> str
    def store_lineage(self, item_id: str, lineage: Dict[str, Any],
                     metadata: Optional[Dict[str, Any]] = None) -> str
```

**Methods:**
- `store_attributes(item_id, attributes, metadata)`: Store attributes
- `store_raw_response(item_id, raw_response, metadata)`: Store raw response
- `store_lineage(item_id, lineage, metadata)`: Store processing lineage

## Exception Classes

### `VLMError`

Base exception for VLM-related errors.

```python
class VLMError(Exception):
    pass
```

### `ProviderError`

Provider-specific errors.

```python
class ProviderError(VLMError):
    pass

class ProviderConfigError(ProviderError):
    pass

class ProviderAPIError(ProviderError):
    pass

class ProviderRateLimitError(ProviderAPIError):
    pass

class ProviderTimeoutError(ProviderAPIError):
    pass
```

### `PipelineError`

Pipeline processing errors.

```python
class PipelineError(Exception):
    pass
```

### `ConfigurationError`

Configuration-related errors.

```python
class ConfigurationError(Exception):
    pass
```

### `StorageError`

Storage-related errors.

```python
class StorageError(ResourceError):
    pass
```

## Usage Examples

### Basic Pipeline Usage

```python
from vis2attr.core.config import Config
from vis2attr.pipeline.service import PipelineService

# Load configuration
config = Config.from_file("config/project.yaml")

# Initialize pipeline
pipeline = PipelineService(config)

# Analyze single item
result = pipeline.analyze_item("./item.jpg")

if result.success:
    print(f"Item {result.item_id} processed successfully")
    print(f"Attributes: {result.attributes.data}")
    print(f"Confidence: {result.decision.confidence_score}")
else:
    print(f"Processing failed: {result.error}")
```

### Batch Processing

```python
# Analyze multiple items
input_paths = ["./item1.jpg", "./item2.jpg", "./item3.jpg"]
results = pipeline.analyze_batch(input_paths)

# Process results
successful = [r for r in results if r.success]
failed = [r for r in results if not r.success]

print(f"Successful: {len(successful)}")
print(f"Failed: {len(failed)}")

for result in successful:
    print(f"{result.item_id}: {result.attributes.data['brand']}")
```

### Custom Provider Usage

```python
from vis2attr.providers.factory import create_provider

# Create provider
provider_config = {
    "model": "mistral-small-latest",
    "max_tokens": 1000,
    "temperature": 0.1
}
provider = create_provider("mistral", provider_config)

# Make request
request = VLMRequest(
    model="mistral-small-latest",
    messages=[{"role": "user", "content": "Analyze this image"}],
    images=[b"image_data"]
)

response = provider.predict(request)
print(f"Response: {response.content}")
```

### Storage Usage

```python
from vis2attr.storage.factory import create_storage_backend

# Create storage backend
storage_config = {"file_path": "./custom.parquet"}
storage = create_storage_backend("parquet", storage_config)

# Store attributes
storage_id = storage.store_attributes(
    item_id="item_001",
    attributes=attributes,
    metadata={"source": "api"}
)

print(f"Stored with ID: {storage_id}")
```

## Type Hints

All classes and methods include comprehensive type hints for better IDE support and static analysis.

```python
from typing import Dict, List, Optional, Union, Any
from pathlib import Path
from datetime import datetime
```

## Serialization

Data models support JSON serialization for API integration:

```python
import json

# Serialize to JSON
result_dict = {
    "item_id": result.item_id,
    "success": result.success,
    "attributes": result.attributes.__dict__ if result.attributes else None,
    "decision": result.decision.__dict__ if result.decision else None,
    "processing_time_ms": result.processing_time_ms
}

json_str = json.dumps(result_dict, indent=2)
```

## Validation

Data models include validation for:

- **Required Fields**: All mandatory fields present
- **Data Types**: Correct types for each field
- **Value Ranges**: Confidence scores between 0.0 and 1.0
- **Schema Compliance**: Attributes match defined schema
- **Provider Limits**: Requests within provider constraints
