"""Database connection utilities."""

from supabase import create_client, Client
from shared.config import settings


def get_supabase_client() -> Client:
    """Create and return a Supabase client instance."""
    return create_client(
        settings.supabase_url,
        settings.supabase_service_role_key
    )


# Singleton instance
supabase: Client = get_supabase_client()
