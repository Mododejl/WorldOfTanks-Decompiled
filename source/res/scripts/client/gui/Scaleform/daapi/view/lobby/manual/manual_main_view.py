# Python bytecode 2.7 (decompiled from Python 2.7)
# Embedded file name: scripts/client/gui/Scaleform/daapi/view/lobby/manual/manual_main_view.py
import logging
from gui.Scaleform.daapi.view.meta.ManualMainViewMeta import ManualMainViewMeta
from gui.Scaleform.locale.RES_ICONS import RES_ICONS
from gui.shared import events, g_eventBus, EVENT_BUS_SCOPE
from gui.Scaleform.daapi.settings.views import VIEW_ALIAS
from gui.Scaleform.daapi.view.lobby.manual.manual_view_base import ManualViewBase
_logger = logging.getLogger(__name__)

class ManualMainView(ManualViewBase, ManualMainViewMeta):
    __background_alpha__ = 1

    def __init__(self, _=None):
        super(ManualMainView, self).__init__()

    def closeView(self):
        self._close()
        self.manualController.clear()
        self.fireEvent(events.LoadViewEvent(VIEW_ALIAS.LOBBY_HANGAR), scope=EVENT_BUS_SCOPE.LOBBY)

    def onChapterOpenedS(self, chapterIndex):
        _logger.debug('ManualMainView. Chapter selected: %s', chapterIndex)
        g_eventBus.handleEvent(events.LoadViewEvent(VIEW_ALIAS.MANUAL_CHAPTER_VIEW, ctx={'chapterIndex': chapterIndex}), scope=EVENT_BUS_SCOPE.LOBBY)
        self.as_showCloseBtnS(False)

    def _populate(self):
        super(ManualMainView, self)._populate()
        chapters = self.manualController.getChaptersUIData()
        self.as_setChaptersS(chapters)
        self.as_setPageBackgroundS(RES_ICONS.MAPS_ICONS_MANUAL_MAINPAGE_BACKGROUND)
        self.addListener(events.ManualEvent.CHAPTER_CLOSED, self.__onChapterClosed, EVENT_BUS_SCOPE.LOBBY)

    def _dispose(self):
        super(ManualMainView, self)._dispose()
        self.removeListener(events.ManualEvent.CHAPTER_CLOSED, self.__onChapterClosed, EVENT_BUS_SCOPE.LOBBY)

    def __onChapterClosed(self, _):
        self.as_showCloseBtnS(True)
