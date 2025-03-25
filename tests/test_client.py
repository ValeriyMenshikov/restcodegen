from clients.http.petstore.apis.pet_api import PetApi
from clients.http.petstore.models.api_models import Pet, Category, Status1
from restcodegen.restclient import Client, Configuration
import pytest

import structlog

structlog.configure(
    processors=[
        structlog.processors.JSONRenderer(
            indent=4,
            ensure_ascii=True,
        )
    ]
)


@pytest.fixture
def client() -> PetApi:
    configuration = Configuration(
        base_url="https://petstore3.swagger.io/api/v3", disable_log=False
    )
    client = Client(configuration=configuration)
    return PetApi(client)


def test_get_pet_pet_id(client: PetApi) -> None:
    client.get_pet_pet_id(pet_id=1)


def test_post_pet(client: PetApi) -> None:
    client.post_pet(
        pet=Pet(
            id=10,
            name="test",
            photoUrls=["string"],
            category=Category(id=1, name="Dogs"),
            status=Status1.AVAILABLE,
        )
    )
