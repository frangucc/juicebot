"""Database connection utilities."""

from supabase import create_client, Client
from shared.config import settings
import httpx


def get_supabase_client() -> Client:
    """Create and return a Supabase client instance with timeout configuration."""
    # Configure httpx with proper timeouts to prevent hanging connections
    # timeout of 30s for connect, 30s for read, 30s for write, 60s for pool
    timeout = httpx.Timeout(30.0, connect=30.0, read=30.0, write=30.0, pool=60.0)

    # Create httpx client with connection limits and timeouts
    http_client = httpx.Client(
        timeout=timeout,
        limits=httpx.Limits(
            max_keepalive_connections=10,
            max_connections=20,
            keepalive_expiry=30.0  # Close idle connections after 30s
        ),
        http2=True
    )

    # Create client with custom http client injected
    client = create_client(
        settings.supabase_url,
        settings.supabase_service_role_key
    )

    # Replace the default httpx client with our configured one
    client.postgrest.session = http_client

    return client


# Singleton instance
supabase: Client = get_supabase_client()
