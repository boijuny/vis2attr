# Configuration

## Overview

vis2attr uses YAML-based configuration files to define pipeline behavior, schema structure, and provider settings. The configuration system is designed to be flexible and schema-driven, allowing customization without code changes.

## Configuration File

**Default Location**: `config/project.yaml`

**Custom Location**: Specify with `--config` CLI option

## Configuration Structure

### Pipeline Components

```yaml
# Core pipeline components
ingestor: ingest.fs                    # Image ingestion method
provider: providers.mistral           # VLM provider
storage: storage.files                # Storage backend

# Schema and prompts
schema_path: config/schemas/default.yaml
prompt_template: config/prompts/default.jinja
```

### Storage Configuration

```yaml
storage_config:
  storage_root: "./storage"           # Storage directory
  create_dirs: true                   # Create directories if missing
  backup_enabled: false               # Enable backup functionality
```

### Decision Thresholds

```yaml
thresholds:
  default: 0.75                       # Default confidence threshold
  brand: 0.80                         # Brand-specific threshold
  model_or_type: 0.70                 # Model/type threshold
  primary_colors: 0.65                # Color threshold
  materials: 0.70                     # Materials threshold
  condition: 0.75                     # Condition threshold
```

### I/O Settings

```yaml
io:
  max_images_per_item: 3              # Maximum images per item
  max_resolution: 768                 # Maximum image resolution
  supported_formats:                  # Supported image formats
    - ".jpg"
    - ".jpeg"
    - ".png"
    - ".webp"
```

### Provider Settings

```yaml
providers:
  mistral:
    model: "mistral-small-latest"     # Mistral model
    max_tokens: 1000                  # Maximum tokens
    temperature: 0.1                  # Response temperature
    
  openai:
    model: "gpt-4-vision-preview"     # OpenAI model
    max_tokens: 1000
    temperature: 0.1
    
  google:
    model: "gemini-pro-vision"        # Google model
    max_tokens: 1000
    temperature: 0.1
    
  anthropic:
    model: "claude-3-vision"          # Anthropic model
    max_tokens: 1000
    temperature: 0.1
```

### Metrics and Logging

```yaml
metrics:
  enable_metrics: true                # Enable metrics collection
  log_level: "INFO"                  # Logging level
  structured_logging: true           # Use structured logging
```

### Security Settings

```yaml
security:
  strip_exif: true                    # Remove EXIF data
  avoid_pii: true                     # Avoid PII in processing
  temp_file_cleanup: true            # Clean up temporary files
```

## Schema Configuration

### Schema File Location

**Default**: `config/schemas/default.yaml`

**Custom**: Override with `--schema` CLI option

### Schema Structure

```yaml
# Default schema for item attribute extraction
brand:
  value: null
  confidence: 0.0

model_or_type:
  value: null
  confidence: 0.0

primary_colors:
  - name: ""
    confidence: 0.0

materials:
  - name: ""
    confidence: 0.0

condition:
  value: null
  confidence: 0.0

notes: ""
```

### Custom Schemas

You can create custom schemas for different use cases:

```yaml
# Example: Electronics schema
brand:
  value: null
  confidence: 0.0

model:
  value: null
  confidence: 0.0

category:
  value: null
  confidence: 0.0

condition:
  value: null
  confidence: 0.0

accessories:
  - name: ""
    confidence: 0.0

warranty_status:
  value: null
  confidence: 0.0

notes: ""
```

### Schema Validation

- **Required Fields**: All fields must be present
- **Confidence Scores**: Must be between 0.0 and 1.0
- **Data Types**: Values must match expected types
- **Nested Structures**: Arrays and objects supported

## Prompt Templates

### Template Location

**Default**: `config/prompts/default.jinja`

**Custom**: Override in configuration

### Template Variables

```jinja2
{# Available template variables #}
{{ schema }}          {# Schema definition #}
{{ item_id }}         {# Item identifier #}
{{ images }}          {# Image data #}
{{ meta }}            {# Item metadata #}
```

### Example Template

```jinja2
You are an expert at analyzing product images and extracting structured attributes.

Please analyze the following image(s) and extract the requested attributes according to the schema:

Schema: {{ schema | tojson }}

{% if images %}
Images: {{ images | length }} image(s) provided
{% endif %}

{% if meta %}
Metadata: {{ meta | tojson }}
{% endif %}

Please respond with a JSON object that matches the schema exactly, including confidence scores for each field.
```

## Environment Variables

### Required Variables

| Variable | Provider | Description |
|----------|----------|-------------|
| `MISTRAL_API_KEY` | Mistral | Mistral API key |

### Optional Variables

| Variable | Provider | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | OpenAI | OpenAI API key |
| `GOOGLE_API_KEY` | Google | Google API key |
| `ANTHROPIC_API_KEY` | Anthropic | Anthropic API key |

### Configuration Override

Environment variables can override configuration values:

```bash
# Override log level
export VIS2ATTR_LOG_LEVEL=DEBUG

# Override storage root
export VIS2ATTR_STORAGE_ROOT=/custom/storage
```

## Configuration Validation

### Schema Validation

The configuration system validates:

- **File Format**: Valid YAML syntax
- **Required Fields**: All mandatory fields present
- **Data Types**: Correct types for each field
- **Value Ranges**: Thresholds between 0.0 and 1.0
- **File Paths**: Existing files and directories

### Validation Errors

Common validation errors and solutions:

**"Invalid YAML syntax"**
- Check indentation (use spaces, not tabs)
- Verify quotes around strings
- Ensure proper list formatting

**"Missing required field"**
- Add missing configuration sections
- Check field names for typos
- Verify required provider settings

**"Invalid threshold value"**
- Ensure thresholds are between 0.0 and 1.0
- Use decimal format (0.75, not 75%)
- Check for proper number formatting

**"File not found"**
- Verify file paths are correct
- Check relative vs absolute paths
- Ensure files exist in specified locations

## Configuration Examples

### Development Configuration

```yaml
# config/dev.yaml
ingestor: ingest.fs
provider: providers.mistral
storage: storage.files

schema_path: config/schemas/default.yaml
prompt_template: config/prompts/default.jinja

thresholds:
  default: 0.6  # Lower threshold for development
  brand: 0.7
  model_or_type: 0.6
  primary_colors: 0.5
  materials: 0.6
  condition: 0.6

io:
  max_images_per_item: 5  # More images for testing
  max_resolution: 1024    # Higher resolution
  supported_formats: [".jpg", ".jpeg", ".png", ".webp"]

providers:
  mistral:
    model: "mistral-small-latest"
    max_tokens: 2000  # More tokens for development
    temperature: 0.2  # Higher temperature for variety

metrics:
  enable_metrics: true
  log_level: "DEBUG"  # Verbose logging
  structured_logging: true

security:
  strip_exif: true
  avoid_pii: true
  temp_file_cleanup: true
```

### Production Configuration

```yaml
# config/prod.yaml
ingestor: ingest.fs
provider: providers.mistral
storage: storage.files

schema_path: config/schemas/default.yaml
prompt_template: config/prompts/default.jinja

thresholds:
  default: 0.8  # Higher threshold for production
  brand: 0.85
  model_or_type: 0.8
  primary_colors: 0.75
  materials: 0.8
  condition: 0.85

io:
  max_images_per_item: 3
  max_resolution: 768
  supported_formats: [".jpg", ".jpeg", ".png", ".webp"]

providers:
  mistral:
    model: "mistral-small-latest"
    max_tokens: 1000
    temperature: 0.1  # Lower temperature for consistency

metrics:
  enable_metrics: true
  log_level: "INFO"
  structured_logging: true

security:
  strip_exif: true
  avoid_pii: true
  temp_file_cleanup: true
```

## Best Practices

### Configuration Management

1. **Version Control**: Keep configs in version control
2. **Environment Separation**: Use different configs for dev/prod
3. **Sensitive Data**: Never commit API keys
4. **Documentation**: Document custom configurations
5. **Validation**: Test configurations before deployment

### Performance Tuning

1. **Image Resolution**: Balance quality vs performance
2. **Token Limits**: Optimize for your use case
3. **Batch Size**: Adjust based on memory constraints
4. **Thresholds**: Tune for your quality requirements
5. **Caching**: Enable caching where appropriate

### Security Considerations

1. **EXIF Stripping**: Always enabled in production
2. **API Keys**: Use environment variables
3. **File Permissions**: Restrict access to config files
4. **Audit Logging**: Enable for compliance
5. **Data Retention**: Configure appropriate retention policies
