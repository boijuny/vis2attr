"""CLI command for analyzing images and extracting attributes."""

import click
import logging
import pandas as pd
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from ..core.config import Config
from ..pipeline.service import PipelineService, PipelineError


@click.command()
@click.option(
    "--input", "-i",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Input file or directory. If directory, processes each file separately (use --batch for subdirectories)"
)
@click.option(
    "--config", "-c",
    type=click.Path(exists=True, path_type=Path),
    default="config/project.yaml",
    help="Path to configuration file"
)
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    default="predictions.parquet",
    help="Output file path for predictions"
)
@click.option(
    "--schema",
    type=str,
    help="Override schema path from config"
)
@click.option(
    "--provider",
    type=click.Choice(["openai", "google", "anthropic", "mistral"]),
    help="Override provider from config"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose logging"
)
@click.option(
    "--batch",
    is_flag=True,
    help="Process each subdirectory as separate items (only when input is a directory)"
)
def analyze_command(
    input: Path,
    config: Path,
    output: Path,
    schema: Optional[str],
    provider: Optional[str],
    verbose: bool,
    batch: bool
):
    """Analyze images and extract structured attributes.
    
    This command processes images through the vis2attr pipeline to extract
    structured attributes like brand, colors, materials, and condition.
    """
    # Set up logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Load configuration
        click.echo(f"Loading configuration from: {config}")
        pipeline_config = Config.from_file(str(config))
        
        # Apply overrides
        if schema:
            pipeline_config.schema_path = schema
            click.echo(f"Using schema: {schema}")
        if provider:
            pipeline_config.provider = f"providers.{provider}"
            click.echo(f"Using provider: {provider}")
        
        # Initialize pipeline
        click.echo("Initializing pipeline...")
        pipeline = PipelineService(pipeline_config)
        
        # Determine input processing strategy
        if input.is_file():
            # Process single file
            input_paths = [input]
            click.echo(f"Processing single file: {input}")
        elif input.is_dir():
            if batch:
                # Process each subdirectory as a separate item
                input_paths = [d for d in input.iterdir() if d.is_dir()]
                if not input_paths:
                    click.echo("No subdirectories found for batch processing")
                    return
                click.echo(f"Batch processing {len(input_paths)} directories")
            else:
                # Process each file in directory as a separate item
                input_paths = [f for f in input.iterdir() if f.is_file()]
                if not input_paths:
                    click.echo("No files found in directory")
                    return
                click.echo(f"Processing {len(input_paths)} files as separate items")
        else:
            click.echo(f"Invalid input path: {input}")
            return
        
        # Run analysis
        click.echo("Starting analysis...")
        results = pipeline.analyze_batch(input_paths)
        
        # Process results
        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]
        
        click.echo(f"\nAnalysis completed:")
        click.echo(f"  ✅ Successful: {len(successful_results)}")
        click.echo(f"  ❌ Failed: {len(failed_results)}")
        
        if failed_results:
            click.echo("\nFailed items:")
            for result in failed_results:
                click.echo(f"  - {result.item_id}: {result.error}")
        
        # Save results to output file
        if successful_results:
            click.echo(f"\nSaving results to: {output}")
            _save_results_to_parquet(successful_results, output)
            click.echo("Results saved successfully!")
        
        # Show summary statistics
        if successful_results:
            _show_summary_stats(successful_results)
        
    except PipelineError as e:
        click.echo(f"❌ Pipeline error: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        if verbose:
            import traceback
            click.echo(traceback.format_exc(), err=True)
        raise click.Abort()


def _save_results_to_parquet(results: List, output_path: Path) -> None:
    """Save analysis results to a Parquet file.
    
    Args:
        results: List of successful PipelineResult objects
        output_path: Path to save the Parquet file
    """
    # Prepare data for DataFrame
    data = []
    for result in results:
        row = {
            'item_id': result.item_id,
            'timestamp': result.timestamp.isoformat(),
            'processing_time_ms': result.processing_time_ms,
            'success': result.success,
            'decision_accepted': result.decision.accepted if result.decision else False,
            'confidence_score': result.decision.confidence_score if result.decision else None,
        }
        
        # Add attribute data
        if result.attributes:
            for field, value in result.attributes.data.items():
                row[f'attr_{field}'] = value
                if field in result.attributes.confidences:
                    row[f'conf_{field}'] = result.attributes.confidences[field]
        
        # Add decision details
        if result.decision:
            row['decision_reasons'] = '; '.join(result.decision.reasons) if result.decision.reasons else None
            row['field_flags'] = str(result.decision.field_flags) if result.decision.field_flags else None
        
        data.append(row)
    
    # Create DataFrame and save
    df = pd.DataFrame(data)
    df.to_parquet(output_path, index=False)


def _show_summary_stats(results: List) -> None:
    """Show summary statistics for the analysis results.
    
    Args:
        results: List of successful PipelineResult objects
    """
    click.echo("\n📊 Summary Statistics:")
    
    # Basic stats
    total_items = len(results)
    accepted_items = sum(1 for r in results if r.decision and r.decision.accepted)
    avg_processing_time = sum(r.processing_time_ms for r in results) / total_items if total_items > 0 else 0
    
    click.echo(f"  Total items processed: {total_items}")
    acceptance_rate = (accepted_items/total_items*100) if total_items > 0 else 0
    click.echo(f"  Items accepted: {accepted_items} ({acceptance_rate:.1f}%)")
    click.echo(f"  Average processing time: {avg_processing_time:.1f}ms")
    
    # Confidence statistics
    if any(r.decision for r in results):
        confidences = [r.decision.confidence_score for r in results if r.decision]
        if confidences:
            avg_confidence = sum(confidences) / len(confidences)
            min_confidence = min(confidences)
            max_confidence = max(confidences)
            click.echo(f"  Average confidence: {avg_confidence:.3f}")
            click.echo(f"  Confidence range: {min_confidence:.3f} - {max_confidence:.3f}")
    
    # Provider stats
    providers = {}
    for result in results:
        if result.raw_response:
            provider = result.raw_response.provider
            providers[provider] = providers.get(provider, 0) + 1
    
    if providers:
        click.echo(f"  Provider usage: {dict(providers)}")
