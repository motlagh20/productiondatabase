"""DB router: the `staging` alias is read-only historical source.

All app models live on `default` (mes_app). Nothing is written to staging from the
app — dimension seeding reads staging via an explicit connection, never the ORM's
write path. This router is a hard guard: any attempted write routed to staging fails.
"""


class StagingReadOnlyRouter:
    STAGING = 'staging'

    def db_for_read(self, model, **hints):
        return 'default'

    def db_for_write(self, model, **hints):
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # Never migrate anything onto the staging DB.
        if db == self.STAGING:
            return False
        return True
