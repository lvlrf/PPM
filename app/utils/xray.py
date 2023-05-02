from app import xray
from app.db import GetDB, User, get_users
from app.models.proxy import ProxySettings
from app.models.user import User, UserResponse, UserStatus
from app.xray.config import XRayConfig


def xray_add_user(user: User):
    if not isinstance(user, User):
        user = UserResponse.from_orm(user)
    for proxy_type, inbound_tags in user.inbounds.items():
        account = user.get_account(proxy_type)
        for inbound_tag in inbound_tags:
            try:
                xray.api.add_inbound_user(tag=inbound_tag, user=account)
            except xray.exc.EmailExistsError:
                pass


def xray_remove_user(user: User):
    for inbound_tag in xray.config.inbounds_by_tag:
        try:
            xray.api.remove_inbound_user(tag=inbound_tag, email=user.username)
        except xray.exc.EmailNotFoundError:
            pass


def xray_config_include_db_clients(config: XRayConfig):
    config = config.copy()

    with GetDB() as db:
        for user in get_users(db, status=UserStatus.active):
            proxies_settings = {
                p.type: ProxySettings.from_dict(p.type, p.settings).dict(no_obj=True)
                for p in user.proxies
            }
            for proxy_type, inbound_tags in user.inbounds.items():
                for inbound_tag in inbound_tags:
                    config.add_inbound_client(inbound_tag,
                                              user.username,
                                              proxies_settings[proxy_type])

    return config
