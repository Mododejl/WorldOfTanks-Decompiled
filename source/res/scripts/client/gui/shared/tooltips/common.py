# Embedded file name: scripts/client/gui/shared/tooltips/common.py
import cPickle
from collections import namedtuple
from operator import methodcaller
import pickle
import types
import BigWorld
import constants
import ArenaType
import fortified_regions
import math
from gui.Scaleform.daapi.view.lobby.profile.ProfileUtils import ProfileUtils
from gui.Scaleform.locale.RES_ICONS import RES_ICONS
from gui.Scaleform.managers.UtilsManager import ImageUrlProperties
from gui.Scaleform.framework.managers.TextManager import TextType, TextIcons
from gui.prb_control import getBattleID
from gui.shared.formatters.time_formatters import getRentLeftTimeStr
from predefined_hosts import g_preDefinedHosts
from constants import PREBATTLE_TYPE
from debug_utils import LOG_WARNING, LOG_DEBUG
from helpers import i18n, time_utils
from helpers.i18n import makeString as ms
from gui.Scaleform.daapi.view.lobby.fortifications.fort_utils.FortViewHelper import FortViewHelper
from gui.Scaleform.locale.FORTIFICATIONS import FORTIFICATIONS as FORT
from CurrentVehicle import g_currentVehicle
from UnitBase import SORTIE_DIVISION
from gui import g_htmlTemplates, makeHtmlString, game_control
from gui.Scaleform.daapi.view.lobby.fortifications.components.sorties_dps import makeDivisionData
from gui.Scaleform.daapi.view.lobby.fortifications.fort_utils import fort_formatters
from gui.Scaleform.locale.FORTIFICATIONS import FORTIFICATIONS as I18N_FORTIFICATIONS
from gui.Scaleform.locale.ITEM_TYPES import ITEM_TYPES
from gui.Scaleform.locale.TOOLTIPS import TOOLTIPS
from gui.Scaleform.daapi.view.lobby.rally.vo_converters import makeBuildingIndicatorsVO
from gui.prb_control.items.unit_items import SupportedRosterSettings
from gui.shared.gui_items import GUI_ITEM_TYPE
from gui.shared.utils import findFirst, CONST_CONTAINER
from gui.shared.ClanCache import g_clanCache
from gui.shared.tooltips import ToolTipBaseData, TOOLTIP_TYPE, ACTION_TOOLTIPS_TYPE
from gui.shared import g_eventsCache, g_itemsCache
from gui.Scaleform.daapi.view.lobby.customization import CAMOUFLAGES_KIND_TEXTS, CAMOUFLAGES_NATIONS_TEXTS
from gui.Scaleform.locale.VEHICLE_CUSTOMIZATION import VEHICLE_CUSTOMIZATION
from gui.Scaleform.genConsts.CUSTOMIZATION_ITEM_TYPE import CUSTOMIZATION_ITEM_TYPE
from gui.Scaleform.daapi.view.lobby.customization import CustomizationHelper
from items import vehicles

class IgrTooltipData(ToolTipBaseData):

    def __init__(self, context):
        super(IgrTooltipData, self).__init__(context, TOOLTIP_TYPE.IGR)

    def getDisplayableData(self, *args):
        qLabels, qProgress = [], []
        premVehQuests = []
        if game_control.g_instance.igr.getRoomType() in (constants.IGR_TYPE.PREMIUM, constants.IGR_TYPE.BASE):
            quests = g_eventsCache.getQuests()
            for q in quests.itervalues():
                if game_control.g_instance.igr.getRoomType() == constants.IGR_TYPE.PREMIUM:
                    template = g_htmlTemplates['html_templates:lobby/tooltips']['igr_quest']
                    if q.accountReqs.hasIGRCondition() and not q.hasPremIGRVehBonus():
                        metaList = q.getBonuses('meta')
                        if len(metaList):
                            qLabels.append(metaList[0].format())
                        winCond = None
                        if q.postBattleCond.getConditions().getName() == 'and':
                            winCond = q.postBattleCond.getConditions().find('win')
                        isWin = winCond.getValue() if winCond is not None else False
                        battlesCond = q.bonusCond.getConditions().find('battles')
                        if battlesCond is not None:
                            curBattles, totalBattles = (0, 0)
                            progress = battlesCond.getProgressPerGroup()
                            if None in progress:
                                curBattles, totalBattles, _, _ = progress[None]
                            qProgress.append([curBattles, totalBattles, i18n.makeString('#quests:igr/tooltip/winsLabel') if isWin else i18n.makeString('#quests:igr/tooltip/battlesLabel')])
                if q.hasPremIGRVehBonus():
                    metaList = q.getBonuses('meta')
                    leftTime = time_utils.getTimeDeltaFromNow(q.getFinishTime())
                    if len(metaList) and leftTime > 0:
                        header = makeHtmlString('html_templates:lobby/tooltips', 'prem_igr_veh_quest_header', ctx={'qLabel': metaList[0].format()})
                        text = i18n.makeString('#tooltips:vehicleIgr/specialAbility')
                        localization = '#tooltips:vehicleIgr/%s'
                        actionLeft = getRentLeftTimeStr(localization, leftTime, timeStyle=TextType.STATS_TEXT)
                        text += '\n' + actionLeft
                        premVehQuests.append({'header': header,
                         'descr': text})

        descriptionTemplate = 'igr_description' if len(qLabels) == 0 else 'igr_description_with_quests'
        igrPercent = (game_control.g_instance.igr.getXPFactor() - 1) * 100
        igrType = game_control.g_instance.igr.getRoomType()
        icon = makeHtmlString('html_templates:igr/iconBig', 'premium' if igrType == constants.IGR_TYPE.PREMIUM else 'basic')
        return {'title': i18n.makeString(TOOLTIPS.IGR_TITLE, igrIcon=icon),
         'description': makeHtmlString('html_templates:lobby/tooltips', descriptionTemplate, {'igrValue': '{0}%'.format(BigWorld.wg_getIntegralFormat(igrPercent))}),
         'quests': map(lambda i: i.format(**template.ctx), qLabels),
         'progressHeader': makeHtmlString('html_templates:lobby/tooltips', 'igr_progress_header', {}),
         'progress': qProgress,
         'premVehQuests': premVehQuests}


class EfficiencyTooltipData(ToolTipBaseData):

    def __init__(self, context):
        super(EfficiencyTooltipData, self).__init__(context, TOOLTIP_TYPE.EFFICIENCY)

    def getDisplayableData(self, _, value):
        return value


class SortieDivisionTooltipData(ToolTipBaseData):

    def __init__(self, context):
        super(SortieDivisionTooltipData, self).__init__(context, TOOLTIP_TYPE.FORTIFICATIONS)

    def getDisplayableData(self):
        divisionsData = []
        divisions = makeDivisionData(I18N_FORTIFICATIONS.sortie_division_name)
        for division in divisions:
            divisionsData.append({'divisName': division['label'],
             'divisLevels': self.__getLevelsStr(division['level']),
             'divisBonus': self.__getBonusStr(division['profit']),
             'divisPlayers': self.__getPlayerLimitsStr(*self.__getPlayerLimits(division['level']))})

        return {'divisions': divisionsData}

    def __getPlayerLimits(self, divisionType):
        divisionIndex = SORTIE_DIVISION._ORDER.index(divisionType)
        division = SupportedRosterSettings.list(PREBATTLE_TYPE.SORTIE)[divisionIndex]
        return (division.getMinSlots(), division.getMaxSlots())

    def __getPlayerLimitsStr(self, minCount, maxCount):
        return self.app.utilsManager.textManager.getText(TextType.MAIN_TEXT, str(minCount) + ' - ' + str(maxCount))

    def __getLevelsStr(self, maxlvl):
        minLevel = 1
        minLevelStr = fort_formatters.getTextLevel(minLevel)
        maxLevelStr = fort_formatters.getTextLevel(maxlvl)
        return self.app.utilsManager.textManager.getText(TextType.MAIN_TEXT, minLevelStr + ' - ' + maxLevelStr)

    def __getBonusStr(self, bonus):
        text = (TextType.DEFRES_TEXT, BigWorld.wg_getIntegralFormat(bonus) + ' ')
        icon = (TextIcons.NUT_ICON,)
        return self.app.utilsManager.textManager.concatStyles((text, icon))


class MapTooltipData(ToolTipBaseData):

    def __init__(self, context):
        super(MapTooltipData, self).__init__(context, TOOLTIP_TYPE.MAP)

    def getDisplayableData(self, arenaID):
        arenaType = ArenaType.g_cache[int(arenaID)]
        return {'mapName': i18n.makeString('#arenas:%s/name' % arenaType.geometryName),
         'gameplayName': i18n.makeString('#arenas:type/%s/name' % arenaType.gameplayName),
         'imageURL': '../maps/icons/map/%s.png' % arenaType.geometryName,
         'description': i18n.makeString('#arenas:%s/description' % arenaType.geometryName)}


class HistoricalAmmoTooltipData(ToolTipBaseData):

    def __init__(self, context):
        super(HistoricalAmmoTooltipData, self).__init__(context, TOOLTIP_TYPE.HISTORICAL_AMMO)

    def getDisplayableData(self, battleID, vehicleID):
        battle = g_eventsCache.getHistoricalBattles().get(battleID)
        shellsItems = battle.getShellsLayout(int(vehicleID))
        priceString = battle.getShellsLayoutFormatedPrice(int(vehicleID), self.app.colorManager, True, True)
        data = {'price': priceString,
         'shells': []}
        shells = data['shells']
        for shell, count in shellsItems:
            shells.append({'id': str(shell.intCD),
             'type': shell.type,
             'label': ITEM_TYPES.shell_kindsabbreviation(shell.type),
             'icon': '../maps/icons/ammopanel/ammo/%s' % shell.descriptor['icon'][0],
             'count': count})

        return data


class HistoricalModulesTooltipData(ToolTipBaseData):

    def __init__(self, context):
        super(HistoricalModulesTooltipData, self).__init__(context, TOOLTIP_TYPE.HISTORICAL_MODULES)

    def getDisplayableData(self, battleID):
        templatePath = 'html_templates:lobby/historicalBattles/tooltips'
        template = 'moduleLabel'
        vehicle = g_currentVehicle.item
        battle = g_eventsCache.getHistoricalBattles().get(battleID)
        modules = battle.getModules(vehicle)
        data = {}
        if modules is not None:
            modulesData = []
            for item in modules.itervalues():
                modulesData.append({'type': item.itemTypeName,
                 'label': makeHtmlString(templatePath, template, {'type': item.userType,
                           'name': item.userName})})

            data = {'tankName': vehicle.userName,
             'modules': modulesData}
        return data


class SettingsControlTooltipData(ToolTipBaseData):

    def __init__(self, context):
        super(SettingsControlTooltipData, self).__init__(context, TOOLTIP_TYPE.CONTROL)

    def getDisplayableData(self, controlID):
        warningKey = '%s/warning' % controlID
        warning = i18n.makeString('#settings:%s' % warningKey)
        if warningKey == warning:
            warning = ''
        return {'name': i18n.makeString('#settings:%s' % controlID),
         'descr': i18n.makeString('#settings:%s/description' % controlID),
         'recommended': '',
         'status': {'level': 'warning',
                    'text': warning}}


class SettingsButtonTooltipData(ToolTipBaseData):

    def __init__(self, context):
        super(SettingsButtonTooltipData, self).__init__(context, TOOLTIP_TYPE.CONTROL)

    def getDisplayableData(self):
        from ConnectionManager import connectionManager
        serverName = ''
        if connectionManager.peripheryID == 0:
            serverName = connectionManager.serverUserName
        else:
            hostsList = g_preDefinedHosts.getSimpleHostsList(g_preDefinedHosts.hostsWithRoaming())
            for key, name, csisStatus, peripheryID in hostsList:
                if connectionManager.peripheryID == peripheryID:
                    serverName = name
                    break

        stats = None
        if constants.IS_SHOW_SERVER_STATS:
            stats = dict(game_control.g_instance.serverStats.getStats())
        return {'name': i18n.makeString(TOOLTIPS.HEADER_MENU_HEADER),
         'description': i18n.makeString(TOOLTIPS.HEADER_MENU_DESCRIPTION),
         'serverHeader': i18n.makeString(TOOLTIPS.HEADER_MENU_SERVER),
         'serverName': serverName,
         'playersOnServer': i18n.makeString(TOOLTIPS.HEADER_MENU_PLAYERSONSERVER),
         'servers': stats}


class CustomizationItemTooltipData(ToolTipBaseData):

    def __init__(self, context):
        super(CustomizationItemTooltipData, self).__init__(context, TOOLTIP_TYPE.CONTROL)

    def getDisplayableData(self, type, id, nationId, timeLeft = None):
        ms = i18n.makeString
        item = self._context.buildItem(nationId, id, type)
        headerText = ''
        typeText = ''
        descriptionText = ''
        timeLeftText = ''
        bottomText = ''
        if timeLeft is not None:
            isUsed = False
        else:
            timeLeft, isUsed = CustomizationHelper.getTimeLeft(id, type, nationId)
        if timeLeft >= 0:
            timeLeftText = self.__getTimeLeftText(timeLeft, isUsed)
            timeLeftText = self.__getText(TextType.MAIN_TEXT, timeLeftText)
        else:
            timeLeftText = ''
        if type == CUSTOMIZATION_ITEM_TYPE.CAMOUFLAGE:
            headerText = item['description'] + '/label'
            typeText = ms(VEHICLE_CUSTOMIZATION.CAMOUFLAGE) + ' ' + ms(CAMOUFLAGES_KIND_TEXTS[item['kind']])
            descriptionText = self.__getText(TextType.STANDARD_TEXT, ms(item['description'] + '/description'))
            bottomText = self.__getText(TextType.STATS_TEXT, ms(CAMOUFLAGES_NATIONS_TEXTS[nationId]))
        elif type == CUSTOMIZATION_ITEM_TYPE.EMBLEM:
            groupName, _, _, _, emblemName, _ = item
            groups, _, _ = vehicles.g_cache.playerEmblems()
            _, group, _, _ = groups.get(groupName)
            headerText = emblemName
            typeText = ms(VEHICLE_CUSTOMIZATION.EMBLEM) + ' ' + ms(group)
            descriptionText = ''
            bottomText = ''
        elif type == CUSTOMIZATION_ITEM_TYPE.INSCRIPTION:
            groupName, _, _, _, inscriptionName, _ = item
            groups = vehicles.g_cache.customization(nationId).get('inscriptionGroups', {})
            _, group, _ = groups.get(groupName)
            headerText = inscriptionName
            typeText = ms(VEHICLE_CUSTOMIZATION.INSCRIPTION) + ' ' + ms(group)
            descriptionText = ''
            bottomText = self.__getText(TextType.STATS_TEXT, ms(CAMOUFLAGES_NATIONS_TEXTS[nationId]))
        return {'header': self.__getText(TextType.HIGH_TITLE, ms(headerText)),
         'kind': self.__getText(TextType.MAIN_TEXT, typeText),
         'description': descriptionText,
         'timeLeft': timeLeftText,
         'vehicleType': bottomText}

    def __getText(self, type, text):
        return self.app.utilsManager.textManager.getText(type, text)

    def __getTimeLeftText(self, timeLeft, isUsed):
        ms = i18n.makeString
        result = ''
        if timeLeft > 0:
            secondsInDay = 86400
            secondsInHour = 3600
            secondsInMinute = 60
            if timeLeft > secondsInDay:
                timeLeft = int(math.ceil(timeLeft / secondsInDay))
                dimension = ms(VEHICLE_CUSTOMIZATION.TIMELEFT_TEMPORAL_DAYS)
            elif timeLeft > secondsInHour:
                timeLeft = int(math.ceil(timeLeft / secondsInHour))
                dimension = ms(VEHICLE_CUSTOMIZATION.TIMELEFT_TEMPORAL_HOURS)
            else:
                timeLeft = int(math.ceil(timeLeft / secondsInMinute))
                dimension = ms(VEHICLE_CUSTOMIZATION.TIMELEFT_TEMPORAL_MINUTES)
            result = ms(VEHICLE_CUSTOMIZATION.TIMELEFT_TEMPORAL_USED if isUsed else VEHICLE_CUSTOMIZATION.TIMELEFT_TEMPORAL, time=timeLeft, dimension=dimension)
        elif timeLeft == 0:
            result = ms(VEHICLE_CUSTOMIZATION.TIMELEFT_INFINITY)
        return result


class ClanInfoTooltipData(ToolTipBaseData, FortViewHelper):

    def __init__(self, context):
        super(ClanInfoTooltipData, self).__init__(context, TOOLTIP_TYPE.FORTIFICATIONS)

    def getDisplayableData(self, clanDBID):
        fortCtrl = g_clanCache.fortProvider.getController()
        isFortFrozen = False
        if clanDBID is None:
            fort = fortCtrl.getFort()
            fortDossier = fort.getFortDossier()
            battlesStats = fortDossier.getBattlesStats()
            isFortFrozen = self._isFortFrozen()
            clanName, clanMotto, clanTag = g_clanCache.clanName, '', g_clanCache.clanTag
            clanLvl = fort.level if fort is not None else 0
            homePeripheryID = fort.peripheryID
            playersAtClan, buildingsNum = len(g_clanCache.clanMembers), len(fort.getBuildingsCompleted())
            wEfficiencyVal = ProfileUtils.getFormattedWinsEfficiency(battlesStats)
            combatCount, winsEff, profitEff = battlesStats.getCombatCount(), ProfileUtils.UNAVAILABLE_SYMBOL if wEfficiencyVal == str(ProfileUtils.UNAVAILABLE_VALUE) else wEfficiencyVal, battlesStats.getProfitFactor()
            creationTime = fortDossier.getGlobalStats().getCreationTime()
            defence, vacation, offDay = fort.getDefencePeriod(), fort.getVacationDate(), fort.getLocalOffDay()
        elif type(clanDBID) in (types.IntType, types.LongType, types.FloatType):
            clanInfo = fortCtrl.getPublicInfoCache().getItem(clanDBID)
            if clanInfo is None:
                LOG_WARNING('Requested clan info is empty', clanDBID)
                return
            clanName, clanMotto = clanInfo.getClanName(), ''
            clanTag, clanLvl = '[%s]' % clanInfo.getClanAbbrev(), clanInfo.getLevel()
            homePeripheryID = clanInfo.getHomePeripheryID()
            playersAtClan, buildingsNum = (None, None)
            combatCount, profitEff = clanInfo.getBattleCount(), clanInfo.getProfitFactor()
            creationTime = None
            defence, offDay = clanInfo.getDefencePeriod(), clanInfo.getLocalOffDay()
            vacation = clanInfo.getVacationPeriod()
            winsEff = None
        else:
            LOG_WARNING('Invalid clanDBID identifier', clanDBID, type(clanDBID))
            return
        topStats = []
        host = g_preDefinedHosts.periphery(homePeripheryID)
        if host is not None:
            topStats.append((i18n.makeString(TOOLTIPS.FORTIFICATION_TOOLTIPENEMYCLANINFO_HOMEPEREPHIRY), host.name))
        if playersAtClan is not None:
            topStats.append((i18n.makeString(TOOLTIPS.FORTIFICATION_TOOLTIPENEMYCLANINFO_PLAYERSATCLAN), playersAtClan))
        if buildingsNum is not None:
            topStats.append((i18n.makeString(TOOLTIPS.FORTIFICATION_TOOLTIPENEMYCLANINFO_BUILDINGSATFORTIFICATION), buildingsNum))
        if combatCount is not None:
            topStats.append((i18n.makeString(TOOLTIPS.FORTIFICATION_TOOLTIPENEMYCLANINFO_FIGHTSFORFORTIFICATION), combatCount))
        if winsEff is not None:
            topStats.append((i18n.makeString(TOOLTIPS.FORTIFICATION_TOOLTIPENEMYCLANINFO_WINPERCENTAGE), winsEff))
        if profitEff is not None:
            topStats.append((i18n.makeString(TOOLTIPS.FORTIFICATION_TOOLTIPENEMYCLANINFO_PROFITPERCENTAGE), BigWorld.wg_getNiceNumberFormat(profitEff) if profitEff > 0 else ProfileUtils.UNAVAILABLE_SYMBOL))
        if creationTime is not None:
            fortCreationData = self.app.utilsManager.textManager.getText(TextType.NEUTRAL_TEXT, i18n.makeString(TOOLTIPS.FORTIFICATION_TOOLTIPCLANINFO_FORTCREATIONDATE, creationDate=BigWorld.wg_getLongDateFormat(creationTime)))
        else:
            fortCreationData = None

        def _makeLabels(stats, itemIdx):
            return '\n'.join((str(a[itemIdx]) for a in stats))

        infoTexts, protectionHeader = [], ''
        if defence[0]:
            if isFortFrozen:
                protectionHeader = self.app.utilsManager.textManager.getText(TextType.ERROR_TEXT, i18n.makeString(TOOLTIPS.FORTIFICATION_TOOLTIPENEMYCLANINFO_DEFENSETIMESTOPPED))
            else:
                protectionHeader = self.app.utilsManager.textManager.getText(TextType.HIGH_TITLE, i18n.makeString(TOOLTIPS.FORTIFICATION_TOOLTIPENEMYCLANINFO_DEFENSETIME))
            statsValueColor = TextType.DISABLE_TEXT if isFortFrozen else TextType.STATS_TEXT
            defencePeriodString = i18n.makeString(TOOLTIPS.FORTIFICATION_TOOLTIPENEMYCLANINFO_PERIOD, startTime=BigWorld.wg_getShortTimeFormat(defence[0]), finishTime=BigWorld.wg_getShortTimeFormat(defence[1]))
            defencePeriodString = self.app.utilsManager.textManager.getText(statsValueColor, defencePeriodString)
            infoTexts.append(i18n.makeString(TOOLTIPS.FORTIFICATION_TOOLTIPENEMYCLANINFO_DEFENSEHOUR, period=defencePeriodString))
            if offDay > -1:
                dayOffString = i18n.makeString('#menu:dateTime/weekDays/full/%d' % (offDay + 1))
            else:
                dayOffString = i18n.makeString(TOOLTIPS.FORTIFICATION_TOOLTIPENEMYCLANINFO_NODAYOFF)
            dayOffString = self.app.utilsManager.textManager.getText(statsValueColor, dayOffString)
            infoTexts.append(i18n.makeString(TOOLTIPS.FORTIFICATION_TOOLTIPENEMYCLANINFO_DAYOFF, dayOff=dayOffString))
            if vacation[0] and vacation[1]:
                vacationString = i18n.makeString(TOOLTIPS.FORTIFICATION_TOOLTIPENEMYCLANINFO_PERIOD, startTime=BigWorld.wg_getShortDateFormat(vacation[0]), finishTime=BigWorld.wg_getShortDateFormat(vacation[1]))
            else:
                vacationString = i18n.makeString(TOOLTIPS.FORTIFICATION_TOOLTIPENEMYCLANINFO_NOVACATION)
            vacationString = self.app.utilsManager.textManager.getText(statsValueColor, vacationString)
            infoTexts.append(i18n.makeString(TOOLTIPS.FORTIFICATION_TOOLTIPENEMYCLANINFO_VACATION, period=vacationString))
        return {'headerText': self.app.utilsManager.textManager.getText(TextType.HIGH_TITLE, i18n.makeString(TOOLTIPS.FORTIFICATION_TOOLTIPENEMYCLANINFO_HEADER, clanTag=clanTag, clanLevel=fort_formatters.getTextLevel(clanLvl))),
         'fullClanName': self.app.utilsManager.textManager.getText(TextType.NEUTRAL_TEXT, clanName),
         'sloganText': self.app.utilsManager.textManager.getText(TextType.STANDARD_TEXT, clanMotto),
         'infoDescriptionTopText': self.app.utilsManager.textManager.getText(TextType.MAIN_TEXT, _makeLabels(topStats, 0)),
         'infoTopText': self.app.utilsManager.textManager.getText('statsText', _makeLabels(topStats, 1)),
         'infoDescriptionBottomText': '',
         'infoBottomText': '',
         'protectionHeaderText': protectionHeader,
         'infoText': makeHtmlString('html_templates:lobby/fortifications/tooltips/defense_description', 'main', {'text': '\n'.join(infoTexts)}),
         'fortCreationDate': fortCreationData}


class ToolTipRefSysDescription(ToolTipBaseData):
    BONUSES_PRIORITY = ('vehicles', 'tankmen', 'credits')

    def __init__(self, context):
        super(ToolTipRefSysDescription, self).__init__(context, TOOLTIP_TYPE.REF_SYSTEM)

    def getDisplayableData(self):
        return {'titleTF': self.__makeTitle(),
         'actionTF': self.__makeMainText(TOOLTIPS.TOOLTIPREFSYSDESCRIPTION_HEADER_ACTIONTF),
         'conditionsTF': self.__makeConditions(),
         'awardsTitleTF': self.__makeStandardText(TOOLTIPS.TOOLTIPREFSYSDESCRIPTION_HEADER_AWARDSTITLETF),
         'blocksVOs': self.__makeBlocks(),
         'bottomTF': self.__makeMainText(TOOLTIPS.TOOLTIPREFSYSDESCRIPTION_BOTTOM_BOTTOMTF)}

    def __makeTitle(self):
        localMsg = ms(TOOLTIPS.TOOLTIPREFSYSDESCRIPTION_HEADER_TITLETF)
        return self.app.utilsManager.textManager.getText(TextType.HIGH_TITLE, localMsg)

    def __makeMainText(self, value):
        localMsg = ms(value)
        return self.app.utilsManager.textManager.getText(TextType.MAIN_TEXT, localMsg)

    def __makeConditions(self):
        txt = ms(TOOLTIPS.TOOLTIPREFSYSAWARDS_INFOBODY_CONDITIONS, top=game_control.g_instance.refSystem.getPosByXPinTeam())
        return self.app.utilsManager.textManager.getText(TextType.STANDARD_TEXT, txt)

    def __makeStandardText(self, value):
        localMsg = ms(value)
        return self.app.utilsManager.textManager.getText(TextType.STANDARD_TEXT, localMsg)

    def __makeBlocks(self):
        result = []
        for xp, quests in game_control.g_instance.refSystem.getQuests():
            xpCost = BigWorld.wg_getIntegralFormat(xp)
            awardDescrPars = []
            for quest in quests:
                for bonusName in self.BONUSES_PRIORITY:
                    bonuses = quest.getBonuses(bonusName)
                    if bonuses:
                        awardDescrPars.append(', '.join(map(methodcaller('getDescription'), bonuses)))

            awardDescr = ', '.join(awardDescrPars)
            result.append({'leftTF': self.app.utilsManager.textManager.getText(TextType.CREDITS_TEXT, xpCost),
             'rightTF': awardDescr,
             'iconSource': RES_ICONS.MAPS_ICONS_LIBRARY_XPCOSTICON})

        return result


class ToolTipRefSysAwards(ToolTipBaseData):
    BONUSES_PRIORITY = ('vehicles', 'tankmen', 'credits')

    def __init__(self, context):
        super(ToolTipRefSysAwards, self).__init__(context, TOOLTIP_TYPE.REF_SYSTEM)

    def getDisplayableData(self, data):
        xp, questIDs = pickle.loads(data)

        def filterFunc(q):
            return q.getID() in questIDs

        quests = g_eventsCache.getSystemQuests(filterFunc)
        icon = ''
        awardDescrPars = []
        isCompleted = True
        for quest in quests.itervalues():
            for bonusName in self.BONUSES_PRIORITY:
                bonuses = quest.getBonuses(bonusName)
                if bonuses:
                    awardDescrPars.append(', '.join(map(methodcaller('getDescription'), bonuses)))
                    if not icon:
                        icon = bonuses[0].getTooltipIcon()

            if isCompleted and not quest.isCompleted():
                isCompleted = False

        awardDescr = ', '.join(awardDescrPars)
        return {'iconSource': icon,
         'infoTitle': self.__makeTitle(awardDescr),
         'infoBody': self.__makeBody(xp, isCompleted),
         'conditions': self.__makeConditions(),
         'awardStatus': self.__makeStatus(isCompleted)}

    def __makeTitle(self, value):
        award = self.app.utilsManager.textManager.getText(TextType.HIGH_TITLE, value)
        return self.__makeTitleGeneralText(award)

    def __makeTitleGeneralText(self, award):
        text = i18n.makeString(TOOLTIPS.TOOLTIPREFSYSAWARDS_TITLE_GENERAL, awardMsg=award)
        return self.app.utilsManager.textManager.getText(TextType.HIGH_TITLE, text)

    def __makeBody(self, expCount, isCompleted):
        howManyExp = expCount - game_control.g_instance.refSystem.getReferralsXPPool()
        notEnoughMsg = ''
        if not isCompleted and howManyExp > 0:
            notEnough = self.app.utilsManager.textManager.getText(TextType.ERROR_TEXT, i18n.makeString(TOOLTIPS.TOOLTIPREFSYSAWARDS_INFOBODY_REQUIREMENTS_NOTENOUGH))
            notEnoughMsg = i18n.makeString(TOOLTIPS.TOOLTIPREFSYSAWARDS_INFOBODY_REQUIREMENTS_NOTENOUGHMSG, notEnough=notEnough, howMany=self.__formatExpCount(howManyExp))
        resultFormatter = self.app.utilsManager.textManager.getText(TextType.MAIN_TEXT, i18n.makeString(TOOLTIPS.TOOLTIPREFSYSAWARDS_INFOBODY_REQUIREMENTS, expCount=self.__formatExpCount(expCount), notEnoughMsg=notEnoughMsg))
        return resultFormatter

    def __formatExpCount(self, value):
        value = BigWorld.wg_getIntegralFormat(value)
        value = self.app.utilsManager.textManager.getText(TextType.CREDITS_TEXT, value)
        iconLocal = RES_ICONS.MAPS_ICONS_LIBRARY_XPCOSTICON
        utilsManager = self.app.utilsManager
        icon = utilsManager.getHtmlIconText(ImageUrlProperties(iconLocal, 18, 18, -9, 0))
        return value + icon

    def __makeConditions(self):
        txt = i18n.makeString(TOOLTIPS.TOOLTIPREFSYSAWARDS_INFOBODY_CONDITIONS, top=game_control.g_instance.refSystem.getPosByXPinTeam())
        return self.app.utilsManager.textManager.getText(TextType.STANDARD_TEXT, txt)

    def __makeStatus(self, isReceived):
        loc = TOOLTIPS.TOOLTIPREFSYSAWARDS_INFOBODY_NOTACCESS
        if isReceived:
            loc = TOOLTIPS.TOOLTIPREFSYSAWARDS_INFOBODY_ACCESS
        txt = i18n.makeString(loc)
        txt = self.app.utilsManager.textManager.getText(TextType.MAIN_TEXT, txt)
        return txt


class ToolTipRefSysXPMultiplier(ToolTipBaseData):

    def __init__(self, context):
        super(ToolTipRefSysXPMultiplier, self).__init__(context, TOOLTIP_TYPE.REF_SYSTEM)

    def getDisplayableData(self):
        refSystem = game_control.g_instance.refSystem
        xpIcon = RES_ICONS.MAPS_ICONS_LIBRARY_XPCOSTICON
        icon = self.app.utilsManager.getHtmlIconText(ImageUrlProperties(xpIcon, 18, 18, -9, 0))
        expNum = self.app.utilsManager.textManager.getText(TextType.CREDITS_TEXT, ms(BigWorld.wg_getNiceNumberFormat(refSystem.getMaxReferralXPPool())))
        titleText = self.app.utilsManager.textManager.getText(TextType.HIGH_TITLE, ms(TOOLTIPS.TOOLTIPREFSYSXPMULTIPLIER_TITLE))
        descriptionText = self.app.utilsManager.textManager.getText(TextType.MAIN_TEXT, ms(TOOLTIPS.TOOLTIPREFSYSXPMULTIPLIER_DESCRIPTION))
        conditionsText = self.app.utilsManager.textManager.getText(TextType.STANDARD_TEXT, ms(TOOLTIPS.TOOLTIPREFSYSXPMULTIPLIER_CONDITIONS))
        bottomText = self.app.utilsManager.textManager.getText(TextType.MAIN_TEXT, ms(TOOLTIPS.TOOLTIPREFSYSXPMULTIPLIER_BOTTOM, expNum=expNum + '<nobr>' + icon))
        xpBlocks = []
        for i, (period, bonus) in enumerate(refSystem.getRefPeriods()):
            xpBonus = 'x%s' % BigWorld.wg_getNiceNumberFormat(bonus)
            condition = self.__formatPeriod(period)
            xpBlocks.append({'xpIconSource': RES_ICONS.MAPS_ICONS_LIBRARY_XPCOSTICON,
             'multiplierText': self.app.utilsManager.textManager.getText(TextType.CREDITS_TEXT, xpBonus),
             'descriptionText': self.app.utilsManager.textManager.getText(TextType.MAIN_TEXT, condition)})

        return {'titleText': titleText,
         'descriptionText': descriptionText,
         'conditionsText': conditionsText,
         'bottomText': bottomText,
         'xpBlocksVOs': xpBlocks}

    def __formatPeriod(self, period):
        if period <= 24:
            return ms(TOOLTIPS.TOOLTIPREFSYSXPMULTIPLIER_CONDITIONS_HOURS, hoursNum=period)
        if period <= 8760:
            return ms(TOOLTIPS.TOOLTIPREFSYSXPMULTIPLIER_CONDITIONS_DAYS, daysNum=period / 24)
        return ms(TOOLTIPS.TOOLTIPREFSYSXPMULTIPLIER_CONDITIONS_OTHER)


_battleStatus = namedtuple('_battleStatus', ('level', 'msg', 'color', 'prefix'))

class ToolTipFortBuildingData(ToolTipBaseData, FortViewHelper):

    class BATTLE_STATUSES(CONST_CONTAINER):
        NO_BATTLE = _battleStatus('warning', FORT.TOOLTIPBUILDINGINFO_STATUSMSG_WASNOTBATTLE, TextType.DEFRES_TEXT, '')
        LOST = _battleStatus('critical', FORT.TOOLTIPBUILDINGINFO_STATUSMSG_DEFEAT, TextType.ERROR_TEXT, '-')
        WON = _battleStatus('info', FORT.TOOLTIPBUILDINGINFO_STATUSMSG_VICTORY, TextType.SUCCESS_TEXT, '+')

    def __init__(self, context):
        super(ToolTipFortBuildingData, self).__init__(context, TOOLTIP_TYPE.FORTIFICATIONS)

    def getDisplayableData(self, buildingUID, isMine):
        ms = i18n.makeString
        fort = self.fortCtrl.getFort()
        battleID = getBattleID()
        battle = fort.getBattle(battleID)
        buildingTypeID = self.UI_BUILDINGS_BIND.index(buildingUID)
        if battle.isDefence():
            isAttack = not isMine
        else:
            isAttack = isMine
        if isAttack:
            buildingsList = battle.getAttackerBuildList()
            buildingsFullList = battle.getAttackerFullBuildList()
        else:
            buildingsList = battle.getDefenderBuildList()
            buildingsFullList = battle.getDefenderFullBuildList()
        buildingFullData = findFirst(lambda x: x[0] == buildingTypeID, buildingsFullList)
        _, status, buildingLevel, hpVal, defResVal = buildingFullData
        isReadyForBattle = status == constants.FORT_BUILDING_STATUS.READY_FOR_BATTLE
        buildingData = None
        resCount, arenaTypeID = (None, None)
        if isReadyForBattle:
            buildingData = findFirst(lambda x: x[0] == buildingTypeID, buildingsList)
            _, resCount, arenaTypeID = buildingData
        _, status, buildingLevel, hpVal, defResVal = buildingFullData
        progress = self._getProgress(buildingTypeID, buildingLevel)
        normLevel = max(buildingLevel, 1)
        buildingLevelData = fortified_regions.g_cache.buildings[buildingTypeID].levels[normLevel]
        hpTotalVal = buildingLevelData.hp
        maxDefResVal = buildingLevelData.storage
        buildingName = self.app.utilsManager.textManager.getText(TextType.HIGH_TITLE, ms(FORT.buildings_buildingname(buildingUID)))
        currentMapTxt = None
        buildingLevelTxt = self.app.utilsManager.textManager.getText(TextType.MAIN_TEXT, ms(FORT.FORTMAINVIEW_HEADER_LEVELSLBL, buildLevel=str(fort_formatters.getTextLevel(buildingLevel))))
        descrActionTxt = None
        statusTxt = None
        statusLevel = None
        indicatorsModel = None
        infoMessage = None
        if status == constants.FORT_BUILDING_STATUS.LOW_LEVEL:
            minBuildingLevel = fortified_regions.g_cache.defenceConditions.minRegionLevel
            minLevel = fort_formatters.getTextLevel(1)
            maxLevel = fort_formatters.getTextLevel(minBuildingLevel - 1)
            infoMessage = ms(FORT.TOOLTIPBUILDINGINFO_LOWLEVELMESSAGE, minLevel=minLevel, maxLevel=maxLevel)
        else:
            indicatorsModel = makeBuildingIndicatorsVO(buildingLevel, progress, hpVal, hpTotalVal, defResVal, maxDefResVal)
            if isReadyForBattle:
                lootedBuildings = battle.getLootedBuildList()
                battleStatus = self.BATTLE_STATUSES.NO_BATTLE
                if (buildingData, isAttack) in lootedBuildings:
                    battleStatus = self.BATTLE_STATUSES.LOST
                    if battle.isDefence() and isAttack or not battle.isDefence() and not isAttack:
                        battleStatus = self.BATTLE_STATUSES.WON
                arenaType = ArenaType.g_cache.get(arenaTypeID)
                prefix = self.app.utilsManager.textManager.getText(TextType.STANDARD_TEXT, ms(FORT.TOOLTIPBUILDINGINFO_MEP_MAPPREFIX))
                mapName = self.app.utilsManager.textManager.getText(TextType.NEUTRAL_TEXT, arenaType.name)
                currentMapTxt = prefix + mapName
                statusLevel = battleStatus.level
                statusTxt = ms(battleStatus.msg)
                defResStatusTxt = self.app.utilsManager.textManager.concatStyles(((battleStatus.color, '%s %s' % (battleStatus.prefix, BigWorld.wg_getIntegralFormat(resCount))), (TextIcons.NUT_ICON,)))
                descrActionTxt = self.app.utilsManager.textManager.getText(TextType.MAIN_TEXT, ms(FORT.TOOLTIPBUILDINGINFO_DESCRACTION))
                descrActionTxt = descrActionTxt % {'value': defResStatusTxt}
            else:
                minResCount = hpTotalVal * 0.2
                minResStatusTxt = self.app.utilsManager.textManager.concatStyles(((TextType.NEUTRAL_TEXT, BigWorld.wg_getIntegralFormat(minResCount)), (TextIcons.NUT_ICON,)))
                infoMessage = self.app.utilsManager.textManager.getText(TextType.MAIN_TEXT, ms(FORT.TOOLTIPBUILDINGINFO_DESTROYEDMESSAGE))
                infoMessage = infoMessage % {'value': minResStatusTxt}
        result = {'buildingUID': buildingUID,
         'buildingName': buildingName,
         'currentMap': currentMapTxt,
         'buildingLevel': buildingLevelTxt,
         'descrAction': descrActionTxt,
         'statusMsg': statusTxt,
         'statusLevel': statusLevel,
         'indicatorModel': indicatorsModel,
         'isAvailable': isReadyForBattle,
         'infoMessage': infoMessage}
        return result


class ActionTooltipData(ToolTipBaseData):

    def __init__(self, context):
        super(ActionTooltipData, self).__init__(context, TOOLTIP_TYPE.CONTROL)

    def getDisplayableData(self, type, key, newPrice, oldPrice, isBuying, forCredits = False):
        actionNames = None
        body = ''
        descr = ''
        newCredits, newGold = newPrice
        oldCredits, oldGold = oldPrice
        newPriceValue = 0
        newPriceCurrency = None
        oldPriceValue = 0
        oldPriceCurrency = None
        hasRentCompensation = False
        rentCompensation = None
        if type == ACTION_TOOLTIPS_TYPE.ECONOMICS:
            actions = g_eventsCache.getEconomicsAction(key)
            if actions:
                actionNames = map(lambda x: x[1], actions)
                newPriceValue = newCredits if forCredits else newGold
                oldPriceValue = oldCredits if forCredits else oldGold
                newPriceCurrency = oldPriceCurrency = 'credits' if forCredits else 'gold'
                if key == 'freeXPToTManXPRate':
                    newPriceCurrency = oldPriceCurrency = 'freeXp'
        elif type == ACTION_TOOLTIPS_TYPE.ITEM:
            item = g_itemsCache.items.getItemByCD(int(key))
            useGold = item.isPremium and not forCredits and isBuying
            newPriceValue = newGold if useGold else newCredits
            newPriceCurrency = 'gold' if useGold else 'credits'
            oldPriceValue = oldGold if useGold else oldCredits
            oldPriceCurrency = 'gold' if useGold else 'credits'
            actions = g_eventsCache.getItemAction(item, True, forCredits)
            if item.itemTypeID in (GUI_ITEM_TYPE.SHELL, GUI_ITEM_TYPE.OPTIONALDEVICE, GUI_ITEM_TYPE.EQUIPMENT) and item.isPremium and not useGold:
                actions += g_eventsCache.getEconomicsAction('exchangeRateForShellsAndEqs')
            if item.itemTypeID == GUI_ITEM_TYPE.VEHICLE and item.isPremium and not isBuying:
                actions += g_eventsCache.getEconomicsAction('exchangeRate')
            if actions:
                actionNames = map(lambda x: x[1], actions)
            if not isBuying:
                sellingActions = g_eventsCache.getItemAction(item, False, forCredits)
                if sellingActions:
                    actionNames = map(lambda x: x[1], sellingActions)

                    def filter(item):
                        (forGold, _), _ = item
                        return forGold

                    sellForGoldAction = findFirst(filter, sellingActions)
                    if sellForGoldAction:
                        newPriceValue = newGold
                        newPriceCurrency = 'gold'
            if item.itemTypeID == GUI_ITEM_TYPE.VEHICLE and isBuying:
                if item.isRented and not item.rentalIsOver and item.rentCompensation[1] > 0:
                    hasRentCompensation = True
                    rentCompensation = item.rentCompensation[1]
        elif type == ACTION_TOOLTIPS_TYPE.CAMOUFLAGE:
            intCD, type = cPickle.loads(key)
            actions = g_eventsCache.getCamouflageAction(intCD) + g_eventsCache.getEconomicsAction(type)
            if actions:
                actionNames = map(lambda x: x[1], actions)
                newPriceValue = newCredits if forCredits else newGold
                oldPriceValue = oldCredits if forCredits else oldGold
                newPriceCurrency = oldPriceCurrency = 'credits' if forCredits else 'gold'
        elif type == ACTION_TOOLTIPS_TYPE.EMBLEMS:
            group, type = cPickle.loads(key)
            actions = g_eventsCache.getEmblemsAction(group) + g_eventsCache.getEconomicsAction(type)
            if actions:
                actionNames = map(lambda x: x[1], actions)
                newPriceValue = newCredits if forCredits else newGold
                oldPriceValue = oldCredits if forCredits else oldGold
                newPriceCurrency = oldPriceCurrency = 'credits' if forCredits else 'gold'
        elif type == ACTION_TOOLTIPS_TYPE.AMMO:
            item = g_itemsCache.items.getItemByCD(int(key))
            actions = []
            for shell in item.gun.defaultAmmo:
                actions += g_eventsCache.getItemAction(shell, isBuying, True)

            if actions:
                actionNames = map(lambda x: x[1], actions)
                newPriceValue = newCredits
                oldPriceValue = oldCredits
                newPriceCurrency = oldPriceCurrency = 'credits'
        if actionNames:
            actionNames = set(actionNames)
        if actionNames or hasRentCompensation:
            formatedNewPrice = makeHtmlString('html_templates:lobby/quests/actions', newPriceCurrency, {'value': BigWorld.wg_getGoldFormat(newPriceValue)})
            formatedOldPrice = makeHtmlString('html_templates:lobby/quests/actions', oldPriceCurrency, {'value': BigWorld.wg_getGoldFormat(oldPriceValue)})
            body = i18n.makeString('#tooltips:actionPrice/body', oldPrice=formatedOldPrice, newPrice=formatedNewPrice)

            def mapName(item):
                action = g_eventsCache.getActions().get(item)
                return i18n.makeString('#tooltips:actionPrice/actionName', actionName=action.getUserName())

            descr = ''
            if actionNames:
                actionUserNames = ', '.join(map(mapName, actionNames))
                if len(actionNames) > 1:
                    descr = i18n.makeString('#tooltips:actionPrice/forActions', actions=actionUserNames)
                else:
                    descr = i18n.makeString('#tooltips:actionPrice/forAction', action=actionUserNames)
            if hasRentCompensation:
                formattedRentCompensation = makeHtmlString('html_templates:lobby/quests/actions', 'gold', {'value': BigWorld.wg_getGoldFormat(rentCompensation)})
                descr += '\n' + i18n.makeString('#tooltips:actionPrice/rentCompensation', rentCompensation=formattedRentCompensation)
        return {'name': i18n.makeString('#tooltips:actionPrice/header'),
         'descr': '%s\n%s' % (body, descr)}
