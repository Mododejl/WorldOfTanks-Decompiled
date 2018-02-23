# Embedded file name: scripts/client/VehicleEffects.py
from collections import namedtuple
import BigWorld
import Math
import Pixie
from Math import Vector3, Matrix
import math
from constants import VEHICLE_HIT_EFFECT
from debug_utils import LOG_CURRENT_EXCEPTION, LOG_CODEPOINT_WARNING
import helpers
from items import _xml
from helpers.EffectMaterialCalculation import calcEffectMaterialIndex
import material_kinds

class TankComponentNames():
    CHASSIS = 'chassis'
    HULL = 'hull'
    TURRET = 'turret'
    GUN = 'gun'


class DetailedEngineState(object):
    rpm = property(lambda self: self.__rpm)
    gearNum = property(lambda self: self.__gearNum)

    def __init__(self):
        self.__rpm = 0.0
        self.__gearNum = 0

    def refresh(self, vehicleSpeed, vehicleTypeDescriptor):
        speedRange = vehicleTypeDescriptor.physics['speedLimits'][0] + vehicleTypeDescriptor.physics['speedLimits'][1]
        speedRangePerGear = speedRange / 3
        gearNum = math.ceil(math.floor(math.fabs(vehicleSpeed) * 50) / 50 / speedRangePerGear)
        self.__rpm = math.fabs(1 + (vehicleSpeed - gearNum * speedRangePerGear) / speedRangePerGear)
        if gearNum == 0:
            self.__rpm = 0
        self.__gearNum = gearNum


class VehicleTrailEffects():
    _DRAW_ORDER_IDX = 102
    enabled = property(lambda self: self.__enabled)

    def __init__(self, vehicle):
        self.__vehicle = vehicle
        chassisModel = self.__vehicle.appearance.modelsDesc['chassis']['model']
        topRightCarryingPoint = self.__vehicle.typeDescriptor.chassis['topRightCarryingPoint']
        self.__enabled = True
        self.__trailParticleNodes = []
        self.__trailParticles = {}
        mMidLeft = Math.Matrix()
        mMidLeft.setTranslate((-topRightCarryingPoint[0], 0, 0))
        mMidRight = Math.Matrix()
        mMidRight.setTranslate((topRightCarryingPoint[0], 0, 0))
        self.__trailParticleNodes = [chassisModel.node('', mMidLeft), chassisModel.node('', mMidRight)]
        i = 0
        for nodeName in ('HP_Track_LFront', 'HP_Track_RFront', 'HP_Track_LRear', 'HP_Track_RRear'):
            node = None
            try:
                identity = Math.Matrix()
                identity.setIdentity()
                node = chassisModel.node(nodeName, identity)
            except:
                matr = mMidLeft if i % 2 == 0 else mMidRight
                node = chassisModel.node('', Math.Matrix(matr))

            self.__trailParticleNodes.append(node)

        identity = Math.Matrix()
        identity.setIdentity()
        self.__centerNode = chassisModel.node('', identity)
        self.__trailParticlesDelayBeforeShow = BigWorld.time() + 4.0
        return

    def destroy(self):
        self.stopEffects()
        self.__trailParticleNodes = None
        self.__trailParticles = None
        self.__centerNode = None
        self.__vehicle = None
        return

    def getTrackCenterNode(self, trackIdx):
        return self.__trailParticleNodes[trackIdx]

    def enable(self, isEnabled):
        if self.__enabled and not isEnabled:
            self.stopEffects()
        self.__enabled = isEnabled

    def stopEffects(self):
        for node in self.__trailParticles.iterkeys():
            for trail in self.__trailParticles[node]:
                node.detach(trail[0])

        self.__trailParticles = {}

    def update(self):
        vehicle = self.__vehicle
        vehicleAppearance = self.__vehicle.appearance
        if not self.__enabled:
            return
        elif vehicle.typeDescriptor.chassis['effects'] is None:
            self.__enabled = False
            return
        else:
            time = BigWorld.time()
            if time < self.__trailParticlesDelayBeforeShow:
                return
            movementInfo = Math.Vector4(vehicleAppearance.fashion.movementInfo.value)
            vehicleSpeedRel = vehicle.filter.speedInfo.value[2] / vehicle.typeDescriptor.physics['speedLimits'][0]
            tooSlow = abs(vehicleSpeedRel) < 0.1
            waterHeight = None if not vehicleAppearance.isInWater else vehicleAppearance.waterHeight
            effectIndexes = self.__getEffectIndexesUnderVehicle(vehicleAppearance)
            self.__updateNodePosition(self.__centerNode, vehicle.position, waterHeight)
            centerEffectIdx = effectIndexes[2]
            if not tooSlow and not vehicleAppearance.isUnderwater:
                self.__createTrailParticlesIfNeeded(self.__centerNode, 0, 'dust', centerEffectIdx, VehicleTrailEffects._DRAW_ORDER_IDX, True)
            centerNodeEffects = self.__trailParticles.get(self.__centerNode)
            if centerNodeEffects is not None:
                for nodeEffect in centerNodeEffects:
                    stopParticles = nodeEffect[1] != centerEffectIdx or vehicleAppearance.isUnderwater or tooSlow
                    self.__updateNodeEffect(nodeEffect, self.__centerNode, centerNodeEffects, vehicleSpeedRel, stopParticles)

            for iTrack in xrange(2):
                trackSpeedRel = movementInfo[iTrack + 1]
                trackSpeedRel = 0.0 if trackSpeedRel == 0 else abs(vehicleSpeedRel) * trackSpeedRel / abs(trackSpeedRel)
                activeCornerNode = self.__trailParticleNodes[2 + iTrack + (0 if trackSpeedRel <= 0 else 2)]
                inactiveCornerNode = self.__trailParticleNodes[2 + iTrack + (0 if trackSpeedRel > 0 else 2)]
                self.__updateNodePosition(activeCornerNode, vehicle.position, waterHeight)
                self.__updateNodePosition(inactiveCornerNode, vehicle.position, waterHeight)
                currEffectIndex = effectIndexes[iTrack]
                if not tooSlow and not vehicleAppearance.isUnderwater:
                    self.__createTrailParticlesIfNeeded(activeCornerNode, iTrack, 'mud', currEffectIndex, VehicleTrailEffects._DRAW_ORDER_IDX + iTrack, True)
                    self.__createTrailParticlesIfNeeded(inactiveCornerNode, iTrack, 'mud', currEffectIndex, VehicleTrailEffects._DRAW_ORDER_IDX + iTrack, False)
                for node in (activeCornerNode, inactiveCornerNode):
                    nodeEffects = self.__trailParticles.get(node)
                    if nodeEffects is not None:
                        for nodeEffect in nodeEffects:
                            createdForActiveNode = nodeEffect[5]
                            stopParticlesOnDirChange = node == activeCornerNode and not createdForActiveNode or node == inactiveCornerNode and createdForActiveNode
                            stopParticles = nodeEffect[1] != currEffectIndex or stopParticlesOnDirChange or vehicleAppearance.isUnderwater or tooSlow
                            self.__updateNodeEffect(nodeEffect, node, nodeEffects, trackSpeedRel, stopParticles)

            return

    def __getEffectIndexesUnderVehicle(self, vehicleAppearance):
        correctedMatKinds = [ (material_kinds.WATER_MATERIAL_KIND if vehicleAppearance.isInWater else matKind) for matKind in vehicleAppearance.terrainMatKind ]
        return map(calcEffectMaterialIndex, correctedMatKinds)

    def __updateNodePosition(self, node, vehiclePos, waterHeight):
        if waterHeight is not None:
            toCenterShift = vehiclePos.y - (Math.Matrix(node).translation.y - node.local.translation.y)
            node.local.translation = Math.Vector3(0, waterHeight + toCenterShift, 0)
        else:
            node.local.translation = Math.Vector3(0, 0, 0)
        return

    def __createTrailParticlesIfNeeded(self, node, iTrack, effectGroup, effectIndex, drawOrder, isActiveNode):
        if effectIndex is None:
            return
        else:
            effectDesc = self.__vehicle.typeDescriptor.chassis['effects'].get(effectGroup)
            if effectDesc is None:
                return
            effectName = effectDesc[0].get(effectIndex)
            if effectName is None or effectName == 'none' or effectName == 'None':
                return
            if isinstance(effectName, list):
                effectIdx = iTrack
                effectIdx += 0 if isActiveNode else 2
                effectName = effectName[effectIdx]
            nodeEffects = self.__trailParticles.get(node)
            if nodeEffects is None:
                nodeEffects = []
                self.__trailParticles[node] = nodeEffects
            else:
                for nodeEffect in nodeEffects:
                    createdForActiveNode = nodeEffect[5]
                    if nodeEffect[1] == effectIndex and createdForActiveNode == isActiveNode:
                        return

            pixie = Pixie.create(effectName)
            pixie.drawOrder = drawOrder
            node.attach(pixie)
            basicRates = []
            for i in xrange(pixie.nSystems()):
                try:
                    source = pixie.system(i).action(1)
                    basicRates.append(source.rate)
                    source.rate = source.rate * 0.001
                except:
                    basicRates.append(-1.0)
                    source = pixie.system(i).action(16)
                    source.MultRate(0.01)

            nodeEffects.append([pixie,
             effectIndex,
             0,
             0,
             basicRates,
             isActiveNode])
            return

    def __updateNodeEffect(self, nodeEffect, node, nodeEffects, relSpeed, stopParticles):
        relEmissionRate = 0.0 if stopParticles else abs(relSpeed)
        basicEmissionRates = nodeEffect[4]
        pixie = nodeEffect[0]
        for i in xrange(pixie.nSystems()):
            if basicEmissionRates[i] < 0:
                source = pixie.system(i).action(16)
                source.MultRate(relEmissionRate)
            else:
                source = pixie.system(i).action(1)
                source.rate = relEmissionRate * basicEmissionRates[i]

        effectInactive = relEmissionRate < 0.0001
        if effectInactive:
            time = BigWorld.time()
            timeOfStop = nodeEffect[3]
            if timeOfStop == 0:
                nodeEffect[3] = time
            elif time - timeOfStop > 5.0 or material_kinds.EFFECT_MATERIALS[nodeEffect[1]] == 'water':
                pixie = nodeEffect[0]
                node.detach(pixie)
                nodeEffects.remove(nodeEffect)
        else:
            nodeEffect[3] = 0


class RangeTable(object):

    def __init__(self, keys, values):
        self.keys = keys
        self.values = values

    def lookup(self, point, defaultValue = None):
        foundValue = defaultValue
        for leftBound, value in zip(self.keys, self.values):
            if point < leftBound:
                break
            foundValue = value

        return foundValue


class ExhaustEffectsDescriptor(object):

    def __init__(self, dataSection):
        try:
            self.tables = []
            states = ('start', 'idle', 'mainLoad', 'highLoad')
            for state in states:
                effectSection = dataSection[state]
                rpm = effectSection.readString('rpm', '0')
                rpm = map(float, rpm.split())
                effects = effectSection.readString('effects', '')
                effects = effects.split()
                if not effects:
                    effects.append('')
                raise len(rpm) == len(effects) or AssertionError('rpm size differs from effects')
                self.tables.append(RangeTable(rpm, effects))

        except Exception as exp:
            raise Exception, 'error reading exhaust effects %s, got %s' % (dataSection.name, exp)


class VehicleExhaustDescriptor(object):

    def __init__(self, dataSection, exhaustEffectsDescriptors, xmlCtx):
        self.nodes = _xml.readNonEmptyString(xmlCtx, dataSection, 'exhaust/nodes').split()
        defaultPixieName = _xml.readNonEmptyString(xmlCtx, dataSection, 'exhaust/pixie')
        dieselPixieName = defaultPixieName
        gasolinePixieName = defaultPixieName
        exhaustTagsSection = dataSection['exhaust/tags']
        if exhaustTagsSection is not None:
            dieselPixieName = exhaustTagsSection.readString('diesel', dieselPixieName)
            gasolinePixieName = exhaustTagsSection.readString('gasoline', gasolinePixieName)
        tmpDefault = exhaustEffectsDescriptors['default']
        self.diesel = exhaustEffectsDescriptors.get(dieselPixieName, tmpDefault)
        self.gasoline = exhaustEffectsDescriptors.get(gasolinePixieName, tmpDefault)
        return

    def prerequisites(self):
        prereqs = set()
        allTables = list(self.diesel.tables)
        allTables += self.gasoline.tables
        for table in allTables:
            for effectName in table.values:
                prereqs.add(effectName)

        return prereqs


class ExhaustEffectsCache():
    activeEffect = property(lambda self: self.__activeEffect)
    maxDrawOrder = property(lambda self: self.__maxDrawOrder)
    uniqueEffects = property(lambda self: self.__uniqueEffects)

    def __init__(self, exhaustEffectsDescriptor, drawOrder, uniqueEffects = None):
        if uniqueEffects is None:
            self.__uniqueEffects = {}
        else:
            self.__uniqueEffects = {name:effect.clone() for name, effect in uniqueEffects.iteritems()}
        self.__tables = []
        self.__maxDrawOrder = drawOrder - 1
        for rangeTable in exhaustEffectsDescriptor.tables:
            effectsValues = []
            for name in rangeTable.values:
                effect = self.__uniqueEffects.get(name)
                if effect is None:
                    effect = Pixie.create(name)
                    self.__maxDrawOrder += 1
                    effect.drawOrder = self.__maxDrawOrder
                    self.__uniqueEffects[name] = effect
                effectsValues.append(effect)

            self.__tables.append(RangeTable(rangeTable.keys, effectsValues))

        if self.__maxDrawOrder < drawOrder:
            self.__maxDrawOrder = drawOrder
        self.__activeEffect = None
        for effect in self.__uniqueEffects.itervalues():
            enablePixie(effect, False)

        return

    def clone(self, exhaustEffectsDescriptor, drawOrder):
        return ExhaustEffectsCache(exhaustEffectsDescriptor, drawOrder, self.__uniqueEffects)

    def changeActiveEffect(self, engineLoad, engineRPM):
        prevEffect = self.__activeEffect
        self.__activeEffect = self.__tables[engineLoad].lookup(engineRPM, prevEffect)
        return prevEffect != self.__activeEffect


class VehicleExhaustEffects():
    enabled = property(lambda self: self.__enabled)

    def __init__(self, vehicleTypeDescriptor):
        self.__enabled = True
        self.__exhaust = []
        isObserver = 'observer' in vehicleTypeDescriptor.type.tags
        if isObserver:
            self.__enabled = False
            return
        else:
            vehicleExhaustDescriptor = vehicleTypeDescriptor.hull['exhaust']
            engineTags = vehicleTypeDescriptor.engine['tags']
            exhaustDesc = vehicleExhaustDescriptor.diesel if 'diesel' in engineTags else vehicleExhaustDescriptor.gasoline
            effectsCache = None
            for idx, nodeName in enumerate(vehicleExhaustDescriptor.nodes):
                if effectsCache is None:
                    effectsCache = ExhaustEffectsCache(exhaustDesc, 50 + idx)
                else:
                    effectsCache = effectsCache.clone(exhaustDesc, effectsCache.maxDrawOrder + 1)
                self.__exhaust.append([None, effectsCache])

            return

    def destroy(self):
        for node, pixieCache in self.__exhaust:
            if pixieCache.activeEffect is not None:
                enablePixie(pixieCache.activeEffect, False)
                pixieCache.activeEffect.clear()

        self.__exhaust = []
        return

    def enable(self, isEnabled):
        for node, pixieCache in self.__exhaust:
            activeEffect = pixieCache.activeEffect
            if activeEffect is not None:
                enablePixie(activeEffect, isEnabled)

        self.__enabled = isEnabled
        return

    def attach(self, hullModel, vehicleExhaustDescriptor):
        for nodeName, nodeAndCache in zip(vehicleExhaustDescriptor.nodes, self.__exhaust):
            node = hullModel.node(nodeName)
            nodeAndCache[0] = node
            for effect in nodeAndCache[1].uniqueEffects.itervalues():
                node.attach(effect)

    def detach(self):
        for node, pixieCache in self.__exhaust:
            if node is not None:
                for effect in pixieCache.uniqueEffects.itervalues():
                    node.detach(effect)

        return

    def changeExhaust(self, engineMode, rpm):
        if not self.__enabled:
            return
        else:
            for node, pixieCache in self.__exhaust:
                prevEffect = pixieCache.activeEffect
                shouldReattach = pixieCache.changeActiveEffect(engineMode, rpm)
                if shouldReattach and node is not None:
                    if prevEffect is not None:
                        enablePixie(prevEffect, False)
                    if pixieCache.activeEffect is not None:
                        enablePixie(pixieCache.activeEffect, True)

            return


def enablePixie(pixie, turnOn):
    multiplier = 1.0 if turnOn else 0.0
    for i in xrange(pixie.nSystems()):
        try:
            source = pixie.system(i).action(16)
            source.MultRate(multiplier)
        except:
            LOG_CURRENT_EXCEPTION()


class DamageFromShotDecoder(object):
    ShotPoint = namedtuple('ShotPoint', ('componentName', 'matrix', 'hitEffectGroup'))
    __hitEffectCodeToEffectGroup = ('armorRicochet', 'armorResisted', 'armorHit', 'armorHit', 'armorCriticalHit')

    @staticmethod
    def hasDamaged(vehicleHitEffectCode):
        return vehicleHitEffectCode >= VEHICLE_HIT_EFFECT.ARMOR_PIERCED

    @staticmethod
    def decodeHitPoints(encodedPoints, vehicleDescr):
        resultPoints = []
        maxHitEffectCode = None
        pointsCount = len(encodedPoints)
        for currPointIndex, encodedPoint in enumerate(encodedPoints):
            compName, hitEffectCode, startPoint, endPoint = DamageFromShotDecoder.decodeSegment(encodedPoint, vehicleDescr)
            if startPoint == endPoint:
                continue
            maxHitEffectCode = max(hitEffectCode, maxHitEffectCode)
            hitTester = getattr(vehicleDescr, compName)['hitTester']
            hitTestRes = hitTester.localHitTest(startPoint, endPoint)
            if not hitTestRes:
                width, height, depth = (hitTester.bbox[1] - hitTester.bbox[0]) / 256
                directions = [Math.Vector3(0.0, -height, 0.0),
                 Math.Vector3(0.0, height, 0.0),
                 Math.Vector3(-width, 0.0, 0.0),
                 Math.Vector3(width, 0.0, 0.0),
                 Math.Vector3(0.0, 0.0, -depth),
                 Math.Vector3(0.0, 0.0, depth)]
                for direction in directions:
                    hitTestRes = hitTester.localHitTest(startPoint + direction, endPoint + direction)
                    if hitTestRes is not None:
                        break

                if hitTestRes is None:
                    continue
            minDist = hitTestRes[0]
            for hitTestRes in hitTestRes:
                dist = hitTestRes[0]
                if dist < minDist:
                    minDist = dist

            hitDir = endPoint - startPoint
            hitDir.normalise()
            rot = Matrix()
            rot.setRotateYPR((hitDir.yaw, hitDir.pitch, 0.0))
            matrix = Matrix()
            matrix.setTranslate(startPoint + hitDir * minDist)
            matrix.preMultiply(rot)
            effectGroup = DamageFromShotDecoder.__hitEffectCodeToEffectGroup[hitEffectCode]
            if hitEffectCode == VEHICLE_HIT_EFFECT.RICOCHET and currPointIndex < pointsCount - 1:
                effectGroup = 'armorBasicRicochet'
            resultPoints.append(DamageFromShotDecoder.ShotPoint(compName, matrix, effectGroup))

        return (maxHitEffectCode, resultPoints)

    @staticmethod
    def decodeSegment(segment, vehicleDescr):
        compIdx = segment >> 8 & 255
        if compIdx == 0:
            componentName = TankComponentNames.CHASSIS
            bbox = vehicleDescr.chassis['hitTester'].bbox
        elif compIdx == 1:
            componentName = TankComponentNames.HULL
            bbox = vehicleDescr.hull['hitTester'].bbox
        elif compIdx == 2:
            componentName = TankComponentNames.TURRET
            bbox = vehicleDescr.turret['hitTester'].bbox
        elif compIdx == 3:
            componentName = TankComponentNames.GUN
            bbox = vehicleDescr.gun['hitTester'].bbox
        else:
            LOG_CODEPOINT_WARNING(compIdx)
        min = Math.Vector3(bbox[0])
        delta = bbox[1] - min
        segStart = min + Math.Vector3(*(k * (segment >> shift & 255) / 255.0 for k, shift in zip(delta, (16, 24, 32))))
        segEnd = min + Math.Vector3(*(k * (segment >> shift & 255) / 255.0 for k, shift in zip(delta, (40, 48, 56))))
        offset = (segEnd - segStart) * 0.01
        segStart -= offset
        segEnd += offset
        return (componentName,
         int(segment & 255),
         segStart,
         segEnd)
