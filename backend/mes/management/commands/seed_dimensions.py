"""Seed dimension masters into the app DB from the staging (historical) source.

Read-only from staging (`staging` alias), writes to `default` (mes_app).
Idempotent: re-running updates in place by natural key.
"""
from django.core.management.base import BaseCommand
from django.db import connections
from mes.models import (
    Chamber,
    Glaze,
    KilnSensor,
    Operator,
    Product,
    Wagon,
)


def _fetch_rows(sql):
    """Read a table from the staging (historical) connection, as dict rows."""
    with connections['staging'].cursor() as cur:
        cur.execute(sql)
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


class Command(BaseCommand):
    help = 'Seed dimension masters from the staging DB (read-only) into the app DB.'

    def handle(self, *args, **options):
        self.stdout.write('Seeding dimensions from staging (read-only)...')

        # --- operator ---
        rows = _fetch_rows(
            'SELECT operator_id, operator_code, full_name, role, is_active FROM operator '
            'WHERE is_active ORDER BY operator_id'
        )
        for r in rows:
            Operator.objects.update_or_create(
                operator_id=r['operator_id'],
                defaults=dict(
                    operator_code=r['operator_code'],
                    full_name=r['full_name'] or '',
                    role=r['role'] or '',
                    is_active=r['is_active'] or True,
                ),
            )
        self.stdout.write(f'  operator: {len(rows)}')

        # --- chamber ---
        rows = _fetch_rows(
            'SELECT chamber_id, chamber_code, chamber_type, description, is_active FROM chamber '
            'WHERE is_active ORDER BY chamber_id'
        )
        for r in rows:
            Chamber.objects.update_or_create(
                chamber_id=r['chamber_id'],
                defaults=dict(
                    chamber_code=r['chamber_code'],
                    chamber_type=r['chamber_type'] or 'SETTING',
                    description=r['description'] or '',
                    is_active=r['is_active'] or True,
                ),
            )
        self.stdout.write(f'  chamber: {len(rows)}')

        # --- product ---
        rows = _fetch_rows(
            'SELECT product_id, product_code_kiln, product_code_packing, product_name_setting, '
            'product_group, is_active FROM product ORDER BY product_id'
        )
        for r in rows:
            Product.objects.update_or_create(
                product_id=r['product_id'],
                defaults=dict(
                    product_code_kiln=r['product_code_kiln'] or '',
                    product_code_packing=r['product_code_packing'] or '',
                    product_name_setting=r['product_name_setting'] or '',
                    product_group=r['product_group'] or '',
                    is_active=r['is_active'] or True,
                ),
            )
        self.stdout.write(f'  product: {len(rows)}')

        # --- glaze ---
        rows = _fetch_rows(
            'SELECT glaze_id, glaze_code, glaze_name, formula, description, is_combined '
            'FROM glaze ORDER BY glaze_id'
        )
        for r in rows:
            Glaze.objects.update_or_create(
                glaze_id=r['glaze_id'],
                defaults=dict(
                    glaze_code=r['glaze_code'],
                    glaze_name=r['glaze_name'],
                    formula=r.get('formula') or '',
                    description=r.get('description') or '',
                    is_combined=r.get('is_combined') or False,
                ),
            )
        self.stdout.write(f'  glaze: {len(rows)}')

        # --- wagon (physical plate names) ---
        # Clean-core boundary (ADR-0008): only the VALID plate range 1..80 enters the
        # app. Historical out-of-range plates (81, 141, 585, ...) are operator typos
        # that belong to the ETL/historical layer, not the app dimension. Excluding
        # them here is what makes the plate dropdown correct by construction — the app
        # needs no ">80" validator (M5_PROPOSED_SCHEMA §3, SRS acceptance #4).
        rows = _fetch_rows(
            "SELECT wagon_id, wagon_name FROM wagon "
            "WHERE wagon_name ~ '^[0-9]+$' AND wagon_name::int BETWEEN 1 AND 80 "
            'ORDER BY wagon_id'
        )
        for r in rows:
            Wagon.objects.update_or_create(
                wagon_id=r['wagon_id'], defaults=dict(wagon_name=str(r['wagon_name'])),
            )
        self.stdout.write(f'  wagon: {len(rows)} (out-of-range historical plates excluded)')

        # --- kiln_sensor ---
        rows = _fetch_rows(
            'SELECT sensor_id, sensor_code, sensor_name, position_order, is_measured '
            'FROM kiln_sensor ORDER BY position_order, sensor_id'
        )
        for r in rows:
            KilnSensor.objects.update_or_create(
                sensor_id=r['sensor_id'],
                defaults=dict(
                    sensor_code=r['sensor_code'],
                    sensor_name=r['sensor_name'] or '',
                    position_order=r['position_order'] or 0,
                    is_measured=r['is_measured'] or True,
                ),
            )
        self.stdout.write(f'  kiln_sensor: {len(rows)}')

        self.stdout.write(self.style.SUCCESS('Dimension seeding complete.'))
