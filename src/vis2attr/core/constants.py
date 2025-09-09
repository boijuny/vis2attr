"""Constants and configuration defaults for the vis2attr pipeline.

This module centralizes all magic numbers and hardcoded values to improve
maintainability and reduce configuration drift across the codebase.
"""

from typing import Dict, List

# =============================================================================
# IMAGE PROCESSING CONSTANTS
# =============================================================================

# Default maximum image resolution (width or height in pixels)
DEFAULT_MAX_RESOLUTION = 768

# Default maximum number of images to process per item
DEFAULT_MAX_IMAGES_PER_ITEM = 3

# Supported image formats
DEFAULT_SUPPORTED_FORMATS = [".jpg", ".jpeg", ".png", ".webp"]


# =============================================================================
# VLM PROVIDER CONSTANTS
# =============================================================================

# Default maximum tokens for VLM requests
DEFAULT_MAX_TOKENS = 1000

# Default temperature for VLM requests (controls randomness)
DEFAULT_TEMPERATURE = 0.1

# Conservative token limit estimate for Mistral models
MISTRAL_MAX_TOKENS_ESTIMATE = 32000

# Model cost per 1K tokens (USD)
MISTRAL_MODEL_COSTS = {
    "pixtral-12b-latest": 0.0003,
    "pixtral-large-latest": 0.0006,
    "mistral-medium-latest": 0.0004,
    "mistral-small-latest": 0.0002,
}

# Default cost per 1K tokens for unknown models
DEFAULT_COST_PER_1K_TOKENS = 0.0003


# =============================================================================
# CONFIDENCE & THRESHOLD CONSTANTS
# =============================================================================

# Default confidence threshold for acceptance decisions
DEFAULT_CONFIDENCE_THRESHOLD = 0.75

# Field-specific confidence thresholds
DEFAULT_FIELD_THRESHOLDS: Dict[str, float] = {
    "default": 0.75,
    "brand": 0.80,
    "model_or_type": 0.70,
    "primary_colors": 0.65,
    "materials": 0.70,
    "condition": 0.75,
}


# =============================================================================
# TIME & PERFORMANCE CONSTANTS
# =============================================================================

# Conversion factor from seconds to milliseconds
SECONDS_TO_MILLISECONDS = 1000

# Default timeout for network requests (seconds)
DEFAULT_TIMEOUT_SECONDS = 30

# Default connection pool size for HTTP clients
DEFAULT_CONNECTION_POOL_SIZE = 10


# =============================================================================
# STORAGE & I/O CONSTANTS
# =============================================================================

# Default storage root directory
DEFAULT_STORAGE_ROOT = "./storage"

# Default backup settings
DEFAULT_BACKUP_ENABLED = False

# Default directory creation behavior
DEFAULT_CREATE_DIRS = True


# =============================================================================
# LOGGING & METRICS CONSTANTS
# =============================================================================

# Default log level
DEFAULT_LOG_LEVEL = "INFO"

# Default metrics enablement
DEFAULT_ENABLE_METRICS = True

# Default structured logging
DEFAULT_STRUCTURED_LOGGING = True


# =============================================================================
# SECURITY CONSTANTS
# =============================================================================

# Default EXIF stripping behavior
DEFAULT_STRIP_EXIF = True

# Default PII avoidance behavior
DEFAULT_AVOID_PII = True

# Default temporary file cleanup behavior
DEFAULT_TEMP_FILE_CLEANUP = True


# =============================================================================
# VALIDATION CONSTANTS
# =============================================================================

# Minimum confidence score (0.0 - 1.0)
MIN_CONFIDENCE_SCORE = 0.0

# Maximum confidence score (0.0 - 1.0) 
MAX_CONFIDENCE_SCORE = 1.0

# Minimum temperature value for VLM requests
MIN_TEMPERATURE = 0.0

# Maximum temperature value for VLM requests
MAX_TEMPERATURE = 2.0

# Minimum resolution for image processing
MIN_RESOLUTION = 32

# Maximum reasonable resolution for image processing
MAX_RESOLUTION = 4096

# Minimum images per item
MIN_IMAGES_PER_ITEM = 1

# Maximum reasonable images per item
MAX_IMAGES_PER_ITEM = 10


# =============================================================================
# CONFIGURATION PATHS
# =============================================================================

# Default configuration file paths (relative to project root)
DEFAULT_CONFIG_PATH = "config/project.yaml"
DEFAULT_SCHEMA_PATH = "config/schemas/default.yaml"
DEFAULT_PROMPT_TEMPLATE = "config/prompts/default.jinja"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def validate_confidence(confidence: float) -> float:
    """Validate and clamp confidence score to valid range."""
    return max(MIN_CONFIDENCE_SCORE, min(MAX_CONFIDENCE_SCORE, confidence))


def validate_temperature(temperature: float) -> float:
    """Validate and clamp temperature to valid range."""
    return max(MIN_TEMPERATURE, min(MAX_TEMPERATURE, temperature))


def validate_resolution(resolution: int) -> int:
    """Validate and clamp resolution to reasonable range."""
    return max(MIN_RESOLUTION, min(MAX_RESOLUTION, resolution))


def validate_images_per_item(count: int) -> int:
    """Validate and clamp images per item to reasonable range."""
    return max(MIN_IMAGES_PER_ITEM, min(MAX_IMAGES_PER_ITEM, count))


# =============================================================================
# CONFIGURATION DEFAULTS
# =============================================================================

# Complete default configuration for fallback scenarios
DEFAULT_CONFIG = {
    "io": {
        "max_images_per_item": DEFAULT_MAX_IMAGES_PER_ITEM,
        "max_resolution": DEFAULT_MAX_RESOLUTION,
        "supported_formats": DEFAULT_SUPPORTED_FORMATS,
    },
    "thresholds": DEFAULT_FIELD_THRESHOLDS.copy(),
    "providers": {
        "mistral": {
            "max_tokens": DEFAULT_MAX_TOKENS,
            "temperature": DEFAULT_TEMPERATURE,
        },
        "openai": {
            "max_tokens": DEFAULT_MAX_TOKENS,
            "temperature": DEFAULT_TEMPERATURE,
        },
        "google": {
            "max_tokens": DEFAULT_MAX_TOKENS,
            "temperature": DEFAULT_TEMPERATURE,
        },
        "anthropic": {
            "max_tokens": DEFAULT_MAX_TOKENS,
            "temperature": DEFAULT_TEMPERATURE,
        },
    },
    "metrics": {
        "enable_metrics": DEFAULT_ENABLE_METRICS,
        "log_level": DEFAULT_LOG_LEVEL,
        "structured_logging": DEFAULT_STRUCTURED_LOGGING,
    },
    "security": {
        "strip_exif": DEFAULT_STRIP_EXIF,
        "avoid_pii": DEFAULT_AVOID_PII,
        "temp_file_cleanup": DEFAULT_TEMP_FILE_CLEANUP,
    },
    "storage_config": {
        "storage_root": DEFAULT_STORAGE_ROOT,
        "create_dirs": DEFAULT_CREATE_DIRS,
        "backup_enabled": DEFAULT_BACKUP_ENABLED,
    },
}
