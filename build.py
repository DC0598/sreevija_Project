import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django


def main():
    required = ("DATABASE_URL", "SECRET_KEY", "ADMIN_EMAIL", "ADMIN_PASSWORD")
    missing = [key for key in required if not os.environ.get(key)]
    if missing:
        raise RuntimeError(f"Missing deployment environment variables: {', '.join(missing)}")
    django.setup()
    from django.core.management import call_command
    from django.db import connection, transaction

    def initialize_store():
        call_command("collectstatic", interactive=False, clear=True)
        call_command("migrate", interactive=False)
        call_command("import_legacy_products")
        call_command("seed_store")
        call_command("create_initial_admin")

    if connection.vendor == "postgresql":
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_xact_lock(%s)", [749231046])
            initialize_store()
    else:
        initialize_store()


if __name__ == "__main__":
    main()
