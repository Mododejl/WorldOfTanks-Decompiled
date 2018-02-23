# Python bytecode 2.7 (decompiled from Python 2.7)
# Embedded file name: scripts/client/gui/Scaleform/daapi/view/meta/StoreViewMeta.py
"""
This file was generated using the wgpygen.
Please, don't edit this file manually.
"""
from gui.Scaleform.framework.entities.View import View

class StoreViewMeta(View):

    def onClose(self):
        self._printOverrideError('onClose')

    def onTabChange(self, tabId):
        self._printOverrideError('onTabChange')

    def onBackButtonClick(self):
        self._printOverrideError('onBackButtonClick')

    def as_showStorePageS(self, tabId):
        return self.flashObject.as_showStorePage(tabId) if self._isDAAPIInited() else None

    def as_initS(self, data):
        """
        :param data: Represented by StoreViewInitVO (AS)
        """
        return self.flashObject.as_init(data) if self._isDAAPIInited() else None

    def as_showBackButtonS(self, label, description):
        return self.flashObject.as_showBackButton(label, description) if self._isDAAPIInited() else None

    def as_hideBackButtonS(self):
        return self.flashObject.as_hideBackButton() if self._isDAAPIInited() else None

    def as_setBtnTabCountersS(self, counters):
        """
        :param counters: Represented by Vector.<CountersVo> (AS)
        """
        return self.flashObject.as_setBtnTabCounters(counters) if self._isDAAPIInited() else None

    def as_removeBtnTabCountersS(self, counters):
        """
        :param counters: Represented by Vector.<String> (AS)
        """
        return self.flashObject.as_removeBtnTabCounters(counters) if self._isDAAPIInited() else None
