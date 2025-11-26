import pytest


@pytest.fixture()
def sample_openapi_spec() -> dict:
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Test API",
            "version": "1.0.0",
            "description": "API for testing",
        },
        "paths": {
            "/users": {
                "get": {
                    "operationId": "getUsers",
                    "tags": ["users"],
                    "summary": "Get users",
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/UserList"}}},
                        }
                    },
                },
                "post": {
                    "operationId": "createUser",
                    "tags": ["users"],
                    "summary": "Create user",
                    "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/User"}}}},
                    "responses": {
                        "201": {
                            "description": "Created",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/User"}}},
                        }
                    },
                },
            },
            "/posts": {
                "get": {
                    "operationId": "getPosts",
                    "tags": ["posts"],
                    "summary": "Get posts",
                    "parameters": [
                        {
                            "name": "userId",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer"},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/PostList"}}},
                        }
                    },
                }
            },
        },
        "components": {
            "schemas": {
                "User": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                    },
                    "required": ["id", "name"],
                },
                "UserList": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/User"},
                },
                "Post": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "title": {"type": "string"},
                        "userId": {"type": "integer"},
                    },
                    "required": ["id", "title"],
                },
                "PostList": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/Post"},
                },
            }
        },
    }
