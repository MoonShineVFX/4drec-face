import lz4framed
import numpy as np
from common.fourd_frame import FourdFrameManager
import lz4.frame
import os


fourd_frame = FourdFrameManager.load(r'G:\submit\demo0318\shots\shot_9\jobs\resolve_1\output\003000.4df')
print(fourd_frame.header)


with open(r'C:\Users\eli.hung\Downloads\testgeo.bin', 'rb') as f:
    data = lz4framed.decompress(f.read())
    arr = np.frombuffer(data, dtype=np.float32)

print(arr)


data = b'testhi' + os.urandom(1024)

with open(r'C:\Users\eli.hung\WebstormProjects\web-gl-pftest\test.lz4', 'wb') as f:
    f.write(lz4.frame.compress(data))

print(len(b'testhi'.decode('utf8')))