# Python bytecode 2.7 (decompiled from Python 2.7)
# Embedded file name: scripts/client/FlockExotic.py
import math
import random
from functools import partial
import BigWorld
import Math
import FlockManager
from Flock import FlockLike
from helpers.CallbackDelayer import CallbackDelayer
from debug_utils import LOG_CURRENT_EXCEPTION, LOG_ERROR

class FlockExotic(BigWorld.Entity, FlockLike, CallbackDelayer):

    def __init__(self):
        BigWorld.Entity.__init__(self)
        FlockLike.__init__(self)
        CallbackDelayer.__init__(self)
        self.flightAngleMin = math.radians(self.flightAngleMin)
        self.flightAngleMax = math.radians(self.flightAngleMax)
        if self.flightAngleMin < 0:
            self.flightAngleMin += math.ceil(abs(self.flightAngleMin) / (math.pi * 2)) * math.pi * 2
        elif self.flightAngleMin > math.pi * 2:
            self.flightAngleMin -= math.floor(self.flightAngleMin / (math.pi * 2)) * math.pi * 2
        self.__isTriggered = False
        self.__models = []

    def prerequisites(self):
        return self._getModelsToLoad()

    def __createMotor(self, positionStart, positionEnd, speed, flightTime):
        time1 = BigWorld.time()
        time2 = time1 + self.accelerationTime
        time3 = time2 + flightTime
        initSpeed = speed * random.uniform(self.initSpeedRandom[0], self.initSpeedRandom[1])
        controlPoint1 = (positionStart, initSpeed, time1)
        controlPoint2 = (positionStart + (initSpeed + speed) / 2.0, speed, time2)
        motor = BigWorld.PyTimedWarplaneMotor(controlPoint1, controlPoint2, 0.0)
        motor.addTrajectoryPoint(positionEnd, speed, time3)
        return motor

    def onEnterWorld(self, prereqs):
        self.__loadModels(prereqs)
        FlockManager.getManager().addFlock(self.position, self.triggerRadius, self.explosionRadius, self.respawnTime, self)

    def onLeaveWorld(self):
        self.__removeModels()
        self.__models = []
        self.models = []
        FlockLike.destroy(self)
        CallbackDelayer.destroy(self)

    def name(self):
        pass

    def __loadModels(self, prereqs):
        try:
            for modelId in prereqs.keys():
                if modelId in prereqs.failedIDs:
                    LOG_ERROR('Failed to load flock model: %s' % modelId)
                    continue
                model = prereqs[modelId]
                model.moveAttachments = True
                model.visible = False
                self.__models.append(model)
                animSpeed = random.uniform(self.animSpeedMin, self.animSpeedMax)
                model.actionScale = animSpeed

        except Exception:
            LOG_CURRENT_EXCEPTION()

    def __removeModels(self):
        for model in self.models:
            self.__removeModel(model)

        self.models = []

    def __removeModel(self, model):
        self._delSound()
        model.motors = ()
        model.position = self.position
        model.visible = False
        self.delModel(model)

    def __getRandomSpawnPos(self):
        randHeight = random.uniform(0, self.spawnHeight)
        randAngle = random.uniform(0, 2 * math.pi)
        randRadius = random.uniform(0, self.spawnRadius)
        return Math.Vector3(randRadius * math.cos(randAngle), randHeight, randRadius * math.sin(randAngle)) + self.position

    def __getRandomTargetPos(self, startPos):
        randHeight = random.uniform(0, self.flightHeight)
        arc = self.flightAngleMax - self.flightAngleMin
        if self.flightAngleMax < self.flightAngleMin:
            arc = 2 * math.pi - abs(arc)
        randAngle = random.uniform(self.flightAngleMin, self.flightAngleMin + arc)
        direction = Math.Vector3(self.flightRadius * math.cos(randAngle), self.flightOffsetFromOrigin + randHeight, self.flightRadius * math.sin(randAngle)) + self.position
        direction = direction - startPos
        direction.normalise()
        direction *= self.speed * self.lifeTime
        return startPos + direction

    def onTrigger(self):
        index = 0
        for model in self.__models:
            model.visible = True
            self.addModel(model)
            model.action('FlockAnimAction')()
            model.position = self.__getRandomSpawnPos()
            targetPos = self.__getRandomTargetPos(model.position)
            direction = targetPos - model.position
            dirLength = direction.length
            speed = self.speed * random.uniform(self.speedRandom[0], self.speedRandom[1])
            if dirLength > 0.0:
                velocity = direction * speed / dirLength
                velocityLen = velocity.length
                if velocityLen > 0.0:
                    flightTime = dirLength / velocityLen
                    motor = self.__createMotor(model.position, targetPos, velocity, flightTime)
                    model.addMotor(motor)
                    self.delayCallback(flightTime, partial(self.__removeModel, model))
                    if index == 0:
                        self._addSound(model, self.flightSound)
                    index += 1
