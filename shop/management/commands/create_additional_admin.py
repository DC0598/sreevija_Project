import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create an optional additional staff superuser from deployment environment variables."

    def handle(self, *args, **options):
        username = os.environ.get("ADDITIONAL_ADMIN_USERNAME", "").strip()
        password = os.environ.get("ADDITIONAL_ADMIN_PASSWORD", "")
        if not username and not password:
            self.stdout.write("No additional admin account is configured.")
            return
        if not username or not password:
            raise CommandError(
                "ADDITIONAL_ADMIN_USERNAME and ADDITIONAL_ADMIN_PASSWORD must both be set."
            )
        if len(password) < 12:
            raise CommandError("ADDITIONAL_ADMIN_PASSWORD must be at least 12 characters.")

        User = get_user_model()
        existing_user = User.objects.filter(username__iexact=username).first()
        if existing_user:
            if not existing_user.is_superuser:
                raise CommandError(
                    "The configured additional admin username belongs to a non-admin account."
                )
            self.stdout.write("The additional admin account already exists; leaving it unchanged.")
            return

        user = User(username=username)
        try:
            validate_password(password, user=user)
        except ValidationError as exc:
            raise CommandError("; ".join(exc.messages)) from exc

        User.objects.create_superuser(
            username=username,
            email="",
            password=password,
            first_name="Admin",
        )
        self.stdout.write(self.style.SUCCESS("Created the configured additional admin account."))
