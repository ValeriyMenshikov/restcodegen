import click

from restcodegen.generator.parser import OpenAPISpec
from restcodegen.generator.rest_codegen import RESTClientGenerator
from restcodegen.generator.utils import format_file


@click.group()
def cli() -> None: ...


@click.command("generate")
@click.option("--url", "-u", required=True, help="OpenAPI spec URL")
@click.option("--service-name", "-s", required=True, help="service name")
@click.option("--async-mode", "-a", required=False, help="Async mode", default=False)
def generate_command(url: str, service_name: str, async_mode: bool) -> None:
    parser = OpenAPISpec(openapi_spec=url, service_name=service_name)
    gen = RESTClientGenerator(openapi_spec=parser, async_mode=async_mode)
    gen.generate()
    format_file()


cli.add_command(generate_command)

if __name__ == "__main__":
    cli()
