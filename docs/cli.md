# CLI Reference

## Overview

vis2attr provides a command-line interface for analyzing images and extracting structured attributes. The CLI supports both single-file and batch processing with comprehensive configuration options.

## Commands

### `vis2attr analyze`

Analyze images and extract structured attributes using Visual Language Models.

#### Usage

```bash
vis2attr analyze [OPTIONS]
```

#### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--input` | `-i` | PATH | Required | Input file or directory |
| `--config` | `-c` | PATH | `config/project.yaml` | Configuration file path |
| `--output` | `-o` | PATH | `predictions.parquet` | Output file path |
| `--schema` | | TEXT | | Override schema path from config |
| `--provider` | | CHOICE | | Override provider (openai, google, anthropic, mistral) |
| `--verbose` | `-v` | FLAG | False | Enable verbose logging |
| `--batch` | | FLAG | False | Process subdirectories as separate items |
| `--help` | | FLAG | | Show help message |

#### Examples

**Single File Analysis**
```bash
# Basic analysis
vis2attr analyze --input ./item.jpg

# With custom output
vis2attr analyze --input ./item.jpg --output ./result.parquet

# With verbose logging
vis2attr analyze --input ./item.jpg --verbose
```

**Directory Processing**
```bash
# Process each file in directory as separate item
vis2attr analyze --input ./images

# Process each subdirectory as separate item (batch mode)
vis2attr analyze --input ./items --batch

# Batch processing with verbose output
vis2attr analyze --input ./items --batch --verbose
```

**Custom Configuration**
```bash
# Use custom configuration file
vis2attr analyze --input ./images --config ./my-config.yaml

# Override provider
vis2attr analyze --input ./images --provider mistral

# Override schema
vis2attr analyze --input ./images --schema ./custom-schema.yaml
```

**Combined Options**
```bash
# Full example with all options
vis2attr analyze \
  --input ./items \
  --batch \
  --config ./production-config.yaml \
  --output ./results.parquet \
  --provider mistral \
  --verbose
```

#### Input Processing

**Single File Mode**
- Processes one image file
- Generates single result
- Suitable for individual item analysis

**Directory Mode (default)**
- Processes each file in directory separately
- Each file becomes a separate item
- Suitable for bulk processing

**Batch Mode (`--batch`)**
- Processes each subdirectory as separate item
- Combines all images in subdirectory
- Suitable for multi-image item analysis

#### Output Format

The analyze command outputs a Parquet file with the following columns:

| Column | Type | Description |
|--------|------|-------------|
| `item_id` | string | Unique item identifier |
| `timestamp` | string | Processing timestamp (ISO format) |
| `processing_time_ms` | float | Processing time in milliseconds |
| `success` | boolean | Whether processing succeeded |
| `decision_accepted` | boolean | Whether item was accepted |
| `confidence_score` | float | Overall confidence score |
| `attr_*` | various | Attribute values (schema-dependent) |
| `conf_*` | float | Confidence scores per field |
| `decision_reasons` | string | Rejection reasons (if any) |
| `field_flags` | string | Field-level status flags |

#### Error Handling

- **File not found**: Clear error message with file path
- **Invalid format**: Lists supported formats
- **Provider errors**: Shows API error details
- **Configuration errors**: Validates config file syntax
- **Processing errors**: Logs detailed error information

### `vis2attr report`

Generate reports from prediction results.

#### Usage

```bash
vis2attr report [OPTIONS]
```

#### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--predictions` | `-p` | PATH | Required | Path to predictions file |
| `--output` | `-o` | PATH | stdout | Output file path |
| `--format` | | CHOICE | `summary` | Report format (json, yaml, table, summary) |
| `--threshold` | | FLOAT | | Confidence threshold for quality metrics |
| `--help` | | FLAG | | Show help message |

#### Examples

**Summary Report (default)**
```bash
# Generate summary to stdout
vis2attr report --predictions ./predictions.parquet

# Save summary to file
vis2attr report --predictions ./results.parquet --output ./report.txt
```

**Detailed Reports**
```bash
# JSON format
vis2attr report --predictions ./results.parquet --format json --output ./report.json

# YAML format
vis2attr report --predictions ./results.parquet --format yaml --output ./report.yaml

# Table format
vis2attr report --predictions ./results.parquet --format table --output ./report.txt
```

**Quality Analysis**
```bash
# Filter by confidence threshold
vis2attr report --predictions ./results.parquet --threshold 0.8

# Generate quality report
vis2attr report --predictions ./results.parquet --format summary --threshold 0.75
```

#### Report Formats

**Summary Format** (default)
- Processing statistics
- Success/failure rates
- Confidence distributions
- Provider usage
- Performance metrics

**JSON Format**
- Machine-readable output
- Complete data structure
- Suitable for API integration

**YAML Format**
- Human-readable structure
- Easy to parse programmatically
- Good for configuration files

**Table Format**
- Tabular data presentation
- Suitable for spreadsheet import
- Row per item analysis

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `MISTRAL_API_KEY` | Mistral API key for VLM calls | Yes (for Mistral) |
| `OPENAI_API_KEY` | OpenAI API key | No (for OpenAI) |
| `GOOGLE_API_KEY` | Google API key | No (for Google) |
| `ANTHROPIC_API_KEY` | Anthropic API key | No (for Anthropic) |

## Configuration Files

The CLI uses YAML configuration files. See [Configuration](configuration.md) for detailed configuration options.

**Default Configuration**: `config/project.yaml`

**Configuration Override Order**:
1. Command-line options
2. Custom config file (`--config`)
3. Default config file (`config/project.yaml`)

## Logging

### Log Levels

- **INFO**: Basic processing information
- **DEBUG**: Detailed processing steps (with `--verbose`)
- **WARNING**: Non-fatal issues
- **ERROR**: Processing failures

### Log Format

```
2024-01-15 10:30:45 - vis2attr.pipeline.service - INFO - Starting analysis for: ./item.jpg
2024-01-15 10:30:45 - vis2attr.pipeline.service - DEBUG - Step 1: Ingesting images
2024-01-15 10:30:46 - vis2attr.pipeline.service - INFO - Loaded item item_001 with 1 images
```

### Verbose Mode

Enable with `--verbose` flag for detailed logging:
- Step-by-step processing
- Provider request/response details
- Configuration loading
- Storage operations
- Performance metrics

## Exit Codes

| Code | Description |
|------|-------------|
| 0 | Success |
| 1 | General error |
| 2 | Configuration error |
| 3 | Input validation error |
| 4 | Provider error |
| 5 | Storage error |

## Performance Tips

1. **Batch Processing**: Use `--batch` for multi-image items
2. **Parallel Processing**: Process multiple directories in parallel
3. **Configuration**: Optimize provider settings for your use case
4. **Storage**: Use SSD storage for better I/O performance
5. **Memory**: Ensure sufficient RAM for large images

## Troubleshooting

### Common Issues

**"Provider not found"**
- Check provider name spelling
- Ensure provider is implemented
- Verify configuration

**"API key not found"**
- Set required environment variable
- Check API key validity
- Verify provider configuration

**"Schema validation failed"**
- Check schema file syntax
- Verify field definitions
- Ensure schema matches data

**"Storage error"**
- Check write permissions
- Verify disk space
- Ensure valid output path

### Debug Mode

Use `--verbose` flag for detailed error information:
```bash
vis2attr analyze --input ./images --verbose
```

This will show:
- Detailed error messages
- Stack traces
- Configuration values
- Processing steps
