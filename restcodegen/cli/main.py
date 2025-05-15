"""Command-line interface for the REST code generator."""

import click

from restcodegen.generator.parser import OpenAPISpec
from restcodegen.generator.rest_codegen import RESTClientGenerator
from restcodegen.generator.utils import format_file
from restcodegen.generator.log import LOGGER


@click.group()
def cli() -> None:
    """REST API client code generator CLI."""
    pass


@click.command("generate")
@click.option(
    "--url",
    "-u",
    required=True,
    type=str,
    help="OpenAPI spec URL or file path",
)
@click.option(
    "--service-name",
    "-s",
    required=True,
    type=str,
    help="Service name for generated client",
)
@click.option(
    "--async-mode",
    "-a",
    is_flag=True,
    help="Generate async client code",
    default=False,
)
@click.option(
    "--api-tags",
    "-t",
    required=False,
    type=str,
    help="API tags to generate clients for (comma-separated)",
    default=None,
)
def generate_command(
    url: str, service_name: str, async_mode: bool, api_tags: str | None
) -> None:
    """Generate REST API client code from OpenAPI specification.
    
    Args:
        url: URL or file path to OpenAPI specification
        service_name: Name of the service for the generated client
        async_mode: Whether to generate async client code
        api_tags: Comma-separated list of API tags to include
    """
    try:
        # Parse API tags if provided
        parsed_tags = _parse_api_tags(api_tags)
        
        # Parse OpenAPI specification
        LOGGER.info(f"Parsing OpenAPI specification from: {url}")
        parser = OpenAPISpec(
            openapi_spec=url,
            service_name=service_name,
            api_tags=parsed_tags,
        )
        
        # Generate client code
        LOGGER.info(f"Generating client for service: {service_name}")
        gen = RESTClientGenerator(openapi_spec=parser, async_mode=async_mode)
        gen.generate()
        
        # Format generated code
        LOGGER.info("Formatting generated code")
        format_file()
        
        LOGGER.info(f"Successfully generated client for service: {service_name}")
    except Exception as e:
        LOGGER.error(f"Error generating client: {str(e)}")
        raise click.ClickException(str(e))


def _parse_api_tags(api_tags: str | None) -> list[str] | None:
    """Parse comma-separated API tags string into a list.
    
    Args:
        api_tags: Comma-separated string of API tags
        
    Returns:
        List of API tags or None if not provided
    """
    if not api_tags:
        return None
    
    return [tag.strip() for tag in api_tags.split(",") if tag.strip()]


# Register commands
cli.add_command(generate_command)


if __name__ == "__main__":
    cli()
