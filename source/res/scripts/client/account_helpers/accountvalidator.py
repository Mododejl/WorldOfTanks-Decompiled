# Embedded file name: scripts/client/account_helpers/AccountValidator.py
import BigWorld
import constants
from adisp import process, async
from items import vehicles, ITEM_TYPE_NAMES
from debug_utils import *
from gui.shared import g_itemsCache
from gui.shared.gui_items import GUI_ITEM_TYPE

class ValidateException(Exception):

    def __init__(self, msg, code, itemData):
        super(ValidateException, self).__init__(msg)
        self.code = code
        self.itemData = itemData


class AccountValidator(object):

    class CODES:
        OK = 0
        INVENTORY_VEHICLE_MISMATCH = 1001
        INVENTORY_CHASSIS_MISMATCH = 1002
        INVENTORY_TURRET_MISMATCH = 1003
        INVENTORY_GUN_MISMATCH = 1004
        INVENTORY_ENGINE_MISMATCH = 1005
        INVENTORY_FUEL_TANK_MISMATCH = 1006
        INVENTORY_RADIO_MISMATCH = 1007
        INVENTORY_TANKMEN_MISMATCH = 1008
        INVENTORY_OPT_DEV_MISMATCH = 1009
        INVENTORY_SHELL_MISMATCH = 1010
        INVENTORY_EQ_MISMATCH = 1011
        INVENTORY_VEHICLE_CREW_MISMATCH = 1012

    @classmethod
    def __packItemData(cls, itemTypeID, itemData, *args):
        return (ITEM_TYPE_NAMES[itemTypeID], itemData) + args

    @async
    def __devSellInvalidVehicle(self, vehInvData, callback):

        def response(code):
            LOG_DEBUG('Invalid vehicle selling result', vehInvData, code)
            callback(code >= 0)

        BigWorld.player().inventory.sellVehicle(vehInvData.invID, True, [], [], response)

    def __validateInventoryVehicles(self):
        for invID, vehInvData in g_itemsCache.items.inventory.getItemsData(GUI_ITEM_TYPE.VEHICLE).iteritems():
            try:
                vehDescr = vehicles.VehicleDescr(compactDescr=vehInvData.compDescr)
            except Exception as e:
                raise ValidateException(e.message, self.CODES.INVENTORY_VEHICLE_MISMATCH, self.__packItemData(GUI_ITEM_TYPE.VEHICLE, vehInvData))

            vehCrewRoles = vehDescr.type.crewRoles
            for idx, tankmanID in enumerate(vehInvData.crew):
                if idx >= len(vehCrewRoles):
                    raise ValidateException('Exceeded tankmen in tank', self.CODES.INVENTORY_VEHICLE_CREW_MISMATCH, self.__packItemData(GUI_ITEM_TYPE.VEHICLE, vehInvData, tankmanID))

    def __validateInvItem(self, itemTypeID, errorCode):
        for intCompactDescr, itemData in g_itemsCache.items.inventory.getItemsData(itemTypeID).iteritems():
            try:
                vehicles.getDictDescr(intCompactDescr)
            except Exception as e:
                raise ValidateException(e.message, errorCode, self.__packItemData(itemTypeID, itemData))

    @async
    @process
    def validate(self, callback):
        yield lambda callback: callback(True)
        handlers = [lambda : self.__validateInvItem(GUI_ITEM_TYPE.CHASSIS, self.CODES.INVENTORY_CHASSIS_MISMATCH),
         lambda : self.__validateInvItem(GUI_ITEM_TYPE.TURRET, self.CODES.INVENTORY_TURRET_MISMATCH),
         lambda : self.__validateInvItem(GUI_ITEM_TYPE.GUI, self.CODES.INVENTORY_GUN_MISMATCH),
         lambda : self.__validateInvItem(GUI_ITEM_TYPE.ENGINE, self.CODES.INVENTORY_ENGINE_MISMATCH),
         lambda : self.__validateInvItem(GUI_ITEM_TYPE.FUEL_TANK, self.CODES.INVENTORY_FUEL_TANK_MISMATCH),
         lambda : self.__validateInvItem(GUI_ITEM_TYPE.RADIO, self.CODES.INVENTORY_RADIO_MISMATCH),
         lambda : self.__validateInvItem(GUI_ITEM_TYPE.OPTIONALDEVICE, self.CODES.INVENTORY_OPT_DEV_MISMATCH),
         lambda : self.__validateInvItem(GUI_ITEM_TYPE.SHELL, self.CODES.INVENTORY_SHELL_MISMATCH),
         lambda : self.__validateInvItem(GUI_ITEM_TYPE.EQUIPMENT, self.CODES.INVENTORY_EQ_MISMATCH),
         self.__validateInventoryVehicles]
        for handler in handlers:
            try:
                handler()
            except ValidateException as e:
                processed = False
                if constants.IS_DEVELOPMENT:
                    itemData = e.itemData[1]
                    if e.code == self.CODES.INVENTORY_VEHICLE_CREW_MISMATCH:
                        processed = yield self.__devSellInvalidVehicle(itemData)
                if not processed:
                    LOG_ERROR('There is exception while validating item', e.itemData)
                    LOG_ERROR(e.message)
                    callback(e.code)
                    return

        callback(self.CODES.OK)
