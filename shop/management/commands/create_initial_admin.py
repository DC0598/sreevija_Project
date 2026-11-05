import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create the configured initial staff account if one does not exist."

    def handle(self, *args, **options):
        email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
        password = os.environ.get("ADMIN_PASSWORD", "")
        if not email or not password:
            raise CommandError("ADMIN_EMAIL and ADMIN_PASSWORD must both be configured.")
        User = get_user_model()
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write("A staff superuser already exists; leaving it unchanged.")
            return
        if User.objects.filter(username__iexact=email).exists():
            raise CommandError(
                f"The username {email} is already in use. Choose a different ADMIN_EMAIL."
            )
        User.objects.create_superuser(
            username=email,
            email=email,
            password=password,
            first_name="Admin",
        )
        self.stdout.write(self.style.SUCCESS(f"Created initial staff account for {email}."))
