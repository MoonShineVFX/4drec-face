from common.bg_remover import detect
from PIL import Image
from pathlib import Path
import numpy as np


if __name__ == '__main__':
    image_folder = Path(r'G:\resource\bgremoval\test_in')
    output_folder = rf'G:\resource\bgremoval\test_out\\'
    image_path_list = [str(path) for path in image_folder.glob('*.jpg')]

    print('Prepare images')
    images = [(image_path, np.array(Image.open(image_path).convert('RGB'))) for image_path in image_path_list]
    h, w, c = images[0][1].shape

    print('Predict')
    model = detect.load_model()
    detect.generate_mask(model, images, w, h, output_folder)
