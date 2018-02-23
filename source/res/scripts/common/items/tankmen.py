# Python bytecode 2.7 (decompiled from Python 2.7)
# Embedded file name: scripts/common/items/tankmen.py
import math
import ResMgr
import random
import struct
import nations
from functools import partial
from items import _xml, ITEM_TYPES, vehicles
from items.passports import PassportCache, passport_generator, maxAttempts, distinctFrom, acceptOn
from vehicles import VEHICLE_CLASS_TAGS
from debug_utils import LOG_ERROR, LOG_WARNING
from constants import IS_CLIENT, IS_WEB, ITEM_DEFS_PATH
from account_shared import AmmoIterator
if IS_CLIENT:
    from helpers import i18n
elif IS_WEB:
    from web_stubs import i18n
SKILL_NAMES = ('reserved',
 'commander',
 'radioman',
 'driver',
 'gunner',
 'loader',
 'repair',
 'fireFighting',
 'camouflage',
 'brotherhood',
 'reserved',
 'reserved',
 'reserved',
 'reserved',
 'reserved',
 'reserved',
 'commander_tutor',
 'commander_eagleEye',
 'commander_sixthSense',
 'commander_expert',
 'commander_universalist',
 'reserved',
 'reserved',
 'reserved',
 'reserved',
 'reserved',
 'reserved',
 'reserved',
 'driver_virtuoso',
 'driver_smoothDriving',
 'driver_badRoadsKing',
 'driver_rammingMaster',
 'driver_tidyPerson',
 'reserved',
 'reserved',
 'reserved',
 'reserved',
 'gunner_gunsmith',
 'gunner_sniper',
 'gunner_smoothTurret',
 'gunner_rancorous',
 'reserved',
 'reserved',
 'reserved',
 'reserved',
 'reserved',
 'loader_pedant',
 'loader_desperado',
 'loader_intuition',
 'reserved',
 'reserved',
 'reserved',
 'reserved',
 'radioman_inventor',
 'radioman_finder',
 'radioman_retransmitter',
 'radioman_lastEffort',
 'reserved',
 'reserved',
 'reserved',
 'reserved')
SKILL_INDICES = dict(((x[1], x[0]) for x in enumerate(SKILL_NAMES) if not x[1].startswith('reserved')))
ROLES = frozenset(('commander',
 'radioman',
 'driver',
 'gunner',
 'loader'))
ROLE_LIMITS = {'commander': 1,
 'driver': 1}
COMMON_SKILLS = frozenset(('repair',
 'fireFighting',
 'camouflage',
 'brotherhood'))
ROLES_AND_COMMON_SKILLS = ROLES | COMMON_SKILLS
SKILLS_BY_ROLES = {'commander': COMMON_SKILLS.union(('commander_tutor',
               'commander_expert',
               'commander_universalist',
               'commander_sixthSense',
               'commander_eagleEye')),
 'driver': COMMON_SKILLS.union(('driver_tidyPerson',
            'driver_smoothDriving',
            'driver_virtuoso',
            'driver_badRoadsKing',
            'driver_rammingMaster')),
 'gunner': COMMON_SKILLS.union(('gunner_smoothTurret',
            'gunner_sniper',
            'gunner_rancorous',
            'gunner_gunsmith')),
 'loader': COMMON_SKILLS.union(('loader_pedant', 'loader_desperado', 'loader_intuition')),
 'radioman': COMMON_SKILLS.union(('radioman_finder',
              'radioman_inventor',
              'radioman_lastEffort',
              'radioman_retransmitter'))}
ACTIVE_SKILLS = SKILLS_BY_ROLES['commander'] | SKILLS_BY_ROLES['radioman'] | SKILLS_BY_ROLES['driver'] | SKILLS_BY_ROLES['gunner'] | SKILLS_BY_ROLES['loader']
PERKS = frozenset(('brotherhood',
 'commander_sixthSense',
 'commander_expert',
 'driver_tidyPerson',
 'gunner_rancorous',
 'gunner_sniper',
 'loader_pedant',
 'loader_desperado',
 'loader_intuition',
 'radioman_lastEffort'))

class TANKMEN_ROLES():
    COMMANDER = 'commander'
    RADIOMAN = 'radioman'
    DRIVER = 'driver'
    GUNNER = 'gunner'
    LOADER = 'loader'


TANKMEN_ROLES_ORDER = {TANKMEN_ROLES.COMMANDER: 0,
 TANKMEN_ROLES.GUNNER: 1,
 TANKMEN_ROLES.DRIVER: 2,
 TANKMEN_ROLES.RADIOMAN: 3,
 TANKMEN_ROLES.LOADER: 4}
MAX_FREE_SKILLS_SIZE = 16
MAX_SKILL_LEVEL = 100
MIN_ROLE_LEVEL = 50
SKILL_LEVELS_PER_RANK = 50
COMMANDER_ADDITION_RATIO = 10
_MAX_FREE_XP = 2000000000
_LEVELUP_K1 = 50.0
_LEVELUP_K2 = 100.0

class _GROUP_TAG(object):
    """Class contains all available tags in group configuration."""
    PASSPORT_REPLACEMENT_FORBIDDEN = 'passportReplacementForbidden'
    RESTRICTIONS = (PASSPORT_REPLACEMENT_FORBIDDEN,)
    RANGE = RESTRICTIONS + tuple(ROLES)


def init(preloadEverything):
    if preloadEverything:
        getSkillsConfig()
        for nationID in xrange(len(nations.NAMES)):
            getNationConfig(nationID)


def getSkillsConfig():
    global _g_skillsConfig
    if _g_skillsConfig is None:
        _g_skillsConfig = _readSkillsConfig(ITEM_DEFS_PATH + 'tankmen/tankmen.xml')
    return _g_skillsConfig


def getSkillsMask(skills):
    result = 0
    for skill in skills:
        result |= 1 << SKILL_INDICES[skill]

    return result


ALL_SKILLS_MASK = getSkillsMask([ skill for skill in SKILL_NAMES if skill != 'reserved' ])

def getNationConfig(nationID):
    global _g_nationsConfig
    if _g_nationsConfig[nationID] is None:
        nationName = nations.NAMES[nationID]
        if nationName not in nations.AVAILABLE_NAMES:
            _g_nationsConfig[nationID] = {}
        else:
            _g_nationsConfig[nationID] = _readNationConfig(ITEM_DEFS_PATH + 'tankmen/' + nationName + '.xml')
    return _g_nationsConfig[nationID]


def generatePassport(nationID, isPremium=False):
    return passportProducer(nationID, isPremium)[1]


def passportProducer(nationID, isPremium=False):
    isPremium = False
    groups = getNationGroups(nationID, isPremium)
    w = random.random()
    summWeight = 0.0
    group = None
    for group in groups:
        weight = group['weight']
        if summWeight <= w < summWeight + weight:
            break
        summWeight += weight

    return (group, (nationID,
      isPremium,
      group['isFemales'],
      random.choice(group['firstNamesList']),
      random.choice(group['lastNamesList']),
      random.choice(group['iconsList'])))


def crewMemberPreviewProducer(nationID, isPremium=False, vehicleTypeID=None, role=None):
    vehicleName = vehicles.g_cache.vehicle(nationID, vehicleTypeID).name if vehicleTypeID else None
    nationalGroups = getNationGroups(nationID, isPremium)
    groups = [ g for g in nationalGroups if vehicleName in g.get('tags', set()) and role in g.get('tags', set()) ]
    if not groups:
        groups = [ g for g in nationalGroups if vehicleName in g.get('tags', set()) ]
    if not groups:
        groups = [ g for g in nationalGroups if role in g.get('tags', set()) ]
    if not groups:
        groups = nationalGroups
    group = random.choice(groups)
    pos = random.randint(0, min(map(len, (group['firstNamesList'], group['lastNamesList'], group['iconsList']))) - 1)
    return (group, (nationID,
      isPremium,
      group['isFemales'],
      group['firstNamesList'][pos],
      group['lastNamesList'][pos],
      group['iconsList'][pos]))


def generateSkills(role, skillsMask):
    """
    builds skills list with all skills according to role or particular skills according to mask
    :param role: string name of role, see ROLES
    :param skillsMask: mask to add roles from SKILLS_BY_ROLES
    :return: list containing subset of SKILLS_BY_ROLES[role]
    """
    skills = []
    if skillsMask != 0:
        tankmanSkills = set()
        for i in xrange(len(role)):
            roleSkills = SKILLS_BY_ROLES[role[i]]
            if skillsMask == ALL_SKILLS_MASK:
                tankmanSkills.update(roleSkills)
            for skill, idx in SKILL_INDICES.iteritems():
                if 1 << idx & skillsMask and skill in roleSkills:
                    tankmanSkills.add(skill)

        skills.extend(tankmanSkills)
    return skills


def generateTankmen(nationID, vehicleTypeID, roles, isPremium, roleLevel, skillsMask, isPreview=False):
    tankmenList = []
    prevPassports = PassportCache()
    for i in xrange(len(roles)):
        role = roles[i]
        pg = passport_generator(nationID, isPremium, partial(crewMemberPreviewProducer, vehicleTypeID=vehicleTypeID, role=role[0]) if isPreview else passportProducer, maxAttempts(10), distinctFrom(prevPassports), acceptOn('roles', role[0]))
        passport = next(pg)
        prevPassports.append(passport)
        skills = generateSkills(role, skillsMask)
        tmanCompDescr = generateCompactDescr(passport, vehicleTypeID, role[0], roleLevel, skills)
        tankmenList.append(tmanCompDescr)

    return tankmenList if len(tankmenList) == len(roles) else []


def generateCompactDescr(passport, vehicleTypeID, role, roleLevel, skills=(), lastSkillLevel=MAX_SKILL_LEVEL, dossierCompactDescr='', freeSkills=()):
    pack = struct.pack
    assert MIN_ROLE_LEVEL <= roleLevel <= MAX_SKILL_LEVEL
    nationID, isPremium, isFemale, firstNameID, lastNameID, iconID = passport
    header = ITEM_TYPES.tankman + (nationID << 4)
    cd = pack('4B', header, vehicleTypeID, SKILL_INDICES[role], roleLevel)
    numSkills = len(skills) + len(freeSkills)
    allSkills = [ SKILL_INDICES[s] for s in freeSkills ]
    for s in skills:
        allSkills.append(SKILL_INDICES[s])

    cd += pack((str(1 + numSkills) + 'B'), numSkills, *allSkills)
    cd += chr(lastSkillLevel if numSkills else 0)
    totalLevel = roleLevel - MIN_ROLE_LEVEL
    if skills:
        totalLevel += (len(skills) - 1) * MAX_SKILL_LEVEL
        totalLevel += lastSkillLevel
    rank, levelsToNextRank = divmod(totalLevel, SKILL_LEVELS_PER_RANK)
    levelsToNextRank = SKILL_LEVELS_PER_RANK - levelsToNextRank
    rankIDs = getNationConfig(nationID)['roleRanks'][role]
    maxRankIdx = len(rankIDs) - 1
    rank = min(rank, maxRankIdx)
    if rank == maxRankIdx:
        levelsToNextRank = 0
    isFemale = 1 if isFemale else 0
    isPremium = 1 if isPremium else 0
    flags = isFemale | isPremium << 1 | len(freeSkills) << 2
    cd += pack('<B4Hi', flags, firstNameID, lastNameID, iconID, rank | levelsToNextRank << 5, 0)
    cd += dossierCompactDescr
    return cd


def getNextUniqueIDs(databaseID, lastFirstNameID, lastLastNameID, lastIconID, nationID, isPremium, fnGroupID, lnGroupID, iGroupID):
    return (getNextUniqueID(databaseID, lastFirstNameID, nationID, isPremium, fnGroupID, 'firstNamesList'), getNextUniqueID(databaseID, lastLastNameID, nationID, isPremium, lnGroupID, 'lastNamesList'), getNextUniqueID(databaseID, lastIconID, nationID, isPremium, iGroupID, 'iconsList'))


def getNextUniqueID(databaseID, lastID, nationID, isPremium, groupID, name):
    ids = getNationConfig(nationID)['premiumGroups' if isPremium else 'normalGroups'][groupID][name]
    groupSize = len(ids)
    if groupSize == 0:
        return (-1, None)
    else:
        for n in (5, 7, 11, 13, 17, 19, 23, 29, 31):
            if groupSize % n != 0:
                step = n
                break
        else:
            step = 37

        nextID = lastID
        if lastID == -1:
            nextID = databaseID % min(7, groupSize)
        else:
            nextID += step
        if nextID >= groupSize:
            nextID -= max(groupSize, step)
        return (nextID, ids[nextID])


def stripNonBattle(compactDescr):
    return compactDescr[:6 + ord(compactDescr[4]) + 1 + 6]


def parseNationSpecAndRole(compactDescr):
    return (ord(compactDescr[0]) >> 4 & 15, ord(compactDescr[1]), ord(compactDescr[2]))


def compareMastery(tankmanDescr1, tankmanDescr2):
    return cmp(tankmanDescr1.totalXP(), tankmanDescr2.totalXP())


def commanderTutorXpBonusFactorForCrew(crew, ammo):
    tutorLevel = 0
    haveBrotherhood = True
    for t in crew:
        if t.role == 'commander':
            tutorLevel = t.skillLevel('commander_tutor')
            if not tutorLevel:
                return 0.0
        if t.skillLevel('brotherhood') != MAX_SKILL_LEVEL:
            haveBrotherhood = False

    skillsConfig = getSkillsConfig()
    if haveBrotherhood:
        tutorLevel += skillsConfig['brotherhood']['crewLevelIncrease']
    equipCrewLevelIncrease = 0
    cache = vehicles.g_cache
    for compDescr, count in AmmoIterator(ammo):
        itemTypeIdx, _, itemIdx = vehicles.parseIntCompactDescr(compDescr)
        if itemTypeIdx == ITEM_TYPES.equipment:
            equipCrewLevelIncrease += getattr(cache.equipments()[itemIdx], 'crewLevelIncrease', 0)

    tutorLevel += equipCrewLevelIncrease
    return tutorLevel * skillsConfig['commander_tutor']['xpBonusFactorPerLevel']


def fixObsoleteNames(compactDescr):
    cd = compactDescr
    header = ord(cd[0])
    assert header & 15 == ITEM_TYPES.tankman
    nationID = header >> 4 & 15
    conf = getNationConfig(nationID)
    namesOffset = ord(cd[4]) + 7
    firstNameID, lastNameID = struct.unpack('<2H', cd[namesOffset:namesOffset + 4])
    hasChanges = False
    if firstNameID not in conf['firstNames']:
        hasChanges = True
        firstNameID = generatePassport(nationID)[3]
    if lastNameID not in conf['lastNames']:
        hasChanges = True
        lastNameID = generatePassport(nationID)[4]
    return cd if not hasChanges else cd[:namesOffset] + struct.pack('<2H', firstNameID, lastNameID) + cd[namesOffset + 4:]


class OperationsRestrictions(object):
    """Class provides restrictions that must be checked in tankmen operations by:
        - group tags if group is unique for tankman.
    """
    __slots__ = ('__groupTags',)

    def __init__(self, tags=None):
        super(OperationsRestrictions, self).__init__()
        self.__groupTags = tags or frozenset()

    def isPassportReplacementForbidden(self):
        return _GROUP_TAG.PASSPORT_REPLACEMENT_FORBIDDEN in self.__groupTags


class TankmanDescr(object):

    def __init__(self, compactDescr, battleOnly=False):
        self.__initFromCompactDescr(compactDescr, battleOnly)

    @property
    def skills(self):
        return list(self.__skills)

    @property
    def freeSkills(self):
        return list(self.__skills[:self.freeSkillsNumber])

    @property
    def lastSkillLevel(self):
        return self.__lastSkillLevel

    @property
    def lastSkillNumber(self):
        return len(self.__skills)

    @property
    def skillLevels(self):
        for skillName in self.__skills:
            level = MAX_SKILL_LEVEL if skillName != self.__skills[-1] else self.__lastSkillLevel
            yield (skillName, level)

    @property
    def isUnique(self):
        g = getNationGroups(self.nationID, self.isPremium)[self.gid] if self.gid else {}
        return 1 == len(g['firstNames']) * len(g['lastNames']) * len(g['icons']) if g else False

    def efficiencyFactorOnVehicle(self, vehicleDescrType):
        _, _, vehicleTypeID = vehicles.parseIntCompactDescr(vehicleDescrType.compactDescr)
        factor = 1.0
        if vehicleTypeID != self.vehicleTypeID:
            isPremium, isSameClass = self.__paramsOnVehicle(vehicleDescrType)
            if isSameClass:
                factor = 1.0 if isPremium else 0.75
            else:
                factor = 0.75 if isPremium else 0.5
        return factor

    def efficiencyOnVehicle(self, vehicleDescr):
        _, nationID, _ = vehicles.parseIntCompactDescr(vehicleDescr.type.compactDescr)
        assert nationID == self.nationID
        factor = self.efficiencyFactorOnVehicle(vehicleDescr.type)
        addition = vehicleDescr.miscAttrs['crewLevelIncrease']
        return (factor, addition)

    def battleXpGain(self, xp, vehicleType, tankmanHasSurvived, commanderTutorXpBonusFactor):
        nationID, vehicleTypeID = vehicleType.id
        assert nationID == self.nationID
        if vehicleTypeID != self.vehicleTypeID:
            isPremium, isSameClass = self.__paramsOnVehicle(vehicleType)
            if isPremium:
                xp *= 1.0 if isSameClass else 0.5
            else:
                xp *= 0.5 if isSameClass else 0.25
        xp *= vehicleType.crewXpFactor
        if not tankmanHasSurvived:
            xp *= 0.9
        if self.role != 'commander':
            xp *= 1.0 + commanderTutorXpBonusFactor
        return int(xp)

    @staticmethod
    def levelUpXpCost(fromSkillLevel, skillSeqNum):
        costs = _g_levelXpCosts
        return 2 ** skillSeqNum * (costs[fromSkillLevel + 1] - costs[fromSkillLevel])

    def skillLevel(self, skillName):
        if skillName not in self.skills:
            return None
        else:
            return MAX_SKILL_LEVEL if skillName != self.__skills[-1] else self.__lastSkillLevel

    def totalXP(self):
        levelCosts = _g_levelXpCosts
        xp = self.freeXP + levelCosts[self.roleLevel]
        numSkills = self.lastSkillNumber - self.freeSkillsNumber
        if numSkills:
            xp += levelCosts[self.__lastSkillLevel] * 2 ** numSkills
            for idx in xrange(1, numSkills):
                xp += levelCosts[MAX_SKILL_LEVEL] * 2 ** idx

        return xp

    def addXP(self, xp):
        self.freeXP = min(_MAX_FREE_XP, self.freeXP + xp)
        while self.roleLevel < MAX_SKILL_LEVEL:
            xpCost = self.levelUpXpCost(self.roleLevel, 0)
            if xpCost > self.freeXP:
                break
            self.freeXP -= xpCost
            self.roleLevel += 1
            self.__updateRankAtSkillLevelUp()

        if self.roleLevel == MAX_SKILL_LEVEL and self.__skills:
            self.__levelUpLastSkill()

    def addSkill(self, skillName):
        if skillName in self.skills:
            raise ValueError(skillName)
        if skillName not in ACTIVE_SKILLS:
            raise ValueError(skillName)
        if self.roleLevel != MAX_SKILL_LEVEL:
            raise ValueError(self.roleLevel)
        if self.__skills and self.__lastSkillLevel != MAX_SKILL_LEVEL:
            raise ValueError(self.__lastSkillLevel)
        self.__skills.append(skillName)
        self.__lastSkillLevel = 0
        self.__levelUpLastSkill()

    def isFreeDropSkills(self):
        if self.lastSkillNumber < 1 + self.freeSkillsNumber:
            return True
        return True if self.lastSkillNumber == 1 + self.freeSkillsNumber and self.__lastSkillLevel == 0 else False

    def dropSkills(self, xpReuseFraction=0.0, throwIfNoChange=True):
        assert 0.0 <= xpReuseFraction <= 1.0
        if len(self.__skills) == 0:
            if throwIfNoChange:
                raise Exception('attempt to reset empty skills')
            return
        prevTotalXP = self.totalXP()
        if self.numLevelsToNextRank != 0:
            numSkills = self.lastSkillNumber - self.freeSkillsNumber
            if numSkills < 1:
                if throwIfNoChange:
                    raise Exception('attempt to reset free skills')
                return
            self.numLevelsToNextRank += self.__lastSkillLevel
            if numSkills > 1:
                self.numLevelsToNextRank += MAX_SKILL_LEVEL * (numSkills - 1)
        del self.__skills[self.freeSkillsNumber:]
        if self.freeSkillsNumber:
            self.__lastSkillLevel = MAX_SKILL_LEVEL
        else:
            self.__lastSkillLevel = 0
        if xpReuseFraction != 0.0:
            self.addXP(int(xpReuseFraction * (prevTotalXP - self.totalXP())))

    def dropSkill(self, skillName, xpReuseFraction=0.0):
        assert 0.0 <= xpReuseFraction <= 1.0
        idx = self.__skills.index(skillName)
        prevTotalXP = self.totalXP()
        numSkills = self.lastSkillNumber - self.freeSkillsNumber
        levelsDropped = MAX_SKILL_LEVEL
        if numSkills == 1:
            levelsDropped = self.__lastSkillLevel
            self.__lastSkillLevel = 0
        elif idx + 1 == numSkills:
            levelsDropped = self.__lastSkillLevel
            self.__lastSkillLevel = MAX_SKILL_LEVEL
        del self.__skills[idx]
        if self.numLevelsToNextRank != 0:
            self.numLevelsToNextRank += levelsDropped
        if xpReuseFraction != 0.0:
            self.addXP(int(xpReuseFraction * (prevTotalXP - self.totalXP())))

    def respecialize(self, newVehicleTypeID, minNewRoleLevel, vehicleChangeRoleLevelLoss, classChangeRoleLevelLoss, becomesPremium):
        assert 0 <= minNewRoleLevel <= MAX_SKILL_LEVEL
        assert 0.0 <= vehicleChangeRoleLevelLoss <= 1.0
        assert 0.0 <= classChangeRoleLevelLoss <= 1.0
        newVehTags = vehicles.g_list.getList(self.nationID)[newVehicleTypeID]['tags']
        roleLevelLoss = 0.0 if newVehicleTypeID == self.vehicleTypeID else vehicleChangeRoleLevelLoss
        isSameClass = len(self.__vehicleTags & newVehTags & vehicles.VEHICLE_CLASS_TAGS)
        if not isSameClass:
            roleLevelLoss += classChangeRoleLevelLoss
        newRoleLevel = int(round(self.roleLevel * (1.0 - roleLevelLoss)))
        newRoleLevel = max(minNewRoleLevel, newRoleLevel)
        self.vehicleTypeID = newVehicleTypeID
        self.__vehicleTags = newVehTags
        if newRoleLevel > self.roleLevel:
            self.__updateRankAtSkillLevelUp(newRoleLevel - self.roleLevel)
            self.roleLevel = newRoleLevel
        elif newRoleLevel < self.roleLevel:
            if self.numLevelsToNextRank != 0:
                self.numLevelsToNextRank += self.roleLevel - newRoleLevel
            self.roleLevel = newRoleLevel
            self.addXP(0)

    def validatePassport(self, isPremium, isFemale, fnGroupID, firstNameID, lnGroupID, lastNameID, iGroupID, iconID):
        if isFemale is None:
            isFemale = self.isFemale
        config = getNationConfig(self.nationID)
        groups = config['premiumGroups' if isPremium else 'normalGroups']
        if firstNameID is not None:
            if fnGroupID >= len(groups):
                return (False, 'Invalid fn group', None)
            group = groups[fnGroupID]
            if group['notInShop']:
                return (False, 'Not in shop', None)
            if bool(group['isFemales']) != bool(isFemale):
                return (False, 'Invalid group sex', None)
            if firstNameID not in group['firstNames']:
                return (False, 'Invalid first name', None)
        if lastNameID is not None:
            if lnGroupID >= len(groups):
                return (False, 'Invalid ln group', None)
            group = groups[lnGroupID]
            if group['notInShop']:
                return (False, 'Not in shop', None)
            if bool(group['isFemales']) != bool(isFemale):
                return (False, 'Invalid group sex', None)
            if lastNameID not in group['lastNames']:
                return (False, 'Invalid last name', None)
        if iconID is not None:
            if iGroupID >= len(groups):
                return (False, 'Invalid i group', None)
            group = groups[iGroupID]
            if group['notInShop']:
                return (False, 'Not in shop', None)
            if bool(group['isFemales']) != bool(isFemale):
                return (False, 'Invalid group sex', None)
            if iconID not in group['icons']:
                return (False, 'Invalid icon id', None)
        if firstNameID is None:
            firstNameID = self.firstNameID
        if lastNameID is None:
            lastNameID = self.lastNameID
        if iconID is None:
            iconID = self.iconID
        return (True, '', (isFemale,
          firstNameID,
          lastNameID,
          iconID))

    def replacePassport(self, ctx):
        isFemale, firstNameID, lastNameID, iconID = ctx
        self.isFemale = isFemale
        self.firstNameID = firstNameID
        self.lastNameID = lastNameID
        self.iconID = iconID

    def getPassport(self):
        """
        Gets passport data: nationID, isPremium, isFemale, firstNameID, lastNameID, iconID
        """
        return (self.nationID,
         self.isPremium,
         self.isFemale,
         self.firstNameID,
         self.lastNameID,
         self.iconID)

    def getRestrictions(self):
        """Gets restrictions that must be checked in tankman operations.
        :return: instance of OperationsRestrictions.
        """
        return OperationsRestrictions(getGroupTags(*self.getPassport()))

    @property
    def group(self):
        """
        Returns tankman composite group.
        TODO: add additional group range when implemented
        """
        return int(self.isFemale) | int(self.isPremium) << 1 | int(self.gid) << 2

    def makeCompactDescr(self):
        pack = struct.pack
        header = ITEM_TYPES.tankman + (self.nationID << 4)
        cd = pack('4B', header, self.vehicleTypeID, SKILL_INDICES[self.role], self.roleLevel)
        numSkills = self.lastSkillNumber
        skills = [ SKILL_INDICES[s] for s in self.__skills ]
        cd += pack((str(1 + numSkills) + 'B'), numSkills, *skills)
        cd += chr(self.__lastSkillLevel if numSkills else 0)
        isFemale = 1 if self.isFemale else 0
        isPremium = 1 if self.isPremium else 0
        flags = isFemale | isPremium << 1 | self.freeSkillsNumber << 2
        cd += pack('<B4Hi', flags, self.firstNameID, self.lastNameID, self.iconID, self.__rankIdx & 31 | (self.numLevelsToNextRank & 2047) << 5, self.freeXP)
        cd += self.dossierCompactDescr
        return cd

    def isRestorable(self):
        """
        Tankman is restorable if he has at least one skill fully developed or
        if his main speciality is 100% and he has enough free experience for one skill provided that
        vehicle is recoverable and crew is not locked.
        :return: bool
        """
        vehicleTags = self.__vehicleTags
        return (len(self.skills) > 0 and self.skillLevel(self.skills[0]) == MAX_SKILL_LEVEL or self.roleLevel == MAX_SKILL_LEVEL and self.freeXP >= _g_totalFirstSkillXpCost) and not ('lockCrew' in vehicleTags and 'unrecoverable' in vehicleTags)

    def __initFromCompactDescr(self, compactDescr, battleOnly):
        cd = compactDescr
        unpack = struct.unpack
        try:
            header, self.vehicleTypeID, roleID, self.roleLevel, numSkills = unpack('5B', cd[:5])
            cd = cd[5:]
            assert header & 15 == ITEM_TYPES.tankman
            nationID = header >> 4 & 15
            nations.NAMES[nationID]
            self.nationID = nationID
            self.__vehicleTags = vehicles.g_list.getList(nationID)[self.vehicleTypeID]['tags']
            self.role = SKILL_NAMES[roleID]
            if self.role not in ROLES:
                raise KeyError(self.role)
            if self.roleLevel > MAX_SKILL_LEVEL:
                raise ValueError(self.roleLevel)
            self.__skills = []
            if numSkills == 0:
                self.__lastSkillLevel = 0
            else:
                for skillID in unpack(str(numSkills) + 'B', cd[:numSkills]):
                    skillName = SKILL_NAMES[skillID]
                    if skillName not in ACTIVE_SKILLS:
                        raise KeyError(skillName, self.role)
                    self.__skills.append(skillName)

                self.__lastSkillLevel = ord(cd[numSkills])
                if self.__lastSkillLevel > MAX_SKILL_LEVEL:
                    raise ValueError(self.__lastSkillLevel)
            cd = cd[numSkills + 1:]
            flags = unpack('<B', cd[:1])[0]
            self.isFemale = bool(flags & 1)
            self.isPremium = bool(flags & 2)
            self.freeSkillsNumber = flags >> 2
            if self.freeSkillsNumber == len(self.__skills) and self.freeSkillsNumber:
                self.__lastSkillLevel = MAX_SKILL_LEVEL
            cd = cd[1:]
            nationConfig = getNationConfig(nationID)
            self.firstNameID, self.lastNameID, self.iconID, rank, self.freeXP = unpack('<4Hi', cd[:12].ljust(12, '\x00'))
            self.gid, _ = findGroupsByIDs(getNationGroups(nationID, self.isPremium), self.isFemale, self.firstNameID, self.lastNameID, self.iconID).pop(0)
            if battleOnly:
                del self.freeXP
                return
            cd = cd[12:]
            self.dossierCompactDescr = cd
            self.__rankIdx = rank & 31
            self.numLevelsToNextRank = rank >> 5
            self.rankID = nationConfig['roleRanks'][self.role][self.__rankIdx]
            if self.firstNameID not in nationConfig['firstNames']:
                raise KeyError(self.firstNameID)
            if self.lastNameID not in nationConfig['lastNames']:
                raise KeyError(self.lastNameID)
            if self.iconID not in nationConfig['icons']:
                raise KeyError(self.iconID)
        except Exception:
            LOG_ERROR('(compact description to XML mismatch?)', compactDescr)
            raise

    def __paramsOnVehicle(self, vehicleType):
        isPremium = 'premium' in vehicleType.tags or 'premiumIGR' in vehicleType.tags
        isSameClass = len(VEHICLE_CLASS_TAGS & vehicleType.tags & self.__vehicleTags)
        return (isPremium, isSameClass)

    def __updateRankAtSkillLevelUp(self, numLevels=1):
        if numLevels < self.numLevelsToNextRank:
            self.numLevelsToNextRank -= numLevels
            return
        rankIDs = getNationConfig(self.nationID)['roleRanks'][self.role]
        maxRankIdx = len(rankIDs) - 1
        while numLevels >= self.numLevelsToNextRank > 0:
            numLevels -= self.numLevelsToNextRank
            self.__rankIdx = min(self.__rankIdx + 1, maxRankIdx)
            self.rankID = rankIDs[self.__rankIdx]
            self.numLevelsToNextRank = SKILL_LEVELS_PER_RANK if self.__rankIdx < maxRankIdx else 0

    def __levelUpLastSkill(self):
        numSkills = self.lastSkillNumber - self.freeSkillsNumber
        while self.__lastSkillLevel < MAX_SKILL_LEVEL:
            xpCost = self.levelUpXpCost(self.__lastSkillLevel, numSkills)
            if xpCost > self.freeXP:
                break
            self.freeXP -= xpCost
            self.__lastSkillLevel += 1
            self.__updateRankAtSkillLevelUp()


def makeTmanDescrByTmanData(tmanData):
    nationID = tmanData['nationID']
    if not 0 <= nationID < len(nations.AVAILABLE_NAMES):
        raise Exception('Invalid nation')
    vehicleTypeID = tmanData['vehicleTypeID']
    if vehicleTypeID not in vehicles.g_list.getList(nationID):
        raise Exception('Invalid vehicle')
    role = tmanData['role']
    if role not in ROLES:
        raise Exception('Invalid role')
    roleLevel = tmanData.get('roleLevel', 50)
    if not 50 <= roleLevel <= MAX_SKILL_LEVEL:
        raise Exception('Wrong tankman level')
    skills = tmanData.get('skills', [])
    freeSkills = tmanData.get('freeSkills', [])
    if skills is None:
        skills = []
    if freeSkills is None:
        freeSkills = []
    __validateSkills(skills)
    __validateSkills(freeSkills)
    if not set(skills).isdisjoint(set(freeSkills)):
        raise Exception('Free skills and skills must be disjoint.')
    if len(freeSkills) > MAX_FREE_SKILLS_SIZE:
        raise Exception('Free skills count is too big.')
    isFemale = tmanData.get('isFemale', False)
    isPremium = tmanData.get('isPremium', False)
    fnGroupID = tmanData.get('fnGroupID', 0)
    firstNameID = tmanData.get('firstNameID', None)
    lnGroupID = tmanData.get('lnGroupID', 0)
    lastNameID = tmanData.get('lastNameID', None)
    iGroupID = tmanData.get('iGroupID', 0)
    iconID = tmanData.get('iconID', None)
    groups = getNationConfig(nationID)['normalGroups' if not isPremium else 'premiumGroups']
    if fnGroupID >= len(groups):
        raise Exception('Invalid group fn ID')
    group = groups[fnGroupID]
    if bool(group['isFemales']) != bool(isFemale):
        raise Exception('Invalid group sex')
    if firstNameID is not None:
        if firstNameID not in group['firstNamesList']:
            raise Exception('firstNameID is not in valid group')
    else:
        firstNameID = random.choice(group['firstNamesList'])
    if lnGroupID >= len(groups):
        raise Exception('Invalid group ln ID')
    group = groups[lnGroupID]
    if bool(group['isFemales']) != bool(isFemale):
        raise Exception('Invalid group sex')
    if lastNameID is not None:
        if lastNameID not in group['lastNamesList']:
            raise Exception('lastNameID is not in valid group')
    else:
        lastNameID = random.choice(group['lastNamesList'])
    if iGroupID >= len(groups):
        raise Exception('Invalid group ln ID')
    group = groups[iGroupID]
    if bool(group['isFemales']) != bool(isFemale):
        raise Exception('Invalid group sex')
    if iconID is not None:
        if iconID not in group['iconsList']:
            raise Exception('iconID is not in valid group')
    else:
        iconID = random.choice(group['iconsList'])
    passport = (nationID,
     isPremium,
     isFemale,
     firstNameID,
     lastNameID,
     iconID)
    tankmanCompDescr = generateCompactDescr(passport, vehicleTypeID, role, roleLevel, skills, freeSkills=freeSkills)
    freeXP = tmanData.get('freeXP', 0)
    if freeXP != 0:
        tankmanDescr = TankmanDescr(tankmanCompDescr)
        tankmanDescr.addXP(freeXP)
        tankmanCompDescr = tankmanDescr.makeCompactDescr()
    return tankmanCompDescr


def isRestorable(tankmanCD):
    tankmanDescr = TankmanDescr(tankmanCD)
    return tankmanDescr.isRestorable()


def ownVehicleHasTags(tankmanCD, tags=()):
    nation, vehTypeID, _ = parseNationSpecAndRole(tankmanCD)
    vehicleType = vehicles.g_cache.vehicle(nation, vehTypeID)
    return bool(vehicleType.tags.intersection(tags))


def hasTagInTankmenGroup(nationID, groupID, isPremium, tag):
    """
    Checks if tankmen group has specified tag.
    :param nationID: int
    :param groupID: int
    :param isPremium: bool
    :param tag: str
    :return bool
    """
    nationGroups = getNationGroups(nationID, isPremium)
    if groupID < 0 or groupID >= len(nationGroups):
        LOG_WARNING('tankmen.hasTagInTankmenGroup: wrong value of the groupID (index out of range)', groupID)
        return False
    groupSet = nationGroups[groupID] if groupID >= 0 else {}
    return False if 'tags' not in groupSet else tag in groupSet['tags']


def unpackCrewParams(crewGroup):
    """
    :param crewGroup: int
    :return tuple(groupID<int>, isFemale<bool>, isPremium<bool>)
    """
    groupID = crewGroup >> 2
    isFemale = bool(crewGroup & 1)
    isPremium = bool(crewGroup & 2)
    return (groupID, isFemale, isPremium)


def tankmenGroupHasRole(nationID, groupID, isPremium, role):
    """
    Checks if tankmen group can have specified role.
    :param nationID: int
    :param groupID: int
    :param isPremium: bool
    :param role: str
    :return bool
    """
    nationGroups = getNationGroups(nationID, isPremium)
    groupSet = nationGroups[groupID] if groupID >= 0 else {}
    return False if 'roles' not in groupSet else role in groupSet['roles']


def tankmenGroupCanChangeRole(nationID, groupID, isPremium):
    """
    Checks if tankmen group can change role.
    :param nationID: int
    :param groupID: int
    :param isPremium: bool
    :param role: str
    :return bool
    """
    nationGroups = getNationGroups(nationID, isPremium)
    groupSet = nationGroups[groupID] if groupID >= 0 else {}
    return True if 'roles' not in groupSet else len(groupSet['roles']) > 1


def getNationGroups(nationID, isPremium):
    """Gets nation-specific configuration of tankmen.
    :param nationID: integer containing ID of nation.
    :param isPremium: if value equals True that gets premium groups, otherwise - normal.
    :return: dictionary containing nation-specific configuration.
    """
    config = getNationConfig(nationID)
    return config['premiumGroups' if isPremium else 'normalGroups']


def findGroupsByIDs(groups, isFemale, firstNameID, secondNameID, iconID):
    """Tries to find groups by the following criteria: ID of first name, ID of last name
        and iconID. The first item has max. overlaps, and so on.
    :param groups: integer containing ID of nation.
    :param isFemale: boolean containing gender flag.
    :param firstNameID: integer containing ID of first name.
    :param secondNameID: integer containing ID of last name.
    :param iconID: integer containing ID of icon.
    :return: list where each item is tuple(ID/index of group, weight) and first item has max. overlaps.
    """
    found = [(-1, 0)]
    for groupID, group in enumerate(groups):
        if isFemale != group['isFemales']:
            continue
        overlap = 0
        if firstNameID in group['firstNames']:
            overlap += 1
        if secondNameID in group['lastNames']:
            overlap += 1
        if iconID in group['icons']:
            overlap += 1
        if overlap:
            found.append((groupID, overlap))

    found.sort(key=lambda item: item[1], reverse=True)
    return found


def getGroupTags(nationID, isPremium, isFemale, firstNameID, secondNameID, iconID):
    """ Gets tags of group if all ids equals desired, otherwise - empty value.
    :param nationID: integer containing ID of nation.
    :param isPremium: if value equals True that gets premium groups, otherwise - normal.
    :param isFemale: boolean containing gender flag.
    :param firstNameID: integer containing ID of first name.
    :param secondNameID: integer containing ID of last name.
    :param iconID: integer containing ID of icon.
    :return: frozenset containing tags of group.
    """
    groups = getNationGroups(nationID, isPremium)
    found = findGroupsByIDs(groups, isFemale, firstNameID, secondNameID, iconID)
    if found:
        groupID, overlap = found[0]
        if overlap == 3:
            return groups[groupID]['tags']
    return frozenset()


def __validateSkills(skills):
    if len(set(skills)) != len(skills):
        raise Exception('Duplicate tankman skills')
    for skill in skills:
        if skill not in SKILL_INDICES:
            raise Exception('Wrong tankman skill')


def _readNationConfig(xmlPath):
    section = ResMgr.openSection(xmlPath)
    if section is None:
        _xml.raiseWrongXml(None, xmlPath, 'can not open or read')
    res = _readNationConfigSection((None, xmlPath), section)
    section = None
    ResMgr.purge(xmlPath, True)
    return res


def _readGroupRoles(xmlCtx, section, subsectionName):
    """
    Returns contents of roles tag group as an immutable subset of ROLES
    :param xmlCtx: xml context for reporting and error handling purposes.
    :param section: group section to read roles section.
    :param subsectionName: name of roles section inside group section.
    :return: subset of ROLES.
    """
    source = _xml.readStringOrNone(xmlCtx, section, subsectionName)
    if source is not None:
        tags = source.split()
        roles = []
        for tag in tags:
            if tag not in ROLES:
                _xml.raiseWrongXml(xmlCtx, subsectionName, 'unknown tag "{}"'.format(tag))
            roles.append(tag)

    else:
        tags = ROLES
    return frozenset(tags)


def _readNationConfigSection(xmlCtx, section):
    res = {}
    firstNames = {}
    lastNames = {}
    icons = {}
    for kindName in ('normalGroups', 'premiumGroups'):
        groups = []
        res[kindName] = groups
        totalWeight = 0.0
        for sname, subsection in _xml.getChildren(xmlCtx, section, kindName):
            ctx = (xmlCtx, kindName + '/' + sname)
            group = {'notInShop': subsection.readBool('notInShop', False),
             'isFemales': 'female' == _xml.readNonEmptyString(ctx, subsection, 'sex'),
             'firstNames': _readIDs((ctx, 'firstNames'), _xml.getChildren(ctx, subsection, 'firstNames'), firstNames, _parseName),
             'lastNames': _readIDs((ctx, 'lastNames'), _xml.getChildren(ctx, subsection, 'lastNames'), lastNames, _parseName),
             'icons': _readIDs((ctx, 'icons'), _xml.getChildren(ctx, subsection, 'icons'), icons, _parseIcon),
             'tags': _readGroupTags((ctx, 'tags'), subsection, 'tags'),
             'roles': _readGroupRoles((ctx, 'roles'), subsection, 'roles')}
            group['firstNamesList'] = list(group['firstNames'])
            group['lastNamesList'] = list(group['lastNames'])
            group['iconsList'] = list(group['icons'])
            weight = _xml.readNonNegativeFloat(ctx, subsection, 'weight')
            totalWeight += weight
            group['weight'] = weight
            group['name'] = sname
            groups.append(group)

        totalWeight = max(0.001, totalWeight)
        for group in groups:
            group['weight'] /= totalWeight

    ranks, rankIDsByNames = _readRanks((xmlCtx, 'ranks'), _xml.getChildren(xmlCtx, section, 'ranks'))
    res['roleRanks'] = _readRoleRanks((xmlCtx, 'roleRanks'), _xml.getSubsection(xmlCtx, section, 'roleRanks'), rankIDsByNames)
    if IS_CLIENT or IS_WEB:
        res['firstNames'] = firstNames
        res['lastNames'] = lastNames
        res['icons'] = icons
        res['ranks'] = ranks
    else:
        res['firstNames'] = frozenset(firstNames)
        res['lastNames'] = frozenset(lastNames)
        res['icons'] = frozenset(icons)
    return res


def _readRanks(xmlCtx, subsections):
    ranks = []
    rankIDsByNames = {}
    for sname, subsection in subsections:
        if rankIDsByNames.has_key(sname):
            _xml.raiseWrong(xmlCtx, sname, 'is not unique')
        ctx = (xmlCtx, sname)
        rankIDsByNames[sname] = len(ranks)
        if not (IS_CLIENT or IS_WEB):
            ranks.append(None)
        ranks.append({'userString': i18n.makeString(_xml.readNonEmptyString(ctx, subsection, 'userString')),
         'icon': _parseIcon((ctx, 'icon'), _xml.getSubsection(ctx, subsection, 'icon'))})

    return (ranks, rankIDsByNames)


def _readRoleRanks(xmlCtx, section, rankIDsByNames):
    res = {}
    for roleName in ROLES:
        rankIDs = []
        res[roleName] = rankIDs
        for rankName in _xml.readNonEmptyString(xmlCtx, section, roleName).split():
            rankIDs.append(rankIDsByNames[rankName])

    return res


def _readIDs(xmlCtx, subsections, accumulator, parser):
    res = set()
    for sname, subsection in subsections:
        try:
            id = int(sname[1:])
        except Exception:
            id = -1

        if sname[0] != '_' or not 0 <= id <= 65535:
            _xml.raiseWrongSection(xmlCtx, sname)
        if id in accumulator:
            _xml.raiseWrongXml(xmlCtx, sname, 'ID is not unique')
        accumulator[id] = parser((xmlCtx, sname), subsection)
        res.add(id)

    if not res:
        _xml.raiseWrongXml(xmlCtx, '', 'is empty')
    return res


if not (IS_CLIENT or IS_WEB):

    def _parseName(xmlCtx, section):
        return None


    _parseIcon = _parseName
else:

    def _parseName(xmlCtx, section):
        return i18n.makeString(_xml.readNonEmptyString(xmlCtx, section, ''))


    def _parseIcon(xmlCtx, section):
        return _xml.readNonEmptyString(xmlCtx, section, '')


def _readGroupTags(xmlCtx, section, subsectionName):
    source = _xml.readStringOrNone(xmlCtx, section, subsectionName)
    if source is not None:
        tags = source.split()
        restrictions = []
        for tag in tags:
            if not (tag in _GROUP_TAG.RANGE or vehicles.g_list.isVehicleExisting(tag)):
                _xml.raiseWrongXml(xmlCtx, subsectionName, 'unknown tag "{}"'.format(tag))
            if tag in _GROUP_TAG.RESTRICTIONS:
                restrictions.append(tag)

        if restrictions and _GROUP_TAG.PASSPORT_REPLACEMENT_FORBIDDEN not in restrictions:
            _xml.raiseWrongXml(xmlCtx, subsectionName, 'Group contains tags of restrictions {}, so tag "{}" is mandatory'.format(restrictions, _GROUP_TAG.PASSPORT_REPLACEMENT_FORBIDDEN))
    else:
        tags = []
    return frozenset(tags)


def _readSkillsConfig(xmlPath):
    xmlCtx = (None, xmlPath)
    section = ResMgr.openSection(xmlPath)
    if section is None:
        _xml.raiseWrongXml(None, xmlPath, 'can not open or read')
    res = {}
    for skillName in ROLES:
        res[skillName] = _readRole(xmlCtx, section, 'roles/' + skillName)

    section = _xml.getSubsection(xmlCtx, section, 'skills')
    xmlCtx = (xmlCtx, 'skills')
    for skillName in ACTIVE_SKILLS:
        res[skillName] = _g_skillConfigReaders[skillName](xmlCtx, section, skillName)

    section = None
    ResMgr.purge(xmlPath, True)
    return res


def _readSkillBasics(xmlCtx, section, subsectionName):
    section = _xml.getSubsection(xmlCtx, section, subsectionName)
    xmlCtx = (xmlCtx, subsectionName)
    res = {}
    if IS_CLIENT or IS_WEB:
        res['userString'] = i18n.makeString(section.readString('userString'))
        res['description'] = i18n.makeString(section.readString('description'))
        res['icon'] = _xml.readNonEmptyString(xmlCtx, section, 'icon')
    return (res, xmlCtx, section)


def _readRole(xmlCtx, section, subsectionName):
    res, xmlCtx, section = _readSkillBasics(xmlCtx, section, subsectionName)
    return res


def _readSkillInt(paramName, minVal, xmlCtx, section, subsectionName):
    res, xmlCtx, section = _readSkillBasics(xmlCtx, section, subsectionName)
    res[paramName] = _xml.readInt(xmlCtx, section, paramName, minVal)
    return res


def _readSkillNonNegFloat(paramName, xmlCtx, section, subsectionName):
    res, xmlCtx, section = _readSkillBasics(xmlCtx, section, subsectionName)
    res[paramName] = _xml.readNonNegativeFloat(xmlCtx, section, paramName)
    return res


def _readSkillFraction(paramName, xmlCtx, section, subsectionName):
    res, xmlCtx, section = _readSkillBasics(xmlCtx, section, subsectionName)
    res[paramName] = _xml.readFraction(xmlCtx, section, paramName)
    return res


def _readGunnerRancorous(xmlCtx, section, subsectionName):
    res, xmlCtx, section = _readSkillBasics(xmlCtx, section, subsectionName)
    res['duration'] = _xml.readPositiveFloat(xmlCtx, section, 'duration')
    res['sectorHalfAngle'] = math.radians(_xml.readPositiveFloat(xmlCtx, section, 'sectorHalfAngle'))
    return res


def _readGunnerGunsmith(xmlCtx, section, subsectionName):
    res, xmlCtx, section = _readSkillBasics(xmlCtx, section, subsectionName)
    res['shotDispersionFactorPerLevel'] = _xml.readPositiveFloat(xmlCtx, section, 'shotDispersionFactorPerLevel')
    return res


def _readCommanderEagleEye(xmlCtx, section, subsectionName):
    res, xmlCtx, section = _readSkillBasics(xmlCtx, section, subsectionName)
    res['distanceFactorPerLevelWhenDeviceWorking'] = _xml.readPositiveFloat(xmlCtx, section, 'distanceFactorPerLevelWhenDeviceWorking')
    res['distanceFactorPerLevelWhenDeviceDestroyed'] = _xml.readPositiveFloat(xmlCtx, section, 'distanceFactorPerLevelWhenDeviceDestroyed')
    return res


def _readLoaderDesperado(xmlCtx, section, subsectionName):
    res, xmlCtx, section = _readSkillBasics(xmlCtx, section, subsectionName)
    res['vehicleHealthFraction'] = _xml.readFraction(xmlCtx, section, 'vehicleHealthFraction')
    res['gunReloadTimeFactor'] = _xml.readPositiveFloat(xmlCtx, section, 'gunReloadTimeFactor')
    return res


def _readBadRoadsKing(xmlCtx, section, subsectionName):
    res, xmlCtx, section = _readSkillBasics(xmlCtx, section, subsectionName)
    res['softGroundResistanceFactorPerLevel'] = _xml.readPositiveFloat(xmlCtx, section, 'softGroundResistanceFactorPerLevel')
    res['mediumGroundResistanceFactorPerLevel'] = _xml.readPositiveFloat(xmlCtx, section, 'mediumGroundResistanceFactorPerLevel')
    return res


_g_skillConfigReaders = {'repair': _readRole,
 'fireFighting': _readRole,
 'camouflage': _readRole,
 'brotherhood': partial(_readSkillInt, 'crewLevelIncrease', 0),
 'commander_tutor': partial(_readSkillNonNegFloat, 'xpBonusFactorPerLevel'),
 'commander_universalist': partial(_readSkillFraction, 'efficiency'),
 'commander_expert': partial(_readSkillNonNegFloat, 'delay'),
 'commander_sixthSense': partial(_readSkillNonNegFloat, 'delay'),
 'commander_eagleEye': _readCommanderEagleEye,
 'driver_tidyPerson': partial(_readSkillNonNegFloat, 'fireStartingChanceFactor'),
 'driver_smoothDriving': partial(_readSkillNonNegFloat, 'shotDispersionFactorPerLevel'),
 'driver_virtuoso': partial(_readSkillNonNegFloat, 'rotationSpeedFactorPerLevel'),
 'driver_badRoadsKing': _readBadRoadsKing,
 'driver_rammingMaster': partial(_readSkillNonNegFloat, 'rammingBonusFactorPerLevel'),
 'gunner_smoothTurret': partial(_readSkillNonNegFloat, 'shotDispersionFactorPerLevel'),
 'gunner_sniper': partial(_readSkillFraction, 'deviceChanceToHitBoost'),
 'gunner_rancorous': _readGunnerRancorous,
 'gunner_gunsmith': _readGunnerGunsmith,
 'loader_pedant': partial(_readSkillNonNegFloat, 'ammoBayHealthFactor'),
 'loader_desperado': _readLoaderDesperado,
 'loader_intuition': partial(_readSkillFraction, 'chance'),
 'radioman_finder': partial(_readSkillNonNegFloat, 'visionRadiusFactorPerLevel'),
 'radioman_inventor': partial(_readSkillNonNegFloat, 'radioDistanceFactorPerLevel'),
 'radioman_lastEffort': partial(_readSkillInt, 'duration', 1),
 'radioman_retransmitter': partial(_readSkillNonNegFloat, 'distanceFactorPerLevel')}
_g_skillsConfig = None
_g_nationsConfig = [ None for x in xrange(len(nations.NAMES)) ]

def _makeLevelXpCosts():
    costs = [0] * (MAX_SKILL_LEVEL + 1)
    prevCost = 0
    for level in xrange(1, len(costs)):
        prevCost += int(round(_LEVELUP_K1 * pow(_LEVELUP_K2, float(level - 1) / MAX_SKILL_LEVEL)))
        costs[level] = prevCost

    return costs


_g_levelXpCosts = _makeLevelXpCosts()

def _calcFirstSkillXpCost():
    result = 0
    for level in range(MAX_SKILL_LEVEL):
        result += TankmanDescr.levelUpXpCost(level, 1)

    return result


_g_totalFirstSkillXpCost = _calcFirstSkillXpCost()
