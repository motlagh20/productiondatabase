"""Initialise ChamberState from the LAST event touching each chamber (point-in-time).

Unlike a whole-history aggregate, the live chamber state depends only on the most
recent event: if the last event was a dryer cycle -> chamber is LOADED; if the last
event was a setting batch (discharge) -> chamber is empty. Run after replay_historical
and after make_demo_slice. Idempotent (get_or_create + overwrite).

Order is decided by EVENT DATE (load_date / date_jalali), not surrogate id, because
dryer_cycle and setting_event use independent id sequences.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from mes.models import Chamber, ChamberState, DryerCycle, SettingEvent


def _jdate(s):
    """Parse YYYY.MM.DD -> tuple for comparison; None if blank/invalid."""
    if not s:
        return None
    try:
        y, m, d = (int(x) for x in s.split('.'))
        return (y, m, d)
    except Exception:
        return None


class Command(BaseCommand):
    help = 'Seed ChamberState from each chamber\'s last (dryer/setting) event by date.'

    def handle(self, *args, **options):
        self.stdout.write('Seeding ChamberState from last-per-chamber event (by date)...')
        n_loaded = n_empty = 0
        for chamber in Chamber.objects.all():
            last_dryer = (
                DryerCycle.objects.filter(chamber=chamber)
                .exclude(load_date__isnull=True).exclude(load_date='')
                .order_by('-load_date').values_list('load_date', flat=True).first()
            )
            last_setting = (
                SettingEvent.objects.filter(chamber=chamber)
                .exclude(date_jalali__isnull=True).exclude(date_jalali='')
                .order_by('-date_jalali').values_list('date_jalali', flat=True).first()
            )
            d = _jdate(last_dryer)
            s = _jdate(last_setting)
            if d is None and s is None:
                loaded = False
            elif d is None:
                loaded = False
            elif s is None:
                loaded = True
            else:
                loaded = d > s  # most-recent dated event wins
            state, _ = ChamberState.objects.get_or_create(chamber=chamber)
            state.is_loaded = loaded
            if loaded:
                state.current_dryer_cycle_id = (
                    DryerCycle.objects.filter(chamber=chamber, load_date=last_dryer)
                    .order_by('-dryer_cycle_id').values_list('dryer_cycle_id', flat=True).first()
                    if last_dryer else None
                )
                state.current_setting_event = None
                state.loaded_at = state.loaded_at or timezone.now()
            else:
                state.current_dryer_cycle = None
                state.current_setting_event_id = (
                    SettingEvent.objects.filter(chamber=chamber, date_jalali=last_setting)
                    .order_by('-setting_event_id').values_list('setting_event_id', flat=True).first()
                    if last_setting else None
                )
                state.loaded_at = None
            state.save()
            if loaded:
                n_loaded += 1
            else:
                n_empty += 1
        self.stdout.write(self.style.SUCCESS(
            f'ChamberState seeded: {n_loaded} loaded, {n_empty} empty.'
        ))
