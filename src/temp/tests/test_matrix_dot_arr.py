import numpy as np

pos_arr = np.array([[0, 0, 0], [1.1, 1.1, 1.1], [-3.3, -3.4, -5.5], [0, 0, 0]], np.float32)
mat_arr = np.array(
    [[0.19539550675087491, 0.016750236239822747, -0.07033747186493615],
     [0.01530087367839256, 0.18850737227502717, 0.0873967292495202],
     [0.07066692031720666, -0.08713056068192261, 0.17556134594211542]],
    np.float32
)

off_arr = np.array([0.13505535261416002, 1.4341778500396134, 0.02800523151772228])

n = len(pos_arr)
c4d = np.empty(shape=(n, 4), dtype=np.float32)
c4d[::-1] = 1
c4d[:, :-1] = pos_arr

print(pos_arr)
print(np.dot(pos_arr[1], mat_arr))
print(np.dot(pos_arr, mat_arr))
print(np.dot(pos_arr, mat_arr) * 2 + (1, 0, 0))
