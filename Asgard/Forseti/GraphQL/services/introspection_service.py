"""
GraphQL Introspection Service.

Introspects GraphQL endpoints to extract schema information.
"""

import json
from typing import Any, Optional, cast
from urllib.request import Request
from urllib.error import URLError

from Asgard.Forseti.GraphQL.models.graphql_models import (
    GraphQLConfig,
    GraphQLSchema,
)
from Asgard.Forseti.GraphQL.services._introspection_helpers import (
    parse_introspection_result,
    schema_to_sdl,
)
from Asgard.Forseti.GraphQL.utilities._url_safety import (
    build_introspection_opener,
    validate_introspection_url,
)


class IntrospectionService:
    """
    Service for introspecting GraphQL endpoints.

    Queries GraphQL endpoints to extract schema information.

    Usage:
        service = IntrospectionService()
        schema = service.introspect("https://api.example.com/graphql")
        print(f"Types: {len(schema.types)}")
    """

    INTROSPECTION_QUERY = """
    query IntrospectionQuery {
      __schema {
        queryType { name }
        mutationType { name }
        subscriptionType { name }
        types {
          ...FullType
        }
        directives {
          name
          description
          locations
          args {
            ...InputValue
          }
        }
      }
    }

    fragment FullType on __Type {
      kind
      name
      description
      fields(includeDeprecated: true) {
        name
        description
        args {
          ...InputValue
        }
        type {
          ...TypeRef
        }
        isDeprecated
        deprecationReason
      }
      inputFields {
        ...InputValue
      }
      interfaces {
        ...TypeRef
      }
      enumValues(includeDeprecated: true) {
        name
        description
        isDeprecated
        deprecationReason
      }
      possibleTypes {
        ...TypeRef
      }
    }

    fragment InputValue on __InputValue {
      name
      description
      type {
        ...TypeRef
      }
      defaultValue
    }

    fragment TypeRef on __Type {
      kind
      name
      ofType {
        kind
        name
        ofType {
          kind
          name
          ofType {
            kind
            name
            ofType {
              kind
              name
              ofType {
                kind
                name
                ofType {
                  kind
                  name
                  ofType {
                    kind
                    name
                  }
                }
              }
            }
          }
        }
      }
    }
    """

    def __init__(self, config: Optional[GraphQLConfig] = None):
        """
        Initialize the introspection service.

        Args:
            config: Optional configuration for introspection behavior.
        """
        self.config = config or GraphQLConfig()

    def introspect(
        self,
        endpoint: str,
        headers: Optional[dict[str, str]] = None,
        timeout: int = 30,
        allow_internal: Optional[bool] = None,
    ) -> GraphQLSchema:
        """
        Introspect a GraphQL endpoint.

        Args:
            endpoint: GraphQL endpoint URL (http/https only).
            headers: Optional HTTP headers.
            timeout: Request timeout in seconds.
            allow_internal: Permit loopback/RFC1918/link-local targets.
                Defaults to GraphQLConfig.allow_internal (False).

        Returns:
            Introspected GraphQLSchema.

        Raises:
            ConnectionError: If the endpoint cannot be reached.
            ValueError: If the URL is blocked or the response is not valid GraphQL.
        """
        if not self.config.allow_introspection:
            raise ValueError("Introspection is disabled in configuration")

        permit_internal = (
            self.config.allow_internal if allow_internal is None else allow_internal
        )
        result = self._execute_query(
            endpoint, headers, timeout, allow_internal=permit_internal
        )
        return parse_introspection_result(result)

    def _execute_query(
        self,
        endpoint: str,
        headers: Optional[dict[str, str]],
        timeout: int,
        allow_internal: bool,
    ) -> dict[str, Any]:
        """Execute the introspection query."""
        validate_introspection_url(endpoint, allow_internal=allow_internal)

        request_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if headers:
            request_headers.update(headers)

        payload = json.dumps({
            "query": self.INTROSPECTION_QUERY,
        }).encode("utf-8")

        request = Request(endpoint, data=payload, headers=request_headers)
        opener = build_introspection_opener(allow_internal=allow_internal)

        try:
            with opener.open(request, timeout=timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except URLError as e:
            raise ConnectionError(f"Failed to connect to endpoint: {e}") from e

        if "errors" in result:
            errors = result["errors"]
            error_messages = [e.get("message", str(e)) for e in errors]
            raise ValueError(f"GraphQL errors: {', '.join(error_messages)}")

        if "data" not in result or "__schema" not in result["data"]:
            raise ValueError("Invalid introspection response")

        return cast(dict[str, Any], result["data"]["__schema"])

    def to_sdl(self, schema: GraphQLSchema) -> str:
        """
        Convert an introspected schema to SDL.

        Args:
            schema: Introspected schema.

        Returns:
            SDL string representation.
        """
        return schema_to_sdl(schema)
