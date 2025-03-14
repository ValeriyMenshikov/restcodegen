# RestCodeGen

RestCodeGen is a tool for generating Python clients based on OpenAPI 3 specifications.   
This tool enables testers to quickly create client libraries for interacting with REST APIs implemented with OpenAPI.

## Installation

To install, you need the required dependencies. Make sure you have Python 3.10 or higher installed.

```bash
pip install restcodegen
```

## Usage

Once installed, you can use the restcodegen command to generate a client.

### Command Syntax

```bash
restcodegen generate -u "http://example.com/openapi.json" -s "my-service" -a false
```

### Command Parameters

```
- --url, -u: URL of the OpenAPI specification (required).
- --service-name, -s: Name of the service (required).
- --async-mode, -a: Flag to enable asynchronous client generation (default is false).
- --api-tags, -t: Comma-separated list of API tags to generate (default is all APIs).
```

### Example

To generate a client for an API available at the URL https://petstore3.swagger.io/api/v3/openapi.json, you can use the following command:

```bash
restcodegen generate -u "https://petstore3.swagger.io/api/v3/openapi.json" -s "petstore" -a false
```

### Result

After a successful command execution, a client library will be created with a name corresponding to the provided service name. The generated files will contain classes and methods for interacting with the API described in the provided specification.

Structure:

```
└── clients                      
     └── http     
        ├── schemas               # OpenAPI 3.0.0 schemas for all generated apis                   
        └── service_name          # Service name     
            ├── apis              # APIs                    
            └── models            # Pydantic models   
```

### Generated client usage

The generated API client includes built-in logging using `structlog`, which allows you to easily track API requests and responses. Additionally, instead of using the built-in `ApiClient`, you can provide your own HTTPX client for more customization.

Here is an example of how to use the generated client:

```python
from restcodegen.restclient import Client, Configuration
from clients.http.petstore import PetApi
import structlog

structlog.configure(
    processors=[
        structlog.processors.JSONRenderer(
            indent=4,
            ensure_ascii=True,
        )
    ]
)

if __name__ == '__main__':
    configuration = Configuration(host="https://petstore3.swagger.io/api/v3")
    api_client = Client(configuration)  # You can replace this with your custom httpx client
    # apiclient = httpx.AsyncClient()  # Uncomment if using a custom HTTPX client
    pet_api = PetApi(api_client)
    response = pet_api.get_pet_pet_id(pet_id=1)
    print(response)

```

## License

This project is licensed under the MIT License. See the LICENSE file for more information.

---

I hope that RestCodeGen will simplify your work with REST APIs. If you have any questions or suggestions, please create an issue in the repository.
