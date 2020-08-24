import time
import logging

import spatialreasoner as sr


logging.basicConfig(level=logging.DEBUG)

ccl = sr.ccl.ClozureCL()
model = sr.spatialreasoner.SpatialReasoner(ccl)
time.sleep(1)

# Query for response
problem = [
    'the circle is on the right of the square',
    'the triangle is on the left of the circle',
    'the cross is in front of the triangle',
    'the line is in front of the circle',
    'the cross is on the left of the line',
]

problem = [
    'the cross is in front of the circle',
    'the triangle is in front of the circle',
    'the cross is in front of the triangle',
]

res = model.query(problem)

time.sleep(2)
model.terminate()

print('Response:', res)
