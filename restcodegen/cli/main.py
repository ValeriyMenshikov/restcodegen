import click

from restcodegen.generator.parser import Parser
from restcodegen.generator.rest_codegen import RESTClientGenerator
from restcodegen.generator.utils import format_file


@click.group()
def cli() -> None: ...


@click.command("generate")
@click.option(
    "--url",
    "-u",
    required=True,
    type=str,
    help="OpenAPI spec URL",
)
@click.option(
    "--service-name",
    "-s",
    required=True,
    type=str,
    help="service name",
)
@click.option(
    "--async-mode",
    "-a",
    required=False,
    type=bool,
    help="Async mode",
    default=False,
)
@click.option(
    "--api-tags",
    "-t",
    required=False,
    type=str,
    help="Api tags for generate clients only for selected tags (comma-separated)",
    default=None,
)
@click.option(
    "--templates-dir",
    "-td",
    required=False,
    type=click.Path(exists=True, dir_okay=True, file_okay=False),
    help="Path to custom API client template",
    default=None,
)
def generate_command(
    url: str, service_name: str, async_mode: bool, api_tags: str | None, templates_dir: str | None
) -> None:
    parser = Parser(
        openapi_spec=url,
        service_name=service_name,
        selected_tags=api_tags.split(",") if api_tags else None,
    )
    gen = RESTClientGenerator(
        openapi_spec=parser,
        async_mode=async_mode,
        templates_dir=templates_dir,
    )
    gen.generate()
    format_file()


cli.add_command(generate_command)

if __name__ == "__main__":
    cli()
