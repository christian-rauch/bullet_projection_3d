#!/usr/bin/env python3
import pybullet as p
import math
import numpy as np
import pybullet_data
from skimage import io

p.connect(p.GUI)
p.setAdditionalSearchPath(pybullet_data.getDataPath())
plane = p.loadURDF("plane100.urdf")
cube = p.loadURDF("cube.urdf", [0, 0, 0.5])

w = 640
h = 480
fov = 40
distance=2
yaw=0
pitch=-40
roll=0
target=[0, 0, 1]
near = 0.01
far = 10000

p.resetDebugVisualizerCamera(cameraDistance=distance, cameraYaw=yaw, cameraPitch=pitch, cameraTargetPosition=target)
vm = p.computeViewMatrixFromYawPitchRoll(distance=distance, yaw=yaw, pitch=pitch, roll=roll, upAxisIndex=2, cameraTargetPosition=target)
pm = p.computeProjectionMatrixFOV(fov = fov, aspect = w / h, nearVal = near, farVal = far)


def getRayFromTo(mouseX, mouseY):
  width, height, viewMat, projMat, cameraUp, camForward, horizon, vertical, _, _, dist, camTarget = p.getDebugVisualizerCamera(
  )
  camPos = [
      camTarget[0] - dist * camForward[0], camTarget[1] - dist * camForward[1],
      camTarget[2] - dist * camForward[2]
  ]
  farPlane = far
  rayForward = [(camTarget[0] - camPos[0]), (camTarget[1] - camPos[1]), (camTarget[2] - camPos[2])]
  lenFwd = math.sqrt(rayForward[0] * rayForward[0] + rayForward[1] * rayForward[1] +
                     rayForward[2] * rayForward[2])
  invLen = farPlane * 1. / lenFwd
  rayForward = [invLen * rayForward[0], invLen * rayForward[1], invLen * rayForward[2]]
  rayFrom = camPos
  oneOverWidth = float(1) / float(width)
  oneOverHeight = float(1) / float(height)

  dHor = [horizon[0] * oneOverWidth, horizon[1] * oneOverWidth, horizon[2] * oneOverWidth]
  dVer = [vertical[0] * oneOverHeight, vertical[1] * oneOverHeight, vertical[2] * oneOverHeight]
  rayToCenter = [
      rayFrom[0] + rayForward[0], rayFrom[1] + rayForward[1], rayFrom[2] + rayForward[2]
  ]
  ortho = [
      -0.5 * horizon[0] + 0.5 * vertical[0] + float(mouseX) * dHor[0] - float(mouseY) * dVer[0],
      -0.5 * horizon[1] + 0.5 * vertical[1] + float(mouseX) * dHor[1] - float(mouseY) * dVer[1],
      -0.5 * horizon[2] + 0.5 * vertical[2] + float(mouseX) * dHor[2] - float(mouseY) * dVer[2]
  ]

  rayTo = [
      rayFrom[0] + rayForward[0] + ortho[0], rayFrom[1] + rayForward[1] + ortho[1],
      rayFrom[2] + rayForward[2] + ortho[2]
  ]
  lenOrtho = math.sqrt(ortho[0] * ortho[0] + ortho[1] * ortho[1] + ortho[2] * ortho[2])
  alpha = math.atan(lenOrtho / farPlane)
  return rayFrom, rayTo, alpha


width, height, viewMat, projMat, cameraUp, camForward, horizon, vertical, _, _, dist, camTarget = p.getDebugVisualizerCamera(
)
camPos = [
    camTarget[0] - dist * camForward[0], camTarget[1] - dist * camForward[1],
    camTarget[2] - dist * camForward[2]
]
farPlane = far
rayForward = [(camTarget[0] - camPos[0]), (camTarget[1] - camPos[1]), (camTarget[2] - camPos[2])]
lenFwd = math.sqrt(rayForward[0] * rayForward[0] + rayForward[1] * rayForward[1] +
                   rayForward[2] * rayForward[2])
oneOverWidth = float(1) / float(width)
oneOverHeight = float(1) / float(height)
dHor = [horizon[0] * oneOverWidth, horizon[1] * oneOverWidth, horizon[2] * oneOverWidth]
dVer = [vertical[0] * oneOverHeight, vertical[1] * oneOverHeight, vertical[2] * oneOverHeight]

lendHor = math.sqrt(dHor[0] * dHor[0] + dHor[1] * dHor[1] + dHor[2] * dHor[2])
lendVer = math.sqrt(dVer[0] * dVer[0] + dVer[1] * dVer[1] + dVer[2] * dVer[2])

cornersX = [0, width, width, 0]
cornersY = [0, 0, height, height]
corners3D = []

imgW = int(width / 10)
imgH = int(height / 10)

img = p.getCameraImage(imgW, imgH, vm, pm, renderer=p.ER_BULLET_HARDWARE_OPENGL)
rgbBuffer = np.reshape(img[2], (imgH, imgW, 4))

# render at full resolution
img_full = p.getCameraImage(w, h, vm, pm, renderer=p.ER_BULLET_HARDWARE_OPENGL)
np.save("depth", img_full[3])
dmin = np.min(img_full[3])
dmax = np.max(img_full[3])
dnorm = (img_full[3]-dmin) / (dmax-dmin)
io.imsave("depth_norm.png", (dnorm*255).astype(np.uint8))
io.imsave("colour.png", img_full[2])
depth = far * near / (far - (far - near) * img_full[3])
print("depth range", np.min(depth), np.max(depth))
io.imsave("depth_mm.png", (depth*1000).astype(np.uint16))

# convert field-of-view to focal length
fovs = fov * np.array([w / h, 1])
fs = (0.5 * np.array([w, h])) / np.tan(np.deg2rad(fovs)/2)

uv = np.dstack(np.meshgrid(range(w), range(h), indexing='xy'))
uv_list = uv.reshape((-1,2))

xy = (uv_list - np.array([w/2, h/2])) * depth.reshape((-1,1)) / fs
xyz = np.concatenate((xy, depth.reshape((-1,1))), axis=1)
np.savetxt("points_m.xyz", xyz)

# NOTE: this depth buffer's reshaping does not match the [w, h] convention for
# OpenGL depth buffers.  See getCameraImageTest.py for an OpenGL depth buffer
depthBuffer = np.reshape(img[3], [imgH, imgW])
print("rgbBuffer.shape=", rgbBuffer.shape)
print("depthBuffer.shape=", depthBuffer.shape)

#disable rendering temporary makes adding objects faster
p.configureDebugVisualizer(p.COV_ENABLE_RENDERING, 0)
p.configureDebugVisualizer(p.COV_ENABLE_GUI, 0)
p.configureDebugVisualizer(p.COV_ENABLE_TINY_RENDERER, 0)
visualShapeId = p.createVisualShape(shapeType=p.GEOM_SPHERE, rgbaColor=[1, 1, 1, 1], radius=0.03)
collisionShapeId = -1  #p.createCollisionShape(shapeType=p.GEOM_MESH, fileName="duck_vhacd.obj", collisionFramePosition=shift,meshScale=meshScale)

for i in range(4):
  w = cornersX[i]
  h = cornersY[i]
  rayFrom, rayTo, _ = getRayFromTo(w, h)
  rf = np.array(rayFrom)
  rt = np.array(rayTo)
  vec = rt - rf
  l = np.sqrt(np.dot(vec, vec))
  newTo = (0.01 / l) * vec + rf
  #print("len vec=",np.sqrt(np.dot(vec,vec)))

  p.addUserDebugLine(rayFrom, newTo, [1, 0, 0])
  corners3D.append(newTo)
count = 0

stepX = 5
stepY = 5
points = []
for w in range(0, imgW, stepX):
  for h in range(0, imgH, stepY):
    count += 1
    if ((count % 100) == 0):
      print(count, "out of ", imgW * imgH / (stepX * stepY))
    rayFrom, rayTo, alpha = getRayFromTo(w * (width / imgW), h * (height / imgH))
    rf = np.array(rayFrom)
    rt = np.array(rayTo)
    vec = rt - rf
    l = np.sqrt(np.dot(vec, vec))
    depthImg = float(depthBuffer[h, w])
    depth = far * near / (far - (far - near) * depthImg)
    depth /= math.cos(alpha)
    newTo = (depth / l) * vec + rf
    points.append(newTo)
    p.addUserDebugLine(rayFrom, newTo, [1, 0, 0])
    mb = p.createMultiBody(baseMass=0,
                           baseCollisionShapeIndex=collisionShapeId,
                           baseVisualShapeIndex=visualShapeId,
                           basePosition=newTo,
                           useMaximalCoordinates=True)
    color = rgbBuffer[h, w]
    color = [color[0] / 255., color[1] / 255., color[2] / 255., 1]
    p.changeVisualShape(mb, -1, rgbaColor=color)
p.addUserDebugLine(corners3D[0], corners3D[1], [1, 0, 0])
p.addUserDebugLine(corners3D[1], corners3D[2], [1, 0, 0])
p.addUserDebugLine(corners3D[2], corners3D[3], [1, 0, 0])
p.addUserDebugLine(corners3D[3], corners3D[0], [1, 0, 0])
p.configureDebugVisualizer(p.COV_ENABLE_RENDERING, 1)
np.savetxt("points.xyz", points)
print("ready\n")
#p.removeBody(plane)
#p.removeBody(cube)
while (1):
  p.setGravity(0, 0, -10)
