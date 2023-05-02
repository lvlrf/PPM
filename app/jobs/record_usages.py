from operator import attrgetter

from app import scheduler, xray
from app.db import engine
from app.db.models import System, User
from sqlalchemy import bindparam, update
from app.utils.xray import xray_config_include_db_clients


def record_users_usage():
    with engine.connect() as conn:
        try:
            params = [
                {"name": stat.name, "value": stat.value}
                for stat in filter(attrgetter('value'), xray.api.get_users_stats(reset=True))
            ]

        except xray.exceptions.ConnectionError:
            try:
                xray.core.restart(
                    xray_config_include_db_clients(xray.config)
                )
            except ProcessLookupError:
                pass

            return

        if not params:
            return

        stmt = update(User). \
            where(User.username == bindparam('name')). \
            values(used_traffic=User.used_traffic + bindparam('value'))

        conn.execute(stmt, params)


scheduler.add_job(record_users_usage, 'interval', seconds=10)


def record_outbounds_usage():
    with engine.connect() as conn:
        try:
            params = [
                {"up": stat.value, "down": 0} if stat.link == "uplink" else {"up": 0, "down": stat.value}
                for stat in filter(attrgetter('value'), xray.api.get_outbounds_stats(reset=True))
            ]

        except xray.exceptions.ConnectionError:
            try:
                xray.core.restart(
                    xray_config_include_db_clients(xray.config)
                )
            except ProcessLookupError:
                pass

            return

        if not params:
            return

        stmt = update(System).values(
            uplink=System.uplink + bindparam('up'),
            downlink=System.downlink + bindparam('down')
        )

        conn.execute(stmt, params)


scheduler.add_job(record_outbounds_usage, 'interval', seconds=5)
