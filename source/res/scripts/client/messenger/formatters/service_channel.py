# Embedded file name: scripts/client/messenger/formatters/service_channel.py
import types
from adisp import async, process
from chat_shared import decompressSysMessage
from debug_utils import LOG_ERROR, LOG_WARNING, LOG_CURRENT_EXCEPTION, LOG_DEBUG
import account_helpers
import ArenaType
import BigWorld
from gui import GUI_SETTINGS
from gui.shared.utils import BoundMethodWeakref
from gui.shared.utils.functions import getTankmanRoleLevel
from gui.shared.gui_items.dossier.factories import getAchievementFactory
from gui.shared.notifications import NotificationPriorityLevel, NotificationGuiSettings
from gui.shared.utils.transport import z_loads
from messenger.formatters import TimeFormatter, NCContextItemFormatter
from messenger.m_constants import MESSENGER_I18N_FILE
from messenger.proto.bw.wrappers import ServiceChannelMessage
import offers
from constants import INVOICE_ASSET, AUTO_MAINTENANCE_TYPE, AUTO_MAINTENANCE_RESULT, PREBATTLE_TYPE, FINISH_REASON, KICK_REASON_NAMES, KICK_REASON, NC_MESSAGE_TYPE, NC_MESSAGE_PRIORITY, SYS_MESSAGE_CLAN_EVENT, SYS_MESSAGE_CLAN_EVENT_NAMES, SYS_MESSAGE_FORT_EVENT, SYS_MESSAGE_FORT_EVENT_NAMES, FORT_BUILDING_TYPE
from gui.prb_control.formatters import getPrebattleFullDescription
from gui.shared.utils.gui_items import formatPrice
from helpers import i18n, html, getClientLanguage, getLocalizedData
from helpers import time_utils
from items import getTypeInfoByIndex, getTypeInfoByName, tankmen
from items import vehicles as vehicles_core
from account_helpers import rare_achievements
from dossiers2.custom.records import DB_ID_TO_RECORD
from dossiers2.ui.achievements import ACHIEVEMENT_BLOCK
from messenger import g_settings

class ServiceChannelFormatter(object):

    def format(self, data, *args):
        return (None, None)

    def isNotify(self):
        return True

    def isAsync(self):
        return False

    def _getGuiSettings(self, data, key = None, priorityLevel = None):
        if isinstance(data, ServiceChannelMessage):
            isAlert = data.isHighImportance and data.active
        else:
            isAlert = False
        if priorityLevel is None:
            priorityLevel = g_settings.msgTemplates.priority(key)
        return NotificationGuiSettings(self.isNotify(), priorityLevel, isAlert)


class ServerRebootFormatter(ServiceChannelFormatter):

    def format(self, message, *args):
        if message.data:
            local_dt = time_utils.utcToLocalDatetime(message.data)
            formatted = g_settings.msgTemplates.format('serverReboot', ctx={'date': local_dt.strftime('%c')})
            return (formatted, self._getGuiSettings(message, 'serverReboot'))
        else:
            return (None, None)
            return None


class ServerRebootCancelledFormatter(ServiceChannelFormatter):

    def format(self, message, *args):
        if message.data:
            local_dt = time_utils.utcToLocalDatetime(message.data)
            formatted = g_settings.msgTemplates.format('serverRebootCancelled', ctx={'date': local_dt.strftime('%c')})
            return (formatted, self._getGuiSettings(message, 'serverRebootCancelled'))
        else:
            return (None, None)
            return None


class BattleResultsFormatter(ServiceChannelFormatter):
    __battleResultKeys = {-1: 'battleDefeatResult',
     0: 'battleDrawGameResult',
     1: 'battleVictoryResult'}
    __goldTemplateKey = 'battleResultGold'
    __questsTemplateKey = 'battleQuests'
    __i18n_penalty = i18n.makeString('#%s:serviceChannelMessages/battleResults/penaltyForDamageAllies' % MESSENGER_I18N_FILE)
    __i18n_contribution = i18n.makeString('#%s:serviceChannelMessages/battleResults/contributionForDamageAllies' % MESSENGER_I18N_FILE)

    def isNotify(self):
        return True

    def format(self, message, *args):
        battleResult = message.data
        arenaTypeID = battleResult.get('arenaTypeID', 0)
        arenaType = ArenaType.g_cache[arenaTypeID] if arenaTypeID > 0 else None
        arenaCreateTime = battleResult.get('arenaCreateTime', None)
        if arenaCreateTime and arenaType:
            ctx = {'arenaName': i18n.makeString(arenaType.name),
             'vehicleName': 'N/A',
             'xp': '0',
             'credits': '0'}
            vehicleCompDesc = battleResult.get('vehTypeCompDescr', None)
            if vehicleCompDesc:
                vt = vehicles_core.getVehicleType(vehicleCompDesc)
                ctx['vehicleName'] = vt.userString
            xp = battleResult.get('xp')
            if xp:
                ctx['xp'] = BigWorld.wg_getIntegralFormat(xp)
            ctx['xpEx'] = self.__makeXpExString(xp, battleResult)
            ctx['gold'] = self.__makeGoldString(battleResult.get('gold', 0))
            accCredits = battleResult.get('credits') - battleResult.get('creditsToDraw', 0)
            if accCredits:
                ctx['credits'] = BigWorld.wg_getIntegralFormat(accCredits)
            ctx['creditsEx'] = self.__makeCreditsExString(accCredits, battleResult)
            ctx['fortResource'] = self.__makeFortResourceString(battleResult)
            ctx['achieves'] = self.__makeAchievementsString(battleResult)
            ctx['lock'] = self.__makeVehicleLockString(ctx['vehicleName'], battleResult)
            ctx['quests'] = self.__makeQuestsAchieve(message)
            templateName = self.__battleResultKeys[battleResult['isWinner']]
            formatted = g_settings.msgTemplates.format(templateName, ctx=ctx, data={'timestamp': arenaCreateTime,
             'savedID': battleResult.get('arenaUniqueID', 0)})
            return (formatted, self._getGuiSettings(message, templateName))
        else:
            return (None, None)
            return

    def __makeFortResourceString(self, battleResult):
        fortResource = battleResult.get('fortResource', None)
        if fortResource is None:
            return ''
        else:
            return g_settings.htmlTemplates.format('battleResultFortResource', ctx={'fortResource': BigWorld.wg_getIntegralFormat(fortResource)})

    def __makeQuestsAchieve(self, message):
        fmtMsg = TokenQuestsFormatter(asBattleFormatter=True)._formatQuestAchieves(message)
        if fmtMsg is not None:
            return g_settings.htmlTemplates.format('battleQuests', {'achieves': fmtMsg})
        else:
            return ''

    def __makeVehicleLockString(self, vehicle, battleResult):
        expireTime = battleResult.get('vehTypeUnlockTime', 0)
        if not expireTime:
            return ''
        return g_settings.htmlTemplates.format('battleResultLocks', ctx={'vehicleName': vehicle,
         'expireTime': TimeFormatter.getLongDatetimeFormat(expireTime)})

    def __makeXpExString(self, xp, battleResult):
        if not xp:
            return ''
        exStrings = []
        penalty = battleResult.get('xpPenalty', 0)
        if penalty > 0:
            exStrings.append(self.__i18n_penalty % BigWorld.wg_getIntegralFormat(penalty))
        if battleResult['isWinner'] == 1:
            xpFactor = battleResult.get('dailyXPFactor', 1)
            if xpFactor > 1:
                exStrings.append(i18n.makeString('#%s:serviceChannelMessages/battleResults/doubleXpFactor' % MESSENGER_I18N_FILE) % xpFactor)
        if len(exStrings):
            return ' ({0:>s})'.format('; '.join(exStrings))
        return ''

    def __makeCreditsExString(self, accCredits, battleResult):
        if not accCredits:
            return ''
        exStrings = []
        penalty = sum([battleResult.get('creditsPenalty', 0), battleResult.get('creditsContributionOut', 0)])
        if penalty > 0:
            exStrings.append(self.__i18n_penalty % BigWorld.wg_getIntegralFormat(penalty))
        contribution = battleResult.get('creditsContributionIn', 0)
        if contribution > 0:
            exStrings.append(self.__i18n_contribution % BigWorld.wg_getIntegralFormat(contribution))
        if len(exStrings):
            return ' ({0:>s})'.format('; '.join(exStrings))
        return ''

    def __makeGoldString(self, gold):
        if not gold:
            return ''
        return g_settings.htmlTemplates.format(self.__goldTemplateKey, {'gold': BigWorld.wg_getGoldFormat(gold)})

    @classmethod
    def __makeAchievementsString(cls, battleResult):
        result = []
        for recordIdx, value in battleResult.get('popUpRecords', []):
            recordName = DB_ID_TO_RECORD[recordIdx]
            if recordName[1] in ('maxXP', 'maxFrags', 'maxDamage', 'markOfMastery'):
                continue
            achieve = getAchievementFactory(recordName).create(value=value)
            if achieve is not None:
                result.append(achieve)

        if 'markOfMastery' in battleResult and battleResult['markOfMastery'] > 0:
            achieve = getAchievementFactory((ACHIEVEMENT_BLOCK.TOTAL, 'markOfMastery')).create(value=battleResult['markOfMastery'])
            if achieve is not None:
                result.append(achieve)
        res = ''
        if len(result):
            res = g_settings.htmlTemplates.format('battleResultAchieves', {'achieves': ', '.join(map(lambda a: a.getUserName(), sorted(result)))})
        return res


class AutoMaintenanceFormatter(ServiceChannelFormatter):
    __messages = {AUTO_MAINTENANCE_RESULT.NOT_ENOUGH_ASSETS: {AUTO_MAINTENANCE_TYPE.REPAIR: '#messenger:serviceChannelMessages/autoRepairError',
                                                 AUTO_MAINTENANCE_TYPE.LOAD_AMMO: '#messenger:serviceChannelMessages/autoLoadError',
                                                 AUTO_MAINTENANCE_TYPE.EQUIP: '#messenger:serviceChannelMessages/autoEquipError'},
     AUTO_MAINTENANCE_RESULT.OK: {AUTO_MAINTENANCE_TYPE.REPAIR: '#messenger:serviceChannelMessages/autoRepairSuccess',
                                  AUTO_MAINTENANCE_TYPE.LOAD_AMMO: '#messenger:serviceChannelMessages/autoLoadSuccess',
                                  AUTO_MAINTENANCE_TYPE.EQUIP: '#messenger:serviceChannelMessages/autoEquipSuccess'},
     AUTO_MAINTENANCE_RESULT.NOT_PERFORMED: {AUTO_MAINTENANCE_TYPE.REPAIR: '#messenger:serviceChannelMessages/autoRepairSkipped',
                                             AUTO_MAINTENANCE_TYPE.LOAD_AMMO: '#messenger:serviceChannelMessages/autoLoadSkipped',
                                             AUTO_MAINTENANCE_TYPE.EQUIP: '#messenger:serviceChannelMessages/autoEquipSkipped'},
     AUTO_MAINTENANCE_RESULT.DISABLED_OPTION: {AUTO_MAINTENANCE_TYPE.REPAIR: '#messenger:serviceChannelMessages/autoRepairDisabledOption',
                                               AUTO_MAINTENANCE_TYPE.LOAD_AMMO: '#messenger:serviceChannelMessages/autoLoadDisabledOption',
                                               AUTO_MAINTENANCE_TYPE.EQUIP: '#messenger:serviceChannelMessages/autoEquipDisabledOption'},
     AUTO_MAINTENANCE_RESULT.NO_WALLET_SESSION: {AUTO_MAINTENANCE_TYPE.REPAIR: '#messenger:serviceChannelMessages/autoRepairErrorNoWallet',
                                                 AUTO_MAINTENANCE_TYPE.LOAD_AMMO: '#messenger:serviceChannelMessages/autoLoadErrorNoWallet',
                                                 AUTO_MAINTENANCE_TYPE.EQUIP: '#messenger:serviceChannelMessages/autoEquipErrorNoWallet'}}

    def isNotify(self):
        return True

    def format(self, message, *args):
        vehicleCompDescr = message.data.get('vehTypeCD', None)
        result = message.data.get('result', None)
        typeID = message.data.get('typeID', None)
        cost = message.data.get('cost', (0, 0))
        if vehicleCompDescr is not None and result is not None and typeID is not None:
            vt = vehicles_core.getVehicleType(vehicleCompDescr)
            if typeID == AUTO_MAINTENANCE_TYPE.REPAIR:
                formatMsgType = 'RepairSysMessage'
            else:
                formatMsgType = 'PurchaseForCreditsSysMessage' if cost[1] == 0 else 'PurchaseForGoldSysMessage'
            msg = i18n.makeString(self.__messages[result][typeID]) % vt.userString
            priorityLevel = NotificationPriorityLevel.MEDIUM
            if result == AUTO_MAINTENANCE_RESULT.OK:
                priorityLevel = NotificationPriorityLevel.LOW
                templateName = formatMsgType
            elif result == AUTO_MAINTENANCE_RESULT.NOT_ENOUGH_ASSETS:
                templateName = 'ErrorSysMessage'
            else:
                templateName = 'WarningSysMessage'
            if result == AUTO_MAINTENANCE_RESULT.OK:
                msg += formatPrice((abs(cost[0]), abs(cost[1])))
            formatted = g_settings.msgTemplates.format(templateName, {'text': msg})
            return (formatted, self._getGuiSettings(message, priorityLevel=priorityLevel))
        else:
            return (None, None)
            return


class AchievementFormatter(ServiceChannelFormatter):

    @async
    def __getRareTitle(self, rareID, callback):
        rare_achievements.getRareAchievementText(getClientLanguage(), rareID, lambda rID, text: callback(text.get('title')))

    def isNotify(self):
        return True

    def isAsync(self):
        return True

    @async
    @process
    def format(self, message, callback):
        yield lambda callback: callback(True)
        achievesList = list()
        achieves = message.data.get('popUpRecords')
        if achieves is not None:
            achievesList.extend([ i18n.makeString('#achievements:{0[1]:>s}'.format(name)) for name in achieves ])
        rares = message.data.get('rareAchievements')
        if rares is not None:
            unknownAchieves = 0
            for rareID in rares:
                if rareID > 0:
                    title = yield self.__getRareTitle(rareID)
                    if title is None:
                        unknownAchieves += 1
                    else:
                        achievesList.append(title)

            if unknownAchieves:
                achievesList.append(i18n.makeString('#system_messages:%s/title' % ('actionAchievements' if unknownAchieves > 1 else 'actionAchievement')))
        if not len(achievesList):
            callback((None, None))
            return
        else:
            formatted = g_settings.msgTemplates.format('achievementReceived', {'achieves': ', '.join(achievesList)})
            callback((formatted, self._getGuiSettings(message, 'achievementReceived')))
            return


class GoldReceivedFormatter(ServiceChannelFormatter):

    def format(self, message, *args):
        data = message.data
        gold = data.get('gold', None)
        transactionTime = data.get('date', None)
        if gold and transactionTime:
            formatted = g_settings.msgTemplates.format('goldReceived', {'date': TimeFormatter.getLongDatetimeFormat(transactionTime),
             'gold': BigWorld.wg_getGoldFormat(account_helpers.convertGold(gold))})
            return (formatted, self._getGuiSettings(message, 'goldReceived'))
        else:
            return (None, None)
            return


class GiftReceivedFormatter(ServiceChannelFormatter):
    __handlers = {'money': ('_GiftReceivedFormatter__formatMoneyGiftMsg', {1: 'creditsReceivedAsGift',
                2: 'goldReceivedAsGift',
                3: 'creditsAndGoldReceivedAsGift'}),
     'xp': ('_GiftReceivedFormatter__formatXPGiftMsg', 'xpReceivedAsGift'),
     'premium': ('_GiftReceivedFormatter__formatPremiumGiftMsg', 'premiumReceivedAsGift'),
     'item': ('_GiftReceivedFormatter__formatItemGiftMsg', 'itemReceivedAsGift'),
     'vehicle': ('_GiftReceivedFormatter__formatVehicleGiftMsg', 'vehicleReceivedAsGift')}

    def format(self, message, *args):
        data = message.data
        giftType = data.get('type')
        if giftType is not None:
            handlerName, templateKey = self.__handlers.get(giftType, (None, None))
            if handlerName is not None:
                formatted, templateKey = getattr(self, handlerName)(templateKey, data)
                return (formatted, self._getGuiSettings(message, templateKey))
        return (None, None)

    def __formatMoneyGiftMsg(self, keys, data):
        accCredits = data.get('credits', 0)
        gold = data.get('gold', 0)
        result = (None, '')
        ctx = {}
        idx = 0
        if accCredits > 0:
            idx |= 1
            ctx['credits'] = BigWorld.wg_getIntegralFormat(accCredits)
        if gold > 0:
            idx |= 2
            ctx['gold'] = BigWorld.wg_getGoldFormat(gold)
        if idx in keys:
            key = keys[idx]
            result = (g_settings.msgTemplates.format(keys[idx], ctx), key)
        return result

    def __formatXPGiftMsg(self, key, data):
        xp = data.get('amount', 0)
        result = None
        if xp > 0:
            result = g_settings.msgTemplates.format(key, ctx={'freeXP': BigWorld.wg_getIntegralFormat(xp)})
        return (result, key)

    def __formatPremiumGiftMsg(self, key, data):
        days = data.get('amount', 0)
        result = None
        if days > 0:
            result = g_settings.msgTemplates.format(key, ctx={'days': days})
        return (result, key)

    def __formatItemGiftMsg(self, key, data):
        amount = data.get('amount', 0)
        result = None
        itemTypeIdx = data.get('itemTypeIdx')
        itemCompactDesc = data.get('itemCD')
        if amount > 0 and itemTypeIdx is not None and itemCompactDesc is not None:
            result = g_settings.msgTemplates.format(key, ctx={'typeName': getTypeInfoByIndex(itemTypeIdx)['userString'],
             'itemName': vehicles_core.getDictDescr(itemCompactDesc)['userString'],
             'amount': amount})
        return (result, key)

    def __formatVehicleGiftMsg(self, key, data):
        vCompDesc = data.get('typeCD', None)
        result = None
        if vCompDesc is not None:
            result = g_settings.msgTemplates.format(key, ctx={'vehicleName': vehicles_core.getVehicleType(vCompDesc).userString})
        return (result, key)


class InvoiceReceivedFormatter(ServiceChannelFormatter):
    __assetHandlers = {INVOICE_ASSET.GOLD: '_InvoiceReceivedFormatter__formatAmount',
     INVOICE_ASSET.CREDITS: '_InvoiceReceivedFormatter__formatAmount',
     INVOICE_ASSET.PREMIUM: '_InvoiceReceivedFormatter__formatAmount',
     INVOICE_ASSET.FREE_XP: '_InvoiceReceivedFormatter__formatAmount',
     INVOICE_ASSET.DATA: '_InvoiceReceivedFormatter__formatData'}
    __operationTemplateKeys = {INVOICE_ASSET.GOLD: 'goldAccruedInvoiceReceived',
     INVOICE_ASSET.CREDITS: 'creditsAccruedInvoiceReceived',
     INVOICE_ASSET.PREMIUM: 'premiumAccruedInvoiceReceived',
     INVOICE_ASSET.FREE_XP: 'freeXpAccruedInvoiceReceived',
     INVOICE_ASSET.GOLD | 16: 'goldDebitedInvoiceReceived',
     INVOICE_ASSET.CREDITS | 16: 'creditsDebitedInvoiceReceived',
     INVOICE_ASSET.PREMIUM | 16: 'premiumDebitedInvoiceReceived',
     INVOICE_ASSET.FREE_XP | 16: 'freeXpDebitedInvoiceReceived'}
    __messageTemplateKeys = {INVOICE_ASSET.GOLD: 'goldInvoiceReceived',
     INVOICE_ASSET.CREDITS: 'creditsInvoiceReceived',
     INVOICE_ASSET.PREMIUM: 'premiumInvoiceReceived',
     INVOICE_ASSET.FREE_XP: 'freeXpInvoiceReceived',
     INVOICE_ASSET.DATA: 'dataInvoiceReceived'}
    __i18nPiecesString = i18n.makeString('#{0:>s}:serviceChannelMessages/invoiceReceived/pieces'.format(MESSENGER_I18N_FILE))
    __i18nCrewLvlString = i18n.makeString('#{0:>s}:serviceChannelMessages/invoiceReceived/crewLvl'.format(MESSENGER_I18N_FILE))

    def __getOperationTimeString(self, data):
        operationTime = data.get('at', None)
        if operationTime:
            fDatetime = TimeFormatter.getLongDatetimeFormat(time_utils.makeLocalServerTime(operationTime))
        else:
            fDatetime = 'N/A'
        return fDatetime

    def __getFinOperationString(self, assetType, amount):
        templateKey = 0 if amount > 0 else 16
        templateKey |= assetType
        ctx = {}
        if assetType == INVOICE_ASSET.GOLD:
            ctx['amount'] = BigWorld.wg_getGoldFormat(abs(amount))
        else:
            ctx['amount'] = BigWorld.wg_getIntegralFormat(abs(amount))
        return g_settings.htmlTemplates.format(self.__operationTemplateKeys[templateKey], ctx=ctx)

    def __getItemsString(self, items):
        accrued = []
        debited = []
        for itemCompactDescr, count in items.iteritems():
            if count:
                try:
                    item = vehicles_core.getDictDescr(itemCompactDescr)
                    itemString = '{0:>s} "{1:>s}" - {2:d} {3:>s}'.format(getTypeInfoByName(item['itemTypeName'])['userString'], item['userString'], abs(count), self.__i18nPiecesString)
                    if count > 0:
                        accrued.append(itemString)
                    else:
                        debited.append(itemString)
                except:
                    LOG_ERROR('itemCompactDescr can not parse ', itemCompactDescr)
                    LOG_CURRENT_EXCEPTION()

        result = ''
        if len(accrued):
            result = g_settings.htmlTemplates.format('itemsAccruedInvoiceReceived', ctx={'items': ', '.join(accrued)})
        if len(debited):
            if len(result):
                result += '<br/>'
            result += g_settings.htmlTemplates.format('itemsDebitedInvoiceReceived', ctx={'items': ', '.join(debited)})
        return result

    @classmethod
    def _getVehicleNames(cls, vehicles, exclude = None, validateNegative = True, showCrewLvl = True):
        addVehNames = []
        removeVehNames = []
        if exclude is None:
            exclude = []
        vehGetter = getattr(vehicles, 'get', None)
        for vehCompDescr in vehicles:
            if vehCompDescr is not None:
                isNegative = False
                if type(vehCompDescr) is types.IntType:
                    isNegative = vehCompDescr < 0
                    vehCompDescr = abs(vehCompDescr)
                if vehCompDescr in exclude:
                    continue
                crewLvl = 50
                if vehGetter is not None and callable(vehGetter) and showCrewLvl:
                    vehData = vehGetter(vehCompDescr, {})
                    crewLvl = getTankmanRoleLevel(vehData.get('crewLvl', 50), vehData.get('crewFreeXP', 0))
                try:
                    vehUserString = vehicles_core.getVehicleType(vehCompDescr).userString
                    if crewLvl > 50:
                        crewLvl = cls.__i18nCrewLvlString % crewLvl
                        vehUserString = '{0:>s} ({1:>s})'.format(vehUserString, crewLvl)
                    if isNegative and validateNegative:
                        removeVehNames.append(vehUserString)
                    else:
                        addVehNames.append(vehUserString)
                except:
                    LOG_ERROR('Wrong vehicle compact descriptor', vehCompDescr)
                    LOG_CURRENT_EXCEPTION()

        return (addVehNames, removeVehNames)

    @classmethod
    def _getVehiclesString(cls, vehicles, exclude = None, htmlTplPostfix = 'InvoiceReceived'):
        addVehNames, removeVehNames = cls._getVehicleNames(vehicles, exclude=exclude)
        result = ''
        if len(addVehNames):
            result = g_settings.htmlTemplates.format('vehiclesAccrued' + htmlTplPostfix, ctx={'vehicles': ', '.join(addVehNames)})
        if len(removeVehNames):
            if len(result):
                result += '<br/>'
            result += g_settings.htmlTemplates.format('vehiclesDebited' + htmlTplPostfix, ctx={'vehicles': ', '.join(removeVehNames)})
        return result

    @classmethod
    def _getComptnString(cls, comptnList, htmlTplPostfix = 'InvoiceReceived'):
        result = []
        html = g_settings.htmlTemplates
        for itemDict, comptn in comptnList:
            itemNames = []
            values = []
            items = itemDict.get('vehicles')
            if len(items):
                itemNames, _ = cls._getVehicleNames(items, validateNegative=False, showCrewLvl=False)
            gold = comptn.get('gold', 0)
            if gold > 0:
                values.append(html.format('goldCompensation' + htmlTplPostfix, ctx={'amount': BigWorld.wg_getGoldFormat(gold)}))
            accCredits = comptn.get('credits', 0)
            if accCredits > 0:
                values.append(html.format('creditsCompensation' + htmlTplPostfix, ctx={'amount': BigWorld.wg_getIntegralFormat(accCredits)}))
            if len(itemNames) and len(values):
                result.append(html.format('compensationFor' + htmlTplPostfix, ctx={'items': ', '.join(itemNames),
                 'compensation': ', '.join(values)}))

        return '<br/>'.join(result)

    def __getTankmenString(self, tmen):
        tmanUserStrings = []
        skillsConfig = tankmen.getSkillsConfig()
        for tmanCompDescr in tmen:
            try:
                tmanDescr = tankmen.TankmanDescr(tmanCompDescr)
                nationConfig = tankmen.getNationConfig(tmanDescr.nationID)
                tmanUserStrings.append('{0:>s} {1:>s} ({2:>s}, {3:>s}, {4:d}%)'.format(nationConfig['ranks'][tmanDescr.rankID].get('userString', ''), nationConfig['lastNames'][tmanDescr.lastNameID], skillsConfig.get(tmanDescr.role, {}).get('userString', ''), vehicles_core.g_cache.vehicle(tmanDescr.nationID, tmanDescr.vehicleTypeID).userString, tmanDescr.roleLevel))
            except:
                LOG_ERROR('Wrong tankman compact descriptor', tmanCompDescr)
                LOG_CURRENT_EXCEPTION()

        result = ''
        if len(tmanUserStrings):
            result = g_settings.htmlTemplates.format('tankmenInvoiceReceived', ctx={'tankman': ', '.join(tmanUserStrings)})
        return result

    def __getSlotsString(self, slots):
        if slots > 0:
            template = 'slotsAccruedInvoiceReceived'
        else:
            template = 'slotsDebitedInvoiceReceived'
        return g_settings.htmlTemplates.format(template, {'amount': BigWorld.wg_getIntegralFormat(abs(slots))})

    def __getL10nDescription(self, data):
        descr = ''
        lData = getLocalizedData(data.get('data', {}), 'localized_description', defVal=None)
        if lData:
            descr = i18n.encodeUtf8(html.escape(lData.get('description', u'')))
            if len(descr):
                descr = '<br/>' + descr
        return descr

    @classmethod
    def _makeComptnItemDict(cls, data):
        result = {}
        for items, comptn in data.get('compensation', []):
            for key, data in items.iteritems():
                exKey = 'ex_{0:>s}'.format(key)
                result.setdefault(exKey, [])
                result[exKey].extend(data)

        return result

    def __formatAmount(self, assetType, data):
        amount = data.get('amount', None)
        if amount is None:
            return
        else:
            return g_settings.msgTemplates.format(self.__messageTemplateKeys[assetType], ctx={'at': self.__getOperationTimeString(data),
             'desc': self.__getL10nDescription(data),
             'op': self.__getFinOperationString(assetType, amount)})

    def __formatData(self, assetType, data):
        dataEx = data.get('data', {})
        if dataEx is None or not len(dataEx):
            return
        else:
            operations = []
            comptnDict = self._makeComptnItemDict(data)
            gold = dataEx.get('gold')
            if gold is not None:
                operations.append(self.__getFinOperationString(INVOICE_ASSET.GOLD, gold))
            accCredtis = dataEx.get('credits')
            if accCredtis is not None:
                operations.append(self.__getFinOperationString(INVOICE_ASSET.CREDITS, accCredtis))
            freeXp = dataEx.get('freeXP')
            if freeXp is not None:
                operations.append(self.__getFinOperationString(INVOICE_ASSET.FREE_XP, freeXp))
            premium = dataEx.get('premium')
            if premium is not None:
                operations.append(self.__getFinOperationString(INVOICE_ASSET.PREMIUM, premium))
            items = dataEx.get('items', {})
            if items is not None and len(items) > 0:
                operations.append(self.__getItemsString(items))
            tmen = dataEx.get('tankmen', {})
            if tmen is not None and len(tmen) > 0:
                operations.append(self.__getTankmenString(tmen))
            vehicles = dataEx.get('vehicles', {})
            if vehicles is not None and len(vehicles) > 0:
                exclude = comptnDict.get('ex_vehicles', [])
                result = self._getVehiclesString(vehicles, exclude=exclude)
                if len(result):
                    operations.append(result)
            compensation = data.get('compensation', [])
            if len(compensation):
                comptnStr = self._getComptnString(compensation)
                if len(comptnStr):
                    operations.append(comptnStr)
            slots = dataEx.get('slots')
            if slots:
                operations.append(self.__getSlotsString(slots))
            return g_settings.msgTemplates.format(self.__messageTemplateKeys[assetType], ctx={'at': self.__getOperationTimeString(data),
             'desc': self.__getL10nDescription(data),
             'op': '<br/>'.join(operations)})

    def format(self, message, *args):
        LOG_DEBUG('invoiceReceived', message)
        data = message.data
        assetType = data.get('assetType', -1)
        handler = self.__assetHandlers.get(assetType)
        if handler is not None:
            formatted = getattr(self, handler)(assetType, data)
            return (formatted, self._getGuiSettings(message, self.__messageTemplateKeys[assetType]))
        else:
            return (None, None)
            return


class AdminMessageFormatter(ServiceChannelFormatter):

    def format(self, message, *args):
        data = decompressSysMessage(message.data)
        if data:
            dataType = type(data)
            text = ''
            if dataType in types.StringTypes:
                text = data
            elif dataType is types.DictType:
                text = getLocalizedData({'value': data}, 'value')
            if not text:
                LOG_ERROR('Text of message not found', message)
                return (None, None)
            formatted = g_settings.msgTemplates.format('adminMessage', {'text': text})
            return (formatted, self._getGuiSettings(message, 'adminMessage'))
        else:
            return (None, None)
            return None


class AccountTypeChangedFormatter(ServiceChannelFormatter):

    def format(self, message, *args):
        data = message.data
        isPremium = data.get('isPremium', None)
        expiryTime = data.get('expiryTime', None)
        result = (None, None)
        if isPremium is not None:
            accountTypeName = i18n.makeString('#menu:accountTypes/premium') if isPremium else i18n.makeString('#menu:accountTypes/base')
            expiryDatetime = TimeFormatter.getLongDatetimeFormat(expiryTime) if expiryTime else None
            if expiryDatetime:
                templateKey = 'accountTypeChangedWithExpiration'
                ctx = {'accType': accountTypeName,
                 'expiryTime': expiryDatetime}
            else:
                templateKey = 'accountTypeChanged'
                ctx = {'accType': accountTypeName}
            formatted = g_settings.msgTemplates.format(templateKey, ctx=ctx)
            result = (formatted, self._getGuiSettings(message, templateKey))
        return result


class PremiumActionFormatter(ServiceChannelFormatter):
    _templateKey = None

    def _getMessage(self, isPremium, expiryTime):
        return None

    def format(self, message, *args):
        data = message.data
        isPremium = data.get('isPremium', None)
        expiryTime = data.get('expiryTime', None)
        if isPremium is not None:
            return (self._getMessage(isPremium, expiryTime), self._getGuiSettings(message, self._templateKey))
        else:
            return (None, None)


class PremiumBoughtFormatter(PremiumActionFormatter):
    _templateKey = 'premiumBought'

    def _getMessage(self, isPremium, expiryTime):
        result = None
        if isPremium is True and expiryTime > 0:
            result = g_settings.msgTemplates.format(self._templateKey, ctx={'expiryTime': TimeFormatter.getLongDatetimeFormat(expiryTime)})
        return result


class PremiumExtendedFormatter(PremiumBoughtFormatter):
    _templateKey = 'premiumExtended'


class PremiumExpiredFormatter(PremiumActionFormatter):
    _templateKey = 'premiumExpired'

    def _getMessage(self, isPremium, expiryTime):
        result = None
        if isPremium is False:
            result = g_settings.msgTemplates.format(self._templateKey)
        return result


class WaresSoldFormatter(ServiceChannelFormatter):

    def isNotify(self):
        return True

    def format(self, message, *args):
        result = (None, None)
        if message.data:
            offer = offers._makeOutOffer(message.data)
            formatted = g_settings.msgTemplates.format('waresSoldAsGold', ctx={'srcWares': BigWorld.wg_getGoldFormat(offer.srcWares),
             'dstName': offer.dstName,
             'fee': offer.fee})
            result = (formatted, self._getGuiSettings(message, 'waresSoldAsGold'))
        return result


class WaresBoughtFormatter(ServiceChannelFormatter):

    def isNotify(self):
        return True

    def format(self, message, *args):
        result = (None, None)
        if message.data:
            offer = offers._makeInOffer(message.data)
            formatted = g_settings.msgTemplates.format('waresBoughtAsGold', ctx={'srcName': offer.srcName,
             'srcWares': BigWorld.wg_getGoldFormat(offer.srcWares)})
            result = (formatted, self._getGuiSettings(message, 'waresBoughtAsGold'))
        return result


class PrebattleFormatter(ServiceChannelFormatter):
    __battleTypeByPrebattleType = {PREBATTLE_TYPE.TOURNAMENT: 'tournament',
     PREBATTLE_TYPE.CLAN: 'clan'}
    _battleFinishReasonKeys = {}
    _defaultBattleFinishReasonKey = ('base', True)

    def isNotify(self):
        return True

    def _getIconId(self, prbType):
        iconId = 'BattleResultIcon'
        if prbType == PREBATTLE_TYPE.CLAN:
            iconId = 'ClanBattleResultIcon'
        elif prbType == PREBATTLE_TYPE.TOURNAMENT:
            iconId = 'TournamentBattleResultIcon'
        return iconId

    def _makeBattleTypeString(self, prbType):
        typeString = self.__battleTypeByPrebattleType.get(prbType, 'prebattle')
        key = '#{0:>s}:serviceChannelMessages/prebattle/battleType/{1:>s}'.format(MESSENGER_I18N_FILE, typeString)
        return i18n.makeString(key)

    def _makeDescriptionString(self, data, showBattlesCount = True):
        if data.has_key('localized_data') and len(data['localized_data']):
            description = getPrebattleFullDescription(data, escapeHtml=True)
        else:
            prbType = data.get('type')
            description = self._makeBattleTypeString(prbType)
        battlesLimit = data.get('battlesLimit', 0)
        if showBattlesCount and battlesLimit > 1:
            battlesCount = data.get('battlesCount')
            if battlesCount > 0:
                key = '#{0:>s}:serviceChannelMessages/prebattle/numberOfBattle'.format(MESSENGER_I18N_FILE)
                numberOfBattleString = i18n.makeString(key, battlesCount)
                description = '{0:>s} {1:>s}'.format(description, numberOfBattleString)
            else:
                LOG_WARNING('Invalid value of battlesCount ', battlesCount)
        return description

    def _getOpponentsString(self, opponents):
        first = i18n.encodeUtf8(opponents.get('1', {}).get('name', ''))
        second = i18n.encodeUtf8(opponents.get('2', {}).get('name', ''))
        result = ''
        if len(first) > 0 and len(second) > 0:
            result = g_settings.htmlTemplates.format('prebattleOpponents', ctx={'first': html.escape(first),
             'second': html.escape(second)})
        return result

    def _getBattleResultString(self, winner, team):
        result = 'undefined'
        if 3 > winner > -1 and team in (1, 2):
            if not winner:
                result = 'draftGame'
            else:
                result = 'defeat' if team != winner else 'win'
        return result

    def _makeBattleResultString(self, finishReason, winner, team):
        finishString, showResult = self._battleFinishReasonKeys.get(finishReason, self._defaultBattleFinishReasonKey)
        if showResult:
            resultString = self._getBattleResultString(winner, team)
            key = '#{0:>s}:serviceChannelMessages/prebattle/finish/{1:>s}/{2:>s}'.format(MESSENGER_I18N_FILE, finishString, resultString)
        else:
            key = '#{0:>s}:serviceChannelMessages/prebattle/finish/{1:>s}'.format(MESSENGER_I18N_FILE, finishString)
        return i18n.makeString(key)

    def _getTimeStamp(self, message):
        import time
        if message.createdAt is not None:
            result = time.mktime(message.createdAt.timetuple())
        else:
            LOG_WARNING('Invalid value of created_at = None')
            result = time.time()
        return result


class PrebattleArenaFinishFormatter(PrebattleFormatter):
    _battleFinishReasonKeys = {FINISH_REASON.TECHNICAL: ('technical', True),
     FINISH_REASON.FAILURE: ('failure', False),
     FINISH_REASON.UNKNOWN: ('failure', False)}

    def format(self, message, *args):
        LOG_DEBUG('prbArenaFinish', message)
        data = message.data
        prbType = data.get('type')
        winner = data.get('winner')
        team = data.get('team')
        wins = data.get('wins')
        finishReason = data.get('finishReason')
        if None in [prbType,
         winner,
         team,
         wins,
         finishReason]:
            return
        else:
            battleResult = self._makeBattleResultString(finishReason, winner, team)
            subtotal = ''
            battlesLimit = data.get('battlesLimit', 0)
            if battlesLimit > 1:
                battlesCount = data.get('battlesCount', -1)
                winsLimit = data.get('winsLimit', -1)
                if battlesCount == battlesLimit or winsLimit == wins[1] or winsLimit == wins[2]:
                    playerTeamWins = wins[team]
                    otherTeamWins = wins[2 if team == 1 else 1]
                    if winsLimit > 0 and playerTeamWins < winsLimit and otherTeamWins < winsLimit:
                        winner = None
                    elif playerTeamWins == otherTeamWins:
                        winner = 0
                    else:
                        winner = 1 if wins[1] > wins[2] else 2
                    sessionResult = self._makeBattleResultString(-1, winner, team)
                    subtotal = g_settings.htmlTemplates.format('prebattleTotal', ctx={'result': sessionResult,
                     'first': wins[1],
                     'second': wins[2]})
                else:
                    subtotal = g_settings.htmlTemplates.format('prebattleSubtotal', ctx={'first': wins[1],
                     'second': wins[2]})
            formatted = g_settings.msgTemplates.format('prebattleArenaFinish', ctx={'desc': self._makeDescriptionString(data),
             'opponents': self._getOpponentsString(data.get('opponents', {})),
             'result': battleResult,
             'subtotal': subtotal}, data={'timestamp': self._getTimeStamp(message),
             'icon': self._getIconId(prbType)})
            return (formatted, self._getGuiSettings(message, 'prebattleArenaFinish'))


class PrebattleKickFormatter(PrebattleFormatter):

    def format(self, message, *args):
        data = message.data
        result = (None, None)
        prbType = data.get('type')
        kickReason = data.get('kickReason')
        if prbType > 0 and kickReason > 0:
            ctx = {}
            key = '#system_messages:prebattle/kick/type/unknown'
            if prbType == PREBATTLE_TYPE.SQUAD:
                key = '#system_messages:prebattle/kick/type/squad'
            elif prbType == PREBATTLE_TYPE.COMPANY:
                key = '#system_messages:prebattle/kick/type/team'
            ctx['type'] = i18n.makeString(key)
            kickName = KICK_REASON_NAMES[kickReason]
            key = '#system_messages:prebattle/kick/reason/{0:>s}'.format(kickName)
            ctx['reason'] = i18n.makeString(key)
            formatted = g_settings.msgTemplates.format('prebattleKick', ctx=ctx)
            result = (formatted, self._getGuiSettings(message, 'prebattleKick'))
        return result


class PrebattleDestructionFormatter(PrebattleFormatter):
    _battleFinishReasonKeys = {KICK_REASON.ARENA_CREATION_FAILURE: ('failure', False),
     KICK_REASON.AVATAR_CREATION_FAILURE: ('failure', False),
     KICK_REASON.VEHICLE_CREATION_FAILURE: ('failure', False),
     KICK_REASON.PREBATTLE_CREATION_FAILURE: ('failure', False),
     KICK_REASON.BASEAPP_CRASH: ('failure', False),
     KICK_REASON.CELLAPP_CRASH: ('failure', False),
     KICK_REASON.UNKNOWN_FAILURE: ('failure', False),
     KICK_REASON.CREATOR_LEFT: ('creatorLeft', False),
     KICK_REASON.PLAYERKICK: ('playerKick', False),
     KICK_REASON.TIMEOUT: ('timeout', False)}

    def format(self, message, *args):
        LOG_DEBUG('prbDestruction', message)
        data = message.data
        prbType = data.get('type')
        team = data.get('team')
        wins = data.get('wins')
        kickReason = data.get('kickReason')
        if None in [prbType,
         team,
         wins,
         kickReason]:
            return (None, None)
        else:
            playerTeamWins = wins[team]
            otherTeamWins = wins[2 if team == 1 else 1]
            winsLimit = data.get('winsLimit')
            if winsLimit > 0 and playerTeamWins < winsLimit and otherTeamWins < winsLimit:
                winner = None
            elif playerTeamWins == otherTeamWins:
                winner = 0
            else:
                winner = 1 if wins[1] > wins[2] else 2
            battleResult = self._makeBattleResultString(kickReason, winner, team)
            total = ''
            if data.get('battlesLimit', 0) > 1:
                total = '({0:d}:{1:d})'.format(wins[1], wins[2])
            formatted = g_settings.msgTemplates.format('prebattleDestruction', ctx={'desc': self._makeDescriptionString(data, showBattlesCount=False),
             'opponents': self._getOpponentsString(data.get('opponents', {})),
             'result': battleResult,
             'total': total}, data={'timestamp': self._getTimeStamp(message),
             'icon': self._getIconId(prbType)})
            return (formatted, self._getGuiSettings(message, 'prebattleDestruction'))


class VehCamouflageTimedOutFormatter(ServiceChannelFormatter):

    def isNotify(self):
        return True

    def format(self, message, *args):
        data = message.data
        formatted = None
        vehTypeCompDescr = data.get('vehTypeCompDescr')
        if vehTypeCompDescr is not None:
            vType = vehicles_core.getVehicleType(vehTypeCompDescr)
            if vType is not None:
                formatted = g_settings.msgTemplates.format('vehCamouflageTimedOut', ctx={'vehicleName': vType.userString})
        return (formatted, self._getGuiSettings(message, 'vehCamouflageTimedOut'))


class VehEmblemTimedOutFormatter(ServiceChannelFormatter):

    def isNotify(self):
        return True

    def format(self, message, *args):
        data = message.data
        formatted = None
        vehTypeCompDescr = data.get('vehTypeCompDescr')
        if vehTypeCompDescr is not None:
            vType = vehicles_core.getVehicleType(vehTypeCompDescr)
            if vType is not None:
                formatted = g_settings.msgTemplates.format('vehEmblemTimedOut', ctx={'vehicleName': vType.userString})
        return (formatted, self._getGuiSettings(message, 'vehEmblemTimedOut'))


class VehInscriptionTimedOutFormatter(ServiceChannelFormatter):

    def isNotify(self):
        return True

    def format(self, message, *args):
        data = message.data
        formatted = None
        vehTypeCompDescr = data.get('vehTypeCompDescr')
        if vehTypeCompDescr is not None:
            vType = vehicles_core.getVehicleType(vehTypeCompDescr)
            if vType is not None:
                formatted = g_settings.msgTemplates.format('vehInscriptionTimedOut', ctx={'vehicleName': vType.userString})
        return (formatted, self._getGuiSettings(message, 'vehInscriptionTimedOut'))


class ConverterFormatter(ServiceChannelFormatter):

    def __i18nValue(self, key, isReceived, **kwargs):
        key = ('%sReceived' if isReceived else '%sWithdrawn') % key
        key = '#messenger:serviceChannelMessages/sysMsg/converter/%s' % key
        return i18n.makeString(key) % kwargs

    def __vehName(self, vehCompDescr):
        return vehicles_core.getVehicleType(abs(vehCompDescr)).userString

    def format(self, message, *args):
        data = message.data
        text = []
        if data.get('playerInscriptions'):
            text.append(i18n.makeString('#messenger:serviceChannelMessages/sysMsg/converter/inscriptions'))
        if data.get('playerEmblems'):
            text.append(i18n.makeString('#messenger:serviceChannelMessages/sysMsg/converter/emblems'))
        if data.get('camouflages'):
            text.append(i18n.makeString('#messenger:serviceChannelMessages/sysMsg/converter/camouflages'))
        vehicles = data.get('vehicles')
        if vehicles:
            vehiclesReceived = [ self.__vehName(cd) for cd in vehicles if cd > 0 ]
            if len(vehiclesReceived):
                text.append(self.__i18nValue('vehicles', True, vehicles=', '.join(vehiclesReceived)))
            vehiclesWithdrawn = [ self.__vehName(cd) for cd in vehicles if cd < 0 ]
            if len(vehiclesWithdrawn):
                text.append(self.__i18nValue('vehicles', False, vehicles=', '.join(vehiclesWithdrawn)))
        slots = data.get('slots')
        if slots:
            text.append(self.__i18nValue('slots', slots > 0, slots=BigWorld.wg_getIntegralFormat(abs(slots))))
        gold = data.get('gold')
        if gold:
            text.append(self.__i18nValue('gold', gold > 0, gold=BigWorld.wg_getGoldFormat(abs(gold))))
        accCredits = data.get('credits')
        if accCredits:
            text.append(self.__i18nValue('credits', accCredits > 0, credits=BigWorld.wg_getIntegralFormat(abs(accCredits))))
        freeXP = data.get('freeXP')
        if freeXP:
            text.append(self.__i18nValue('freeXP', freeXP > 0, freeXP=BigWorld.wg_getIntegralFormat(abs(freeXP))))
        formatted = g_settings.msgTemplates.format('ConverterNotify', {'text': '<br/>'.join(text)})
        return (formatted, self._getGuiSettings(message, 'ConverterNotify'))


class ClientSysMessageFormatter(ServiceChannelFormatter):
    __templateKey = '%sSysMessage'

    def format(self, data, *args):
        if len(args):
            msgType = args[0][0]
        else:
            msgType = 'Error'
        templateKey = self.__templateKey % msgType
        formatted = g_settings.msgTemplates.format(templateKey, ctx={'text': data})
        return (formatted, self._getGuiSettings(args, templateKey))

    def _getGuiSettings(self, data, key = None, priorityLevel = None):
        if type(data) is types.TupleType and len(data):
            auxData = data[0][:]
        else:
            auxData = []
        if priorityLevel is None:
            priorityLevel = g_settings.msgTemplates.priority(key)
        else:
            priorityLevel = NotificationPriorityLevel.MEDIUM
        return NotificationGuiSettings(self.isNotify(), priorityLevel=priorityLevel, auxData=auxData)


class PremiumAccountExpiryFormatter(ClientSysMessageFormatter):

    def format(self, data, *args):
        formatted = g_settings.msgTemplates.format('durationOfPremiumAccountExpires', ctx={'expiryTime': TimeFormatter.getLongDatetimeFormat(data)})
        return (formatted, self._getGuiSettings(args, 'durationOfPremiumAccountExpires'))


class AOGASNotifyFormatter(ClientSysMessageFormatter):

    def format(self, data, *args):
        formatted = g_settings.msgTemplates.format('AOGASNotify', {'text': i18n.makeString('#AOGAS:{0:>s}'.format(data.name()))})
        return (formatted, self._getGuiSettings(args, 'AOGASNotify'))


class VehicleTypeLockExpired(ServiceChannelFormatter):

    def format(self, message, *args):
        result = (None, None)
        if message.data:
            ctx = {}
            vehTypeCompDescr = message.data.get('vehTypeCompDescr')
            if vehTypeCompDescr is None:
                templateKey = 'vehiclesAllLockExpired'
            else:
                templateKey = 'vehicleLockExpired'
                ctx['vehicleName'] = vehicles_core.getVehicleType(vehTypeCompDescr).userString
            formatted = g_settings.msgTemplates.format(templateKey, ctx=ctx)
            result = (formatted, self._getGuiSettings(message, 'vehicleLockExpired'))
        return result


class ServerDowntimeCompensation(ServiceChannelFormatter):
    __templateKey = 'serverDowntimeCompensation'

    def format(self, message, *args):
        result = (None, None)
        subjects = ''
        data = message.data
        if data is not None:
            for key, value in data.items():
                if value:
                    if len(subjects) > 0:
                        subjects += ', '
                    subjects += i18n.makeString('#%s:serviceChannelMessages/' % MESSENGER_I18N_FILE + self.__templateKey + '/' + key)

            if len(subjects) > 0:
                formatted = g_settings.msgTemplates.format(self.__templateKey, ctx={'text': i18n.makeString('#%s:serviceChannelMessages/' % MESSENGER_I18N_FILE + self.__templateKey) % subjects})
                result = (formatted, self._getGuiSettings(message, self.__templateKey))
        return result


class ActionNotificationFormatter(ClientSysMessageFormatter):
    __templateKey = 'action%s'

    def format(self, message, *args):
        result = (None, None)
        data = message.get('data')
        if data:
            templateKey = self.__templateKey % message.get('state', '')
            formatted = g_settings.msgTemplates.format(templateKey, ctx={'text': data}, data={'icon': message.get('type', '')})
            result = (formatted, self._getGuiSettings(args, templateKey))
        return result


class BattleTutorialResultsFormatter(ClientSysMessageFormatter):
    __resultKeyWithBonuses = 'battleTutorialResBonuses'
    __resultKeyWoBonuses = 'battleTutorialResWoBonuses'

    def isNotify(self):
        return True

    def format(self, data, *args):
        LOG_DEBUG('message data', data)
        finishReason = data.get('finishReason', -1)
        resultKey = data.get('resultKey', None)
        finishKey = data.get('finishKey', None)
        if finishReason > -1 and resultKey and finishKey:
            resultString = i18n.makeString('#{0:>s}:serviceChannelMessages/battleTutorial/results/{1:>s}'.format(MESSENGER_I18N_FILE, resultKey))
            reasonString = i18n.makeString('#{0:>s}:serviceChannelMessages/battleTutorial/reasons/{1:>s}'.format(MESSENGER_I18N_FILE, finishKey))
            arenaTypeID = data.get('arenaTypeID', 0)
            arenaName = 'N/A'
            if arenaTypeID > 0:
                arenaName = ArenaType.g_cache[arenaTypeID].name
            vTypeCD = data.get('vTypeCD', None)
            vName = 'N/A'
            if vTypeCD is not None:
                vName = vehicles_core.getVehicleType(vTypeCD).userString
            ctx = {'result': resultString,
             'reason': reasonString,
             'arenaName': i18n.makeString(arenaName),
             'vehicleName': vName,
             'freeXP': '0',
             'credits': '0'}
            freeXP = 0
            credits_ = 0
            chapters = data.get('chapters', [])
            for chapter in chapters:
                if chapter.get('received', False):
                    bonus = chapter.get('bonus', {})
                    freeXP += bonus.get('freeXP', 0)
                    credits_ += bonus.get('credits', 0)

            if freeXP:
                ctx['freeXP'] = BigWorld.wg_getIntegralFormat(freeXP)
            if credits_:
                ctx['credits'] = BigWorld.wg_getIntegralFormat(credits_)
            all_ = data.get('areAllBonusesReceived', False)
            if all_ and credits_ <= 0 and freeXP <= 0:
                key = self.__resultKeyWoBonuses
            else:
                key = self.__resultKeyWithBonuses
            import time
            startedAtTime = data.get('startedAt', time.time())
            formatted = g_settings.msgTemplates.format(key, ctx=ctx, data={'timestamp': startedAtTime,
             'savedID': data.get('arenaUniqueID', 0)})
            return (formatted, self._getGuiSettings(args, key))
        else:
            return (None, None)
            return


class TokenQuestsFormatter(ServiceChannelFormatter):

    def __init__(self, asBattleFormatter = False):
        self._asBattleFormatter = asBattleFormatter

    __questsTemplateKey = 'battleQuests'

    def format(self, message, *args):
        formatted, settings = (None, None)
        fmt = self._formatQuestAchieves(message)
        if fmt is not None:
            settings = self._getGuiSettings(message, 'tokenQuests')
            formatted = g_settings.msgTemplates.format('tokenQuests', {'achieves': self._formatQuestAchieves(message)})
        return (formatted, settings)

    def _formatQuestAchieves(self, message):
        data = message.data
        result = []
        if not self._asBattleFormatter:
            gold = data.get('gold', 0)
            if gold:
                result.append(self.__makeQuestsAchieve('battleQuestsGold', gold=BigWorld.wg_getIntegralFormat(gold)))
        premium = data.get('premium', 0)
        if premium:
            result.append(self.__makeQuestsAchieve('battleQuestsPremium', days=premium))
        if not self._asBattleFormatter:
            freeXP = data.get('freeXP', 0)
            if freeXP:
                result.append(self.__makeQuestsAchieve('battleQuestsFreeXP', freeXP=BigWorld.wg_getIntegralFormat(freeXP)))
        vehicles = data.get('vehicles', {})
        if vehicles is not None and len(vehicles) > 0:
            exclude = InvoiceReceivedFormatter._makeComptnItemDict(data).get('ex_vehicles', [])
            msg = InvoiceReceivedFormatter._getVehiclesString(vehicles, exclude=exclude, htmlTplPostfix='QuestsReceived')
            if len(msg):
                result.append(msg)
        compensation = data.get('compensation', [])
        if len(compensation):
            msg = InvoiceReceivedFormatter._getComptnString(compensation, htmlTplPostfix='QuestsReceived')
            if len(msg):
                result.append('<br/>' + msg)
        if not self._asBattleFormatter:
            creditsVal = data.get('credits', 0)
            if creditsVal:
                result.append(self.__makeQuestsAchieve('battleQuestsCredits', credits=BigWorld.wg_getIntegralFormat(creditsVal)))
        slots = data.get('slots', 0)
        if slots:
            result.append(self.__makeQuestsAchieve('battleQuestsSlots', slots=BigWorld.wg_getIntegralFormat(slots)))
        items = data.get('items', {})
        itemsNames = []
        for intCD, count in items.iteritems():
            itemDescr = vehicles_core.getDictDescr(intCD)
            itemsNames.append(i18n.makeString('#messenger:serviceChannelMessages/battleResults/quests/items/name', name=itemDescr['userString'], count=BigWorld.wg_getIntegralFormat(count)))

        if len(itemsNames):
            result.append(self.__makeQuestsAchieve('battleQuestsItems', names=', '.join(itemsNames)))
        berths = data.get('berths', 0)
        if berths:
            result.append(self.__makeQuestsAchieve('battleQuestsBerths', berths=BigWorld.wg_getIntegralFormat(berths)))
        if not self._asBattleFormatter:
            achieves = data.get('popUpRecords', [])
            achievesNames = set()
            for recordIdx, value in achieves:
                factory = getAchievementFactory(DB_ID_TO_RECORD[recordIdx])
                if factory is not None:
                    a = factory.create(value=int(value))
                    if a is not None:
                        achievesNames.add(a.getUserName())

            if len(achievesNames):
                result.append(self.__makeQuestsAchieve('battleQuestsPopUps', achievements=', '.join(achievesNames)))
        if len(result):
            return ''.join(result)
        else:
            return

    @classmethod
    def __makeQuestsAchieve(cls, key, **kwargs):
        return g_settings.htmlTemplates.format(key, kwargs)


class HistoricalCostsReservedFormatter(ServiceChannelFormatter):
    __htmlKeys = {1: 'historicalGoldReturn',
     2: 'historicalCreditsReturn',
     17: 'historicalGoldDebited',
     18: 'historicalCreditsDebited'}

    def format(self, message, *args):
        data = message.data
        accCredits, gold = (0, 0)
        if 'gold' in data:
            gold = data['gold']
        if 'credits' in data:
            accCredits = data['credits']
        if accCredits or gold:
            resource = []
            priority = NotificationPriorityLevel.LOW
            templateKey = self.__getTemplateKey(1, gold)
            if templateKey:
                priority = NotificationPriorityLevel.MEDIUM
                resource.append(g_settings.htmlTemplates.format(templateKey, ctx={'gold': BigWorld.wg_getGoldFormat(abs(gold))}))
            templateKey = self.__getTemplateKey(2, accCredits)
            if templateKey:
                resource.append(g_settings.htmlTemplates.format(templateKey, ctx={'credits': BigWorld.wg_getIntegralFormat(abs(accCredits))}))
            if len(resource):
                templateName = 'historicalCostsReserved'
                formatted = g_settings.msgTemplates.format(templateName, ctx={'resource': '<br/>'.join(resource)})
                settings = self._getGuiSettings(message, templateName, priority)
                return (formatted, settings)
            else:
                return (None, None)
        else:
            return (None, None)
        return None

    def __getTemplateKey(self, primary, value):
        if not value:
            return
        else:
            key = primary
            if value < 0:
                key |= 16
            result = None
            if key in self.__htmlKeys:
                result = self.__htmlKeys[key]
            return result


class NCMessageFormatter(ServiceChannelFormatter):
    __templateKeyFormat = 'notificationsCenterMessage_{0}'

    def format(self, message, *args):
        LOG_DEBUG('Message has received from notification center', message)
        data = z_loads(message.data)
        if not data:
            return (None, None)
        elif 'body' not in data or not data['body']:
            return (None, None)
        else:
            templateKey = self.__getTemplateKey(data)
            priority = self.__getGuiPriority(data)
            topic = self.__getTopic(data)
            body = self.__getBody(data)
            settings = self._getGuiSettings(message, templateKey, priority)
            msgType = data['type']
            if msgType == NC_MESSAGE_TYPE.POLL:
                if not GUI_SETTINGS.isPollEnabled:
                    return (None, None)
                if not self.__fetchPollData(data, settings):
                    return (None, None)
            formatted = g_settings.msgTemplates.format(templateKey, ctx={'topic': topic,
             'body': body})
            return (formatted, settings)

    def __getTemplateKey(self, data):
        if 'type' in data:
            msgType = data['type']
            if msgType not in NC_MESSAGE_TYPE.RANGE:
                LOG_WARNING('Type of message is not valid, uses default type', msgType)
                msgType = NC_MESSAGE_TYPE.INFO
        else:
            msgType = NC_MESSAGE_TYPE.INFO
        return self.__templateKeyFormat.format(msgType)

    def __getGuiPriority(self, data):
        priority = NC_MESSAGE_PRIORITY.DEFAULT
        if 'priority' in data:
            priority = data['priority']
            if priority not in NC_MESSAGE_PRIORITY.ORDER:
                LOG_WARNING('Priority of message is not valid, uses default priority', priority)
                priority = NC_MESSAGE_PRIORITY.DEFAULT
        return NotificationPriorityLevel.convertFromNC(priority)

    def __getTopic(self, data):
        topic = ''
        if 'topic' in data:
            topic = i18n.encodeUtf8(data['topic'])
        if len(topic):
            topic = g_settings.htmlTemplates.format('notificationsCenterTopic', ctx={'topic': topic})
        return topic

    def __getBody(self, data):
        body = i18n.encodeUtf8(data['body'])
        if 'context' in data:
            body = body % self.__formatContext(data['context'])
        return body

    def __fetchPollData(self, data, settings):
        result = False
        if 'link' in data and data['link']:
            if 'topic' in data:
                topic = i18n.encodeUtf8(data['topic'])
            else:
                topic = ''
            settings.auxData = [data['link'], topic]
            result = True
        return result

    def __formatContext(self, ctx):
        result = {}
        if type(ctx) is not types.DictType:
            LOG_ERROR('Context is invalid', ctx)
            return result
        getItemFormat = NCContextItemFormatter.getItemFormat
        for key, item in ctx.iteritems():
            if len(item) > 1:
                itemType, itemValue = item[0:2]
                result[key] = getItemFormat(itemType, itemValue)
            else:
                LOG_ERROR('Context item is invalid', item)
                result[key] = str(item)

        return result


class ClanMessageFormatter(ServiceChannelFormatter):
    __templates = {SYS_MESSAGE_CLAN_EVENT.LEFT_CLAN: 'clanMessageWarning'}

    def format(self, message, *args):
        LOG_DEBUG('Message has received from clan', message)
        data = message.data
        if data and 'event' in data:
            event = data['event']
            templateKey = self.__templates.get(event)
            message = i18n.makeString('#messenger:serviceChannelMessages/clan/%s' % SYS_MESSAGE_CLAN_EVENT_NAMES[event])
            formatted = g_settings.msgTemplates.format(templateKey, ctx={'message': message})
            settings = self._getGuiSettings(message, templateKey)
            return (formatted, settings)
        else:
            return (None, None)
            return None


class FortMessageFormatter(ServiceChannelFormatter):
    __templates = {SYS_MESSAGE_FORT_EVENT.FORT_READY: 'fortMessageWarning',
     SYS_MESSAGE_FORT_EVENT.RESERVE_ACTIVATED: 'fortMessageWarning',
     SYS_MESSAGE_FORT_EVENT.RESERVE_EXPIRED: 'fortMessageWarning',
     SYS_MESSAGE_FORT_EVENT.RESERVE_PRODUCED: 'fortMessageWarning',
     SYS_MESSAGE_FORT_EVENT.STORAGE_OVERFLOW: 'fortMessageWarning',
     SYS_MESSAGE_FORT_EVENT.ORDER_CANCELED: 'fortMessageWarning'}

    def __init__(self):
        super(FortMessageFormatter, self).__init__()
        self.__messagesFormatters = {SYS_MESSAGE_FORT_EVENT.FORT_READY: BoundMethodWeakref(self._simpleMessage),
         SYS_MESSAGE_FORT_EVENT.RESERVE_ACTIVATED: BoundMethodWeakref(self._reserveActivatedMessage),
         SYS_MESSAGE_FORT_EVENT.RESERVE_EXPIRED: BoundMethodWeakref(self._reserveExpiredMessage),
         SYS_MESSAGE_FORT_EVENT.RESERVE_PRODUCED: BoundMethodWeakref(self._reserveProducedMessage),
         SYS_MESSAGE_FORT_EVENT.STORAGE_OVERFLOW: BoundMethodWeakref(self._storageOverflowMessage),
         SYS_MESSAGE_FORT_EVENT.ORDER_CANCELED: BoundMethodWeakref(self._orderCanceledMessage)}

    def format(self, message, *args):
        LOG_DEBUG('Message has received from clan', message)
        data = message.data
        if data and 'event' in data:
            event = data['event']
            templateKey = self.__templates.get(event)
            messageSting = self.__messagesFormatters[event](data)
            formatted = g_settings.msgTemplates.format(templateKey, ctx={'message': messageSting})
            settings = self._getGuiSettings(message, templateKey)
            return (formatted, settings)
        else:
            return (None,)
            return None

    def _simpleMessage(self, data):
        event = data['event']
        return i18n.makeString('#messenger:serviceChannelMessages/fort/%s' % SYS_MESSAGE_FORT_EVENT_NAMES[event])

    def _reserveActivatedMessage(self, data):
        event = data['event']
        orderTypeID = data['orderTypeID']
        from gui.Scaleform.daapi.view.lobby.fortifications.fort_utils.FortViewHelper import FortViewHelper
        order = i18n.makeString('#fortifications:General/orderType/%s' % FortViewHelper.UI_ORDERS_BIND[orderTypeID])
        from gui.Scaleform.daapi.view.lobby.fortifications.fort_utils import fort_text
        timeExpiration = fort_text.getTimeDurationStr(time_utils.getTimeDeltaFromNow(time_utils.makeLocalServerTime(data['timeExpiration'])))
        return i18n.makeString('#messenger:serviceChannelMessages/fort/%s' % SYS_MESSAGE_FORT_EVENT_NAMES[event], order=order, time=timeExpiration)

    def _reserveExpiredMessage(self, data):
        event = data['event']
        orderTypeID = data['orderTypeID']
        from gui.Scaleform.daapi.view.lobby.fortifications.fort_utils.FortViewHelper import FortViewHelper
        order = i18n.makeString('#fortifications:General/orderType/%s' % FortViewHelper.UI_ORDERS_BIND[orderTypeID])
        return i18n.makeString('#messenger:serviceChannelMessages/fort/%s' % SYS_MESSAGE_FORT_EVENT_NAMES[event], order=order)

    def _reserveProducedMessage(self, data):
        event = data['event']
        orderTypeID = data['orderTypeID']
        count = data['count']
        from gui.Scaleform.daapi.view.lobby.fortifications.fort_utils.FortViewHelper import FortViewHelper
        order = i18n.makeString('#fortifications:General/orderType/%s' % FortViewHelper.UI_ORDERS_BIND[orderTypeID])
        return i18n.makeString('#messenger:serviceChannelMessages/fort/%s' % SYS_MESSAGE_FORT_EVENT_NAMES[event], order=order, count=count)

    def _storageOverflowMessage(self, data):
        event = data['event']
        buildTypeID = data['buildTypeID']
        from gui.Scaleform.daapi.view.lobby.fortifications.fort_utils.FortViewHelper import FortViewHelper
        building = i18n.makeString('#fortifications:Buildings/buildingName/%s' % FortViewHelper.UI_BUILDINGS_BIND[buildTypeID])
        return i18n.makeString('#messenger:serviceChannelMessages/fort/%s' % SYS_MESSAGE_FORT_EVENT_NAMES[event], building=building)

    def _orderCanceledMessage(self, data):
        event = data['event']
        buildTypeID = data['buildTypeID']
        from gui.Scaleform.daapi.view.lobby.fortifications.fort_utils.FortViewHelper import FortViewHelper
        building = i18n.makeString('#fortifications:Buildings/buildingName/%s' % FortViewHelper.UI_BUILDINGS_BIND[buildTypeID])
        import fortified_regions
        order = i18n.makeString('#fortifications:General/orderType/%s' % FortViewHelper.UI_ORDERS_BIND[fortified_regions.g_cache.buildings[buildTypeID].orderType])
        return i18n.makeString('#messenger:serviceChannelMessages/fort/%s' % SYS_MESSAGE_FORT_EVENT_NAMES[event], building=building, order=order)

    def _reattachedToBaseMessage(self, data):
        event = data['event']
        from gui.Scaleform.daapi.view.lobby.fortifications.fort_utils.FortViewHelper import FortViewHelper
        building = i18n.makeString('#fortifications:Buildings/buildingName/%s' % FortViewHelper.UI_BUILDINGS_BIND[FORT_BUILDING_TYPE.MILITARY_BASE])
        return i18n.makeString('#messenger:serviceChannelMessages/fort/%s' % SYS_MESSAGE_FORT_EVENT_NAMES[event], building=building)

    def _storageOverflowMessage(self, data):
        event = data['event']
        buildTypeID = data['buildTypeID']
        from gui.Scaleform.daapi.view.lobby.fortifications.fort_utils.FortViewHelper import FortViewHelper
        building = i18n.makeString('#fortifications:Buildings/buildingName/%s' % FortViewHelper.UI_BUILDINGS_BIND[buildTypeID])
        return i18n.makeString('#messenger:serviceChannelMessages/fort/%s' % SYS_MESSAGE_FORT_EVENT_NAMES[event], building=building)

    def _orderCanceledMessage(self, data):
        event = data['event']
        buildTypeID = data['buildTypeID']
        from gui.Scaleform.daapi.view.lobby.fortifications.fort_utils.FortViewHelper import FortViewHelper
        import fortified_regions
        building = i18n.makeString('#fortifications:Buildings/buildingName/%s' % FortViewHelper.UI_BUILDINGS_BIND[buildTypeID])
        order = i18n.makeString('#fortifications:General/orderType/%s' % FortViewHelper.UI_ORDERS_BIND[fortified_regions.g_cache.buildings[buildTypeID].orderType])
        return i18n.makeString('#messenger:serviceChannelMessages/fort/%s' % SYS_MESSAGE_FORT_EVENT_NAMES[event], building=building, order=order)
