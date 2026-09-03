# Data migration: backfill wagon_plate + chamber_codes + total_weight + stage timestamps
# for existing WagonTrip rows. wagon_plate from wagon FK; chamber_codes/total_weight from
# SettingWagon → SettingEvent; pushed_at/exited_at/entered_waiting_at from related fact tables.
from django.db import migrations
from django.utils import timezone


def backfill(apps, schema_editor):
    WagonTrip = apps.get_model('mes', 'WagonTrip')
    Wagon = apps.get_model('mes', 'Wagon')
    SettingWagon = apps.get_model('mes', 'SettingWagon')
    KilnPush = apps.get_model('mes', 'KilnPush')
    KilnExit = apps.get_model('mes', 'KilnExit')

    # Wagon name lookup
    wagon_names = {w.wagon_id: w.wagon_name for w in Wagon.objects.only('wagon_id', 'wagon_name')}

    trips_to_update = []
    for t in WagonTrip.objects.all():
        updates = {}
        # wagon_plate
        if t.wagon_id in wagon_names:
            updates['wagon_plate'] = wagon_names[t.wagon_id]
        # chamber_codes + total_weight from SettingWagon
        sws = list(SettingWagon.objects.select_related('setting_event__chamber')
                    .filter(trip=t.trip_id))
        if sws:
            codes = []
            total = 0
            for sw in sws:
                cod = sw.setting_event.chamber.chamber_code if sw.setting_event.chamber_id else None
                if cod:
                    codes.append(cod)
                pk = sw.packages or 0
                if pk:
                    total += pk
            if codes and codes != t.chamber_codes:
                updates['chamber_codes'] = codes
            if total and total != t.total_weight:
                updates['total_weight'] = total
        # stage timestamps from related fact tables
        kp = KilnPush.objects.filter(trip=t.trip_id).order_by('push_seq').first()
        if kp and not t.pushed_at:
            updates['pushed_at'] = kp.created_at
        ke = KilnExit.objects.filter(trip=t.trip_id, discharged=False).order_by('exit_push_seq').first()
        if ke and not t.exited_at:
            updates['exited_at'] = ke.created_at
        # entered_waiting_at = when status moved to waiting_hall
        # We can't reliably backfill from status history, so skip it.
        if updates:
            for k, v in updates.items():
                setattr(t, k, v)
            trips_to_update.append(t)

    WagonTrip.objects.bulk_update(
        trips_to_update,
        ['wagon_plate', 'chamber_codes', 'total_weight', 'pushed_at', 'exited_at'],
        batch_size=2000,
    )


class Migration(migrations.Migration):
    dependencies = [
        ('mes', '0007_add_trip_timestamps_and_summary'),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
