# Embedded file name: scripts/client/gui/Scaleform/daapi/view/lobby/fortifications/components/FortIntelligenceClanDescription.py
import BigWorld
import time
from ClientFortifiedRegion import BUILDING_UPDATE_REASON
from ClientFortifiedRegion import ATTACK_PLAN_RESULT
from constants import FORT_MAX_ELECTED_CLANS, FORT_BUILDING_TYPE
import fortified_regions
from gui.Scaleform.daapi.view.lobby.fortifications.fort_utils import fort_formatters
from gui.Scaleform.daapi.view.lobby.fortifications.fort_utils.FortSoundController import g_fortSoundController
from gui.Scaleform.daapi.view.meta.FortIntelligenceClanDescriptionMeta import FortIntelligenceClanDescriptionMeta
from gui.Scaleform.framework import AppRef
from gui.Scaleform.framework.managers.TextManager import TextType
from gui.Scaleform.locale.RES_ICONS import RES_ICONS
from gui.Scaleform.locale.FORTIFICATIONS import FORTIFICATIONS
from gui.Scaleform.locale.TOOLTIPS import TOOLTIPS
from gui.shared.fortifications import getDirectionFromDirPos, getPositionFromDirPos
from gui.shared.fortifications.context import FavoriteCtx
from gui.shared.fortifications.fort_helpers import adjustDefenceHourToLocal
from helpers import i18n
from gui.Scaleform.daapi.view.lobby.fortifications.fort_utils.FortViewHelper import FortViewHelper
from gui.shared.ClanCache import g_clanCache
from adisp import process
from gui import makeHtmlString
from debug_utils import LOG_DEBUG
from gui.shared import events
from gui.shared import EVENT_BUS_SCOPE
from gui.Scaleform.genConsts.FORTIFICATION_ALIASES import FORTIFICATION_ALIASES
from helpers import time_utils
from gui.shared.utils import functions
from helpers.i18n import makeString as _ms

class FortIntelligenceClanDescription(FortIntelligenceClanDescriptionMeta, FortViewHelper, AppRef):

    def __init__(self):
        super(FortIntelligenceClanDescription, self).__init__()
        self.__hasResults = False
        self.__weAreAtWar = False
        self.__item = None
        self.__upcomingAttack = None
        self.__attackInCooldown = None
        self.__defenceInCooldown = None
        self.__selectedDayStart, self.__selectedDayEnd = (0, 0)
        self.__selectedDefencePeriodStart, self.__selectedDefencePeriodEnd = (0, 0)
        self.__clanEmblem = None
        return

    def onFortPublicInfoReceived(self, hasResults):
        self.__hasResults = hasResults
        self.__weAreAtWar = False
        self.__item = None
        self.__clanEmblem = None
        self.__makeData()
        return

    def onFortPublicInfoValidationError(self, _):
        self.__hasResults = False
        self.__weAreAtWar = False
        self.__item = None
        self.__clanEmblem = None
        self.__selectedDayStart, self.__selectedDayEnd = (0, 0)
        self.__selectedDefencePeriodStart, self.__selectedDefencePeriodEnd = (0, 0)
        self.__makeData()
        return

    def onEnemyClanCardReceived(self, card):
        self.__upcomingAttack = None
        self.__attackInCooldown = None
        self.__defenceInCooldown = None
        self.__weAreAtWar = False
        self.__clanEmblem = None
        self.__item = card
        self.__getAttacksAndDeffences()
        self.__setSelectedDate()
        self.__calculateDefencePeriod()
        self.__makeData()
        self.__requestClanEmblem()
        return

    def onEnemyClanCardRemoved(self):
        cache = self.fortCtrl.getPublicInfoCache()
        if cache is not None:
            self.__hasResults = cache.hasResults()
            self.__item = None
            self.__clanEmblem = None
            self.__selectedDayStart, self.__selectedDayEnd = (0, 0)
            self.__selectedDefencePeriodStart, self.__selectedDefencePeriodEnd = (0, 0)
            self.__makeData()
        return

    def onOpenCalendar(self):
        self.fireEvent(events.ShowViewEvent(FORTIFICATION_ALIASES.FORT_CALENDAR_WINDOW_EVENT, ctx={'dateSelected': self.__selectedDayStart}), EVENT_BUS_SCOPE.LOBBY)

    def onFavoritesChanged(self, clanDBID):
        if self.__item is not None and self.__item.getClanDBID() == clanDBID:
            isAdd = clanDBID in self.fortCtrl.getFort().favorites
            self.as_updateBookMarkS(isAdd)
        return

    def onAddRemoveFavorite(self, isAdd):
        self.__toggleFavorite(isAdd)

    def onOpenClanList(self):
        self.fireEvent(events.ShowViewEvent(FORTIFICATION_ALIASES.FORT_CLAN_LIST_WINDOW_EVENT), EVENT_BUS_SCOPE.LOBBY)

    def onOpenClanStatistics(self):
        self.fireEvent(events.ShowViewEvent(FORTIFICATION_ALIASES.FORT_CLAN_STATISTICS_WINDOW_EVENT), EVENT_BUS_SCOPE.LOBBY)

    def onOpenClanCard(self):
        LOG_DEBUG('onOpenClanCard')

    def onHoverDirection(self):
        g_fortSoundController.playEnemyDirectionHover()

    def onAttackDirection(self, direction):
        g_fortSoundController.playEnemyDirectionSelected()
        self.fireEvent(events.ShowViewEvent(FORTIFICATION_ALIASES.FORT_DECLARATION_OF_WAR_WINDOW_EVENT, ctx={'direction': direction,
         'dateSelected': (self.__selectedDefencePeriodStart, self.__selectedDefencePeriodEnd),
         'item': self.__item}), EVENT_BUS_SCOPE.LOBBY)

    def onBuildingChanged(self, buildingTypeID, reason, ctx = None):
        if reason == BUILDING_UPDATE_REASON.UPDATED and buildingTypeID == FORT_BUILDING_TYPE.MILITARY_BASE:
            self.__makeData()

    def _populate(self):
        super(FortIntelligenceClanDescription, self)._populate()
        self.startFortListening()
        self.addListener(events.CalendarEvent.DATE_SELECTED, self.__onCalendarDataSelected, EVENT_BUS_SCOPE.LOBBY)
        self.__makeData()

    def _dispose(self):
        self.__item = None
        self.removeListener(events.CalendarEvent.DATE_SELECTED, self.__onCalendarDataSelected, EVENT_BUS_SCOPE.LOBBY)
        self.stopFortListening()
        super(FortIntelligenceClanDescription, self)._dispose()
        return

    def __makeData(self):
        fort = self.fortCtrl.getFort()
        data = {'numOfFavorites': len(fort.favorites),
         'favoritesLimit': FORT_MAX_ELECTED_CLANS,
         'canAttackDirection': self.fortCtrl.getPermissions().canPlanAttack(),
         'canAddToFavorite': self.fortCtrl.getPermissions().canAddToFavorite(),
         'isOurFortFrozen': self._isFortFrozen(),
         'isSelected': self.__item is not None,
         'haveResults': self.__hasResults}
        if self.__item is not None:
            clanID = self.__item.getClanDBID()
            if self.__item.getLocalDefHour() != time_utils.getDateTimeInLocal(self.__selectedDefencePeriodStart).hour:
                warTime = '%s - %s' % (BigWorld.wg_getShortTimeFormat(self.__selectedDefencePeriodStart), BigWorld.wg_getShortTimeFormat(self.__selectedDefencePeriodEnd))
                warPlannedIcon = makeHtmlString('html_templates:lobby/iconText', 'alert', {})
                warPlannedMsg = makeHtmlString('html_templates:lobby/textStyle', 'alertText', {'message': warTime})
                warPlannedTime = i18n.makeString(warPlannedIcon + ' ' + warPlannedMsg)
                data.update({'warPlannedTime': warPlannedTime,
                 'warPlannedTimeTT': i18n.makeString(TOOLTIPS.FORTIFICATION_FORTINTELLIGENCECLANDESCRIPTION_WARTIME, warTime=warTime)})
            if self.__weAreAtWar:
                closestAttack = self.__attackInCooldown or self.__upcomingAttack
                closestAttackTime = closestAttack.getStartTime()
                isAlreadyFought = self.__attackInCooldown is not None and (self.__defenceInCooldown is None or self.__defenceInCooldown.getStartTime() > self.__attackInCooldown.getStartTime())
                data.update({'isWarDeclared': self.__upcomingAttack is not None,
                 'isAlreadyFought': isAlreadyFought,
                 'warPlannedDate': BigWorld.wg_getLongDateFormat(closestAttackTime),
                 'warNextAvailableDate': BigWorld.wg_getLongDateFormat(closestAttackTime + time_utils.ONE_WEEK)})
            isFrozen = fort.isFrozen()
            clanFortBattlesStats = self.__item.getStatistics().getBattlesStats()
            battlesCount = clanFortBattlesStats.getBattlesCount()
            battlesWinsEff = clanFortBattlesStats.getWinsEfficiency()
            MIN_VALUE = 0.01
            clanAvgDefresValue = functions.roundToMinOrZero(clanFortBattlesStats.getProfitFactor(), MIN_VALUE)
            data.update({'dateSelected': BigWorld.wg_getLongDateFormat(self.__selectedDayStart),
             'selectedDayTimestamp': self.__selectedDayStart,
             'clanTag': '[%s]' % self.__item.getClanAbbrev(),
             'clanName': self.__item.getClanName(),
             'clanInfo': self.__item.getClanMotto(),
             'clanId': clanID,
             'clanEmblem': self.__clanEmblem,
             'isFavorite': clanID in fort.favorites,
             'isFrozen': isFrozen,
             'selectedDateText': self.__getSelectedDateText(),
             'clanBattles': {'value': BigWorld.wg_getNiceNumberFormat(battlesCount) if battlesCount else '--',
                             'icon': RES_ICONS.MAPS_ICONS_LIBRARY_DOSSIER_BATTLES40X32,
                             'ttHeader': i18n.makeString(TOOLTIPS.FORTIFICATION_FORTINTELLIGENCECLANDESCRIPTION_BATTLES_HEADER),
                             'ttBody': i18n.makeString(TOOLTIPS.FORTIFICATION_FORTINTELLIGENCECLANDESCRIPTION_BATTLES_BODY, wins=BigWorld.wg_getNiceNumberFormat(clanFortBattlesStats.getWinsCount()), defeats=BigWorld.wg_getNiceNumberFormat(clanFortBattlesStats.getLossesCount()))},
             'clanWins': {'value': '%s%%' % BigWorld.wg_getNiceNumberFormat(functions.roundToMinOrZero(battlesWinsEff, MIN_VALUE) * 100) if battlesWinsEff is not None else '--',
                          'icon': RES_ICONS.MAPS_ICONS_LIBRARY_DOSSIER_WINS40X32,
                          'ttHeader': i18n.makeString(TOOLTIPS.FORTIFICATION_FORTINTELLIGENCECLANDESCRIPTION_WINS_HEADER),
                          'ttBody': i18n.makeString(TOOLTIPS.FORTIFICATION_FORTINTELLIGENCECLANDESCRIPTION_WINS_BODY)},
             'clanAvgDefres': {'value': BigWorld.wg_getNiceNumberFormat(clanAvgDefresValue) if clanAvgDefresValue else '--',
                               'icon': RES_ICONS.MAPS_ICONS_LIBRARY_DOSSIER_DEFRESRATIO40X32,
                               'ttHeader': i18n.makeString(TOOLTIPS.FORTIFICATION_FORTINTELLIGENCECLANDESCRIPTION_AVGDEFRES_HEADER),
                               'ttBody': i18n.makeString(TOOLTIPS.FORTIFICATION_FORTINTELLIGENCECLANDESCRIPTION_AVGDEFRES_BODY)},
             'directions': self.__getDirectionsData()})
        self.as_setDataS(data)
        return

    @process
    def __toggleFavorite(self, isAdd):
        if self.__item is not None:
            clanID = self.__item.getClanDBID()
            result = yield self.fortProvider.sendRequest(FavoriteCtx(self.__item.getClanDBID(), isAdd=isAdd, waitingID='fort/favorite/' + ('add' if isAdd else 'remove')))
            if not result:
                isAdd = clanID in self.fortCtrl.getFort().favorites
                self.as_updateBookMarkS(isAdd)
        return

    def __getDirectionsData(self):
        directions = []
        fort = self.fortCtrl.getFort()
        start, finish = time_utils.getDayTimeBoundsForUTC(self.__selectedDefencePeriodStart)

        def filterToday(item):
            if start <= item.getStartTime() <= finish:
                return True
            return False

        attacksThisDayByUTC = fort.getAttacks(filterFunc=filterToday)
        hasFreeDirsLeft = len(attacksThisDayByUTC) < len(fort.getOpenedDirections())
        for direction in xrange(1, fortified_regions.g_cache.maxDirections + 1):
            isOpened = bool(self.__item.getDirMask() & 1 << direction)
            name = i18n.makeString('#fortifications:General/directionName%d' % direction)
            data = {'name': name,
             'uid': direction,
             'isOpened': isOpened,
             'ttHeader': i18n.makeString(FORTIFICATIONS.FORTINTELLIGENCE_CLANDESCRIPTION_DIRECTION_TOOLTIP_NOTAVAILABLE_HEADER, direction=name),
             'ttBody': i18n.makeString(FORTIFICATIONS.FORTINTELLIGENCE_CLANDESCRIPTION_DIRECTION_TOOLTIP_NOTOPENED)}
            if isOpened:
                attackTime, attackerClanDBID, attackerClanName, byMyClan = self.__getDirectionAttackerInfo(direction)
                availableTime = self.__item.getDictDirOpenAttacks().get(direction, 0)
                if availableTime <= self.__selectedDefencePeriodStart:
                    availableTime = None
                buildings = self.__getDirectionBuildings(direction)
                ttHeader, ttBody, infoMessage = self.__getDirectionTooltipData(name, buildings, attackerClanDBID, attackerClanName, attackTime, availableTime)
                isBusy = attackerClanDBID is not None
                isInCooldown = availableTime is not None
                isAvailableForAttack = self.fortCtrl.getFort().canPlanAttackOn(self.__selectedDefencePeriodStart, self.__item) == ATTACK_PLAN_RESULT.OK
                isAvailable = not self.__weAreAtWar and hasFreeDirsLeft and not isBusy and not isInCooldown and isAvailableForAttack
                data.update({'buildings': buildings,
                 'isAvailable': isAvailable,
                 'infoMessage': infoMessage,
                 'ttHeader': ttHeader,
                 'ttBody': ttBody,
                 'isAttackDeclaredByMyClan': byMyClan,
                 'attackerClanID': attackerClanDBID,
                 'attackerClanName': attackerClanName})
            directions.append(data)

        return directions

    def __getSelectedDateText(self):
        if self.fortCtrl.getPermissions().canPlanAttack():
            if self._isFortFrozen():
                selectedDateText = self.app.utilsManager.textManager.getText(TextType.ERROR_TEXT, _ms(FORTIFICATIONS.FORTINTELLIGENCE_CLANDESCRIPTION_ATTACKIMPOSSIBLE))
            else:
                selectedDateText = self.app.utilsManager.textManager.getText(TextType.STANDARD_TEXT, _ms(FORTIFICATIONS.FORTINTELLIGENCE_CLANDESCRIPTION_SELECTDATE))
        else:
            selectedDateText = self.app.utilsManager.textManager.getText(TextType.STANDARD_TEXT, _ms(FORTIFICATIONS.FORTINTELLIGENCE_CLANDESCRIPTION_SELECTDATE_CANTATTACK))
        return selectedDateText

    def __getDirectionBuildings(self, direction):
        buildings = [None, None]
        for buildingID, buildingData in self.__item.getDictBuildingsBrief().iteritems():
            dir = getDirectionFromDirPos(buildingData['dirPosByte'])
            if direction == dir:
                pos = getPositionFromDirPos(buildingData['dirPosByte'])
                level = buildingData['level']
                buildings[pos] = {'uid': self.UI_BUILDINGS_BIND[buildingID],
                 'progress': self._getProgress(buildingID, level),
                 'buildingLevel': level}

        return buildings

    def __getDirectionAttackerInfo(self, direction):
        byMyClan = False
        attackerClanDBID = None
        attackerClanName = None
        attackTime = None
        for timestamp, dir, clanDBID, clanAbbrev in self.__item.getListScheduledAttacksAt(self.__selectedDayStart, self.__selectedDayEnd):
            if direction == dir:
                attackerClanDBID = clanDBID
                byMyClan = attackerClanDBID == g_clanCache.clanDBID
                attackerClanName = '[%s]' % clanAbbrev
                attackTime = timestamp

        return (attackTime,
         attackerClanDBID,
         attackerClanName,
         byMyClan)

    def __getDirectionTooltipData(self, dirName, buildings, attackerClanDBID, attackerClanName, attackTime, availableTime):
        infoMessage = ''
        bodyParts = []
        ms = i18n.makeString
        if self.fortCtrl.getFort().isFrozen() or self.__weAreAtWar:
            return (None, None, None)
        else:
            buildingsMsgs = []
            for building in buildings:
                if building is not None:
                    extraInfo = ''
                    if building['buildingLevel'] < FORTIFICATION_ALIASES.CLAN_BATTLE_BUILDING_MIN_LEVEL:
                        extraInfo = ms(FORTIFICATIONS.FORTINTELLIGENCE_CLANDESCRIPTION_DIRECTION_TOOLTIP_BUILDINGLOWLEVEL, minLevel=fort_formatters.getTextLevel(FORTIFICATION_ALIASES.CLAN_BATTLE_BUILDING_MIN_LEVEL))
                    buildingsMsgs.insert(0, ms(FORTIFICATIONS.FORTINTELLIGENCE_CLANDESCRIPTION_DIRECTION_TOOLTIP_BUILDINGITEM, name=ms(FORTIFICATIONS.buildings_buildingname(building['uid'])), level=ms(FORTIFICATIONS.FORTMAINVIEW_HEADER_LEVELSLBL, buildLevel=str(fort_formatters.getTextLevel(building['buildingLevel']))), extraInfo=extraInfo))

            buildingsNames = '\n'.join(buildingsMsgs)
            if availableTime is not None:
                infoMessage = ms(FORTIFICATIONS.FORTINTELLIGENCE_CLANDESCRIPTION_DIRECTION_NOTAVAILABLE, date=BigWorld.wg_getShortDateFormat(availableTime))
                bodyParts.append(ms(FORTIFICATIONS.FORTINTELLIGENCE_CLANDESCRIPTION_DIRECTION_TOOLTIP_NOTAVAILABLE_INFO, date=BigWorld.wg_getShortDateFormat(availableTime)))
                header = ms(FORTIFICATIONS.FORTINTELLIGENCE_CLANDESCRIPTION_DIRECTION_TOOLTIP_NOTAVAILABLE_HEADER, direction=dirName)
            elif attackerClanDBID is None:
                if buildingsNames:
                    bodyParts.append(ms(FORTIFICATIONS.FORTINTELLIGENCE_CLANDESCRIPTION_DIRECTION_TOOLTIP_BUILDINGS, buildings=buildingsNames))
                if self.fortCtrl.getPermissions().canPlanAttack():
                    bodyParts.append(ms(FORTIFICATIONS.FORTINTELLIGENCE_CLANDESCRIPTION_DIRECTION_TOOLTIP_ATTACKINFO))
                    header = ms(FORTIFICATIONS.FORTINTELLIGENCE_CLANDESCRIPTION_DIRECTION_TOOLTIP_ATTACK, direction=dirName)
                else:
                    bodyParts.append(ms(FORTIFICATIONS.FORTINTELLIGENCE_CLANDESCRIPTION_DIRECTION_TOOLTIP_NOTCOMMANDERINFO))
                    header = ms(FORTIFICATIONS.FORTINTELLIGENCE_CLANDESCRIPTION_DIRECTION_TOOLTIP_NOTCOMMANDER, direction=dirName)
            else:
                bodyParts.append(ms(FORTIFICATIONS.FORTINTELLIGENCE_CLANDESCRIPTION_DIRECTION_TOOLTIP_BUSY_INFO, date=BigWorld.wg_getShortDateFormat(attackTime), clanName=attackerClanName))
                if buildingsNames:
                    bodyParts.append(ms(FORTIFICATIONS.FORTINTELLIGENCE_CLANDESCRIPTION_DIRECTION_TOOLTIP_BUILDINGS, buildings=buildingsNames))
                header = ms(FORTIFICATIONS.FORTINTELLIGENCE_CLANDESCRIPTION_DIRECTION_TOOLTIP_BUSY_HEADER, direction=dirName)
            return (header, '\n'.join(bodyParts), infoMessage)

    def __calculateDefencePeriod(self):
        currentDefencePeriod = time_utils.getTimeForLocal(self.__selectedDayStart, adjustDefenceHourToLocal(self.__item.getStartDefHour()))
        localDefHour = self.__item.getDefHourFor(currentDefencePeriod)
        self.__selectedDefencePeriodStart = time_utils.getTimeForLocal(self.__selectedDayStart, localDefHour)
        self.__selectedDefencePeriodEnd = self.__selectedDefencePeriodStart + time_utils.ONE_HOUR

    def __onCalendarDataSelected(self, event):
        timestamp = event.getTimestamp()
        if timestamp:
            self.__selectedDayStart, self.__selectedDayEnd = time_utils.getDayTimeBoundsForLocal(timestamp)
            self.__selectedDefencePeriodStart, self.__selectedDefencePeriodEnd = self.__selectedDayStart, self.__selectedDayEnd
            LOG_DEBUG(time.strftime('Attack time has been changed by user, %d.%m.%Y %H:%M', time_utils.getTimeStructInLocal(timestamp)))
            self.__calculateDefencePeriod()
            self.__makeData()

    def __setSelectedDate(self):
        if self.__upcomingAttack is not None:
            self.__selectedDayStart, self.__selectedDayEnd = time_utils.getDayTimeBoundsForLocal(self.__upcomingAttack.getStartTime())
        elif self.__attackInCooldown is not None:
            self.__selectedDayStart, self.__selectedDayEnd = time_utils.getDayTimeBoundsForLocal(self.__attackInCooldown.getStartTime())
        else:
            timestamp = self.__item.getAvailability(self.fortCtrl.getFort())
            self.__selectedDayStart, self.__selectedDayEnd = time_utils.getDayTimeBoundsForLocal(timestamp)
        self.__selectedDefencePeriodStart, self.__selectedDefencePeriodEnd = self.__selectedDayStart, self.__selectedDayEnd
        return

    def __getAttacksAndDeffences(self):
        clanID = self.__item.getClanDBID()
        fort = self.fortCtrl.getFort()
        currentUserTime = time.time()

        def filterInCooldown(item):
            if currentUserTime < item.getStartTime() + fortified_regions.g_cache.attackCooldownTime and item.isEnded():
                return True
            return False

        def filterUpcoming(item):
            if currentUserTime <= item.getStartTime() and not item.isEnded():
                return True
            return False

        upcomingAttacks = fort.getAttacks(clanID, filterUpcoming)
        attacksInCooldown = fort.getAttacks(clanID, filterInCooldown)
        defencesInCooldown = fort.getDefences(clanID, filterInCooldown)
        if upcomingAttacks:
            self.__upcomingAttack = upcomingAttacks[0]
            self.__weAreAtWar = True
        elif attacksInCooldown:
            self.__attackInCooldown = attacksInCooldown[-1]
            self.__weAreAtWar = True
        if defencesInCooldown:
            self.__defenceInCooldown = defencesInCooldown[-1]

    @process
    def __requestClanEmblem(self):
        if self.__item is not None:
            clanID = self.__item.getClanDBID()
            textureID = 'clanDescription%d' % clanID
            self.__clanEmblem = yield g_clanCache.getClanEmblemTextureID(clanID, False, textureID)
            self.__makeData()
        return
