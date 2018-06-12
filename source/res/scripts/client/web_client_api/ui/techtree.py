# Python bytecode 2.7 (decompiled from Python 2.7)
# Embedded file name: scripts/client/web_client_api/ui/techtree.py
from helpers import dependency
from gui.shared import event_dispatcher
from skeletons.gui.shared import IItemsCache
from web_client_api import W2CSchema, w2c, Field

class _OpenTechTreeSchema(W2CSchema):
    vehicle_id = Field(required=True, type=int)


class TechTreeTabWebApiMixin(object):
    itemsCache = dependency.descriptor(IItemsCache)

    @w2c(_OpenTechTreeSchema, 'tech_tree')
    def openTechTree(self, cmd):
        event_dispatcher.showTechTree(cmd.vehicle_id)

    @w2c(_OpenTechTreeSchema, 'research')
    def openResearch(self, cmd):
        event_dispatcher.showResearchView(cmd.vehicle_id)
