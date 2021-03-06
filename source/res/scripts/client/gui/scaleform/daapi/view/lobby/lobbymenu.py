# Python bytecode 2.7 (decompiled from Python 2.7)
# Embedded file name: scripts/client/gui/Scaleform/daapi/view/lobby/LobbyMenu.py
import BigWorld
import constants
from adisp import process
from gui import DialogsInterface
from gui.Scaleform.daapi.view.common.settings.new_settings_counter import getCountNewSettings
from gui.Scaleform.daapi.view.dialogs import DIALOG_BUTTON_ID
from gui.Scaleform.daapi.view.meta.LobbyMenuMeta import LobbyMenuMeta
from gui.Scaleform.genConsts.MENU_CONSTANTS import MENU_CONSTANTS
from gui.Scaleform.locale.MENU import MENU
from gui.Scaleform.locale.BOOTCAMP import BOOTCAMP
from gui.Scaleform.locale.TOOLTIPS import TOOLTIPS
from gui.shared import event_dispatcher
from gui.shared.formatters import text_styles, icons
from gui.sounds.ambients import LobbySubViewEnv
from helpers import i18n, getShortClientVersion, dependency
from skeletons.gameplay import IGameplayLogic
from skeletons.gui.game_control import IPromoController
from skeletons.gui.game_control import IBootcampController
from skeletons.gui.game_control import IManualController
from skeletons.gui.lobby_context import ILobbyContext
from gui.Scaleform.locale.RES_ICONS import RES_ICONS
from PlayerEvents import g_playerEvents as events
from gui.Scaleform.daapi.settings.views import VIEW_ALIAS
from gui.shared.event_bus import EVENT_BUS_SCOPE
from gui.shared.events import LoadViewEvent
from gui.Scaleform.framework.managers.containers import POP_UP_CRITERIA
from gui.Scaleform.framework import ViewTypes
from gui.prb_control import prbEntityProperty

def _getVersionMessage(promo):
    return {'message': '{0} {1}'.format(text_styles.main(i18n.makeString(MENU.PROMO_PATCH_MESSAGE)), text_styles.stats(getShortClientVersion())),
     'label': i18n.makeString(MENU.PROMO_TOARCHIVE),
     'promoEnabel': promo.isPatchPromoAvailable(),
     'tooltip': TOOLTIPS.LOBBYMENU_VERSIONINFOBUTTON}


class LobbyMenu(LobbyMenuMeta):
    __sound_env__ = LobbySubViewEnv
    promo = dependency.descriptor(IPromoController)
    bootcamp = dependency.descriptor(IBootcampController)
    lobbyContext = dependency.descriptor(ILobbyContext)
    gameplay = dependency.descriptor(IGameplayLogic)
    manualController = dependency.descriptor(IManualController)

    @prbEntityProperty
    def prbEntity(self):
        pass

    def versionInfoClick(self):
        self.promo.showVersionsPatchPromo()
        self.destroy()

    def settingsClick(self):
        event_dispatcher.showSettingsWindow(redefinedKeyMode=False)

    def onWindowClose(self):
        self.destroy()

    def cancelClick(self):
        self.destroy()

    def onEscapePress(self):
        self.destroy()

    @process
    def refuseTraining(self):
        isOk = yield DialogsInterface.showI18nConfirmDialog('refuseTraining')
        if isOk:
            event_dispatcher.stopTutorial()
        self.destroy()

    @process
    def logoffClick(self):
        isOk = yield DialogsInterface.showI18nConfirmDialog('disconnect', focusedID=DIALOG_BUTTON_ID.CLOSE)
        if isOk:
            self.gameplay.goToLoginByRQ()

    @process
    def quitClick(self):
        isOk = yield DialogsInterface.showI18nConfirmDialog('quit', focusedID=DIALOG_BUTTON_ID.CLOSE)
        if isOk:
            self.gameplay.quitFromGame()

    def onCounterNeedUpdate(self):
        self.__updateNewSettingsCount()

    def bootcampClick(self):
        self.bootcamp.runBootcamp()

    def manualClick(self):
        if self.manualController.isActivated():
            windowContainer = self.app.containerManager.getContainer(ViewTypes.LOBBY_SUB)
            view = windowContainer.getView(criteria={POP_UP_CRITERIA.VIEW_ALIAS: VIEW_ALIAS.WIKI_VIEW})
            if view is not None:
                self.destroy()
            else:
                self.fireEvent(LoadViewEvent(VIEW_ALIAS.WIKI_VIEW), EVENT_BUS_SCOPE.LOBBY)
        return

    def _populate(self):
        super(LobbyMenu, self)._populate()
        self.__addListeners()
        state = MENU_CONSTANTS.STATE_SHOW_ALL
        if self.bootcamp.isInBootcamp():
            state = MENU_CONSTANTS.STATE_HIDE_ALL
        elif constants.IS_CHINA:
            state = MENU_CONSTANTS.STATE_SHOW_SERVER_NAME
        elif not constants.IS_SHOW_SERVER_STATS:
            state = MENU_CONSTANTS.STATE_HIDE_SERVER_STATS_ITEM
        self.as_setMenuStateS(state)
        self.as_setVersionMessageS(_getVersionMessage(self.promo))
        bootcampIcon = RES_ICONS.MAPS_ICONS_BOOTCAMP_MENU_MENUBOOTCAMPICON
        bootcampIconSource = icons.makeImageTag(bootcampIcon, 33, 27, -8, 0)
        if self.bootcamp.isInBootcamp():
            self.as_setBootcampButtonLabelS(BOOTCAMP.REQUEST_BOOTCAMP_FINISH, bootcampIconSource)
        elif self.lobbyContext.getServerSettings().isBootcampEnabled():
            if self.bootcamp.runCount() > 0:
                bootcampLabel = BOOTCAMP.REQUEST_BOOTCAMP_RETURN
            else:
                bootcampLabel = BOOTCAMP.REQUEST_BOOTCAMP_START
            self.as_setBootcampButtonLabelS(bootcampLabel, bootcampIconSource)
        else:
            self.as_showBootcampButtonS(False)
        if events.isPlayerEntityChanging:
            self.as_showBootcampButtonS(False)
        if not self.manualController.isActivated() or self.bootcamp.isInBootcamp() or self.__isInQueue():
            self.as_showManualButtonS(False)

    def _dispose(self):
        self.__removeListeners()
        super(LobbyMenu, self)._dispose()

    def __isInQueue(self):
        return self.prbEntity and self.prbEntity.isInQueue()

    def __updateNewSettingsCount(self):
        userLogin = getattr(BigWorld.player(), 'name', '')
        if userLogin == '':
            return
        newSettingsCnt = getCountNewSettings()
        if newSettingsCnt > 0:
            self.as_setCounterS([{'componentId': 'settingsBtn',
              'count': str(newSettingsCnt)}])
        else:
            self.as_removeCounterS(['settingsBtn'])

    def __addListeners(self):
        self.lobbyContext.getServerSettings().onServerSettingsChange += self.__onServerSettingChanged

    def __removeListeners(self):
        self.lobbyContext.getServerSettings().onServerSettingsChange -= self.__onServerSettingChanged

    def __onServerSettingChanged(self, diff):
        if 'isManualEnabled' in diff:
            manualButtonEnabled = diff['isManualEnabled']
            self.as_showManualButtonS(manualButtonEnabled)
