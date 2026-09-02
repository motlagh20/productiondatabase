"""Create Django auth users for all MES operators.

Each Operator row gets a matching auth.User (username=operator_code,
password=test). Safe to re-run — skips existing users.

Usage: ./manage.py sync_operator_users
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from mes.models import Operator

User = get_user_model()


class Command(BaseCommand):
    help = 'Sync Django auth users with MES operators (one user per operator_code)'

    def handle(self, *args, **options):
        created = 0
        skipped = 0
        for op in Operator.objects.all():
            if User.objects.filter(username=op.operator_code).exists():
                skipped += 1
                continue
            User.objects.create_user(
                username=op.operator_code,
                password='test',
                first_name=op.full_name,
                is_active=True,
            )
            created += 1
            self.stdout.write(f'  created: {op.operator_code}  ({op.full_name})')

        self.stdout.write(self.style.SUCCESS(
            f'Done — {created} created, {skipped} already existed.'
        ))
