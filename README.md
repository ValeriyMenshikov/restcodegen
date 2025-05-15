# RestCodeGen

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/Version-1.0.2-orange.svg" alt="Version">
</p>

<p align="center">
  <b>Generate Python clients from OpenAPI specifications with ease</b>
</p>

## 🚀 Overview

RestCodeGen is a powerful tool for automatically generating Python client libraries from OpenAPI 3 specifications. It streamlines the process of interacting with REST APIs, allowing developers and testers to quickly integrate with services that provide OpenAPI documentation.

### ✨ Key Features

- **Easy Client Generation**: Create Python clients with a single command
- **Async Support**: Generate both synchronous and asynchronous clients
- **Selective API Generation**: Choose specific API tags to include
- **Built-in Logging**: Integrated with structlog for comprehensive request/response tracking
- **Customizable**: Use your own HTTPX client for advanced configurations
- **Type Hints**: All generated code includes proper type annotations

## 📦 Installation

RestCodeGen requires Python 3.10 or higher. Install it using pip:

```bash
pip install restcodegen
```

Or with Poetry:

```bash
poetry add restcodegen
```

## 🔧 Usage

### Basic Command

```bash
restcodegen generate -u "http://example.com/openapi.json" -s "my-service" -a false
```

### Command Parameters

| Parameter | Short | Description | Required | Default |
|-----------|-------|-------------|----------|---------|
| `--url` | `-u` | URL of the OpenAPI specification | Yes | - |
| `--service-name` | `-s` | Name of the service | Yes | - |
| `--async-mode` | `-a` | Enable asynchronous client generation | No | `false` |
| `--api-tags` | `-t` | Comma-separated list of API tags to generate | No | All APIs |

### Example

Generate a client for the Petstore API:

```bash
restcodegen generate -u "https://petstore3.swagger.io/api/v3/openapi.json" -s "petstore" -a false
```

## 📁 Generated Structure

After successful execution, a client library will be created with the following structure:

```
└── clients                      
     └── http     
        ├── schemas               # OpenAPI 3.0.0 schemas for all generated APIs                   
        └── service_name          # Service name     
            ├── apis              # API client classes                    
            └── models            # Pydantic models   
```

## 💻 Using the Generated Client

The generated client includes built-in logging with `structlog` and supports custom HTTPX clients:

```python
from restcodegen.restclient import Client, Configuration
from clients.http.petstore import PetApi
import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.JSONRenderer(
            indent=4,
            ensure_ascii=True,
        )
    ]
)

# Create and use the client
if __name__ == '__main__':
    # Configure the base URL
    configuration = Configuration(host="https://petstore3.swagger.io/api/v3")
    
    # Use the built-in client
    api_client = Client(configuration)
    
    # Or use your custom HTTPX client
    # import httpx
    # api_client = httpx.Client()  # or httpx.AsyncClient() for async mode
    
    # Initialize the API
    pet_api = PetApi(api_client)
    
    # Make API calls
    response = pet_api.get_pet_pet_id(pet_id=1)
    print(response)
```

## 🔄 Development Workflow

1. Install development dependencies:
   ```bash
   poetry install
   ```

2. Run tests:
   ```bash
   poetry run pytest
   ```

3. Check code quality:
   ```bash
   poetry run ruff check .
   poetry run mypy .
   ```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

## 📬 Contact

For questions or feedback, please open an issue in the repository.

---

<p align="center">
  <i>RestCodeGen - Making API integration simple and efficient</i>
</p>
