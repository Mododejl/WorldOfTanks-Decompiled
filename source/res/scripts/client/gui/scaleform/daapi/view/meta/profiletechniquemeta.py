# Python bytecode 2.7 (decompiled from Python 2.7)
# Embedded file name: scripts/client/gui/Scaleform/daapi/view/meta/ProfileTechniqueMeta.py
from gui.Scaleform.daapi.view.lobby.profile.ProfileSection import ProfileSection

class ProfileTechniqueMeta(ProfileSection):
    """
    DO NOT MODIFY!
    Generated with yaml.
    __author__ = 'yaml_processor'
    @extends ProfileSection
    """

    def setSelectedTableColumn(self, index, sortDirection):
        self._printOverrideError('setSelectedTableColumn')

    def as_responseVehicleDossierS(self, data):
        """
        :param data: Represented by ProfileVehicleDossierVO (AS)
        """
        return self.flashObject.as_responseVehicleDossier(data) if self._isDAAPIInited() else None
