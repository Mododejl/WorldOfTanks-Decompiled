# Python bytecode 2.7 (decompiled from Python 2.7)
# Embedded file name: scripts/client/web_client_api/ui/__init__.py
from web_client_api import w2capi
from web_client_api.ui.browser import OpenBrowserWindowWebApiMixin, CloseBrowserWindowWebApiMixin, OpenExternalBrowserWebApiMixin
from web_client_api.ui.clan import ClanWindowWebApiMixin
from web_client_api.ui.hangar import HangarWindowsWebApiMixin, HangarTabWebApiMixin
from web_client_api.ui.menu import UserMenuWebApiMixin
from web_client_api.ui.notification import NotificationWebApiMixin
from web_client_api.ui.profile import ProfileTabWebApiMixin, ProfileWindowWebApiMixin
from web_client_api.ui.techtree import TechTreeTabWebApiMixin
from web_client_api.ui.util import UtilWebApiMixin
from web_client_api.ui.vehicle import VehicleCompareWebApiMixin, VehiclePreviewWebApiMixin, VehicleComparisonBasketWebApiMixin

@w2capi(name='open_window', key='window_id')
class OpenWindowWebApi(OpenBrowserWindowWebApiMixin, ClanWindowWebApiMixin, ProfileWindowWebApiMixin, OpenExternalBrowserWebApiMixin, HangarWindowsWebApiMixin):
    pass


@w2capi(name='close_window', key='window_id')
class CloseWindowWebApi(CloseBrowserWindowWebApiMixin):
    pass


@w2capi(name='open_tab', key='tab_id')
class OpenTabWebApi(HangarTabWebApiMixin, ProfileTabWebApiMixin, VehiclePreviewWebApiMixin, TechTreeTabWebApiMixin, VehicleComparisonBasketWebApiMixin):
    pass


@w2capi()
class NotificationWebApi(NotificationWebApiMixin):
    pass


@w2capi(name='context_menu', key='menu_type')
class ContextMenuWebApi(UserMenuWebApiMixin):
    pass


@w2capi(name='util', key='action')
class UtilWebApi(UtilWebApiMixin, VehicleCompareWebApiMixin):
    pass
