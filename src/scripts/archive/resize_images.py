from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import cv2


input_path = r'C:\Users\eli.hung\Desktop\bridge_curse_2-jiachi_2\texture'
output_path = input_path + '_2k'
size = 2048


def resize_image(input_image_path, output_image_path):
    image = cv2.imread(input_image_path)
    resized_image = cv2.resize(image, (size, size))
    cv2.imwrite(
        output_image_path,
        resized_image,
        [int(cv2.IMWRITE_JPEG_QUALITY), 75]
    )
    return output_image_path


if __name__ == '__main__':
    Path(output_path).mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor() as executor:
        future_list = []
        for jpg_path in Path(input_path).glob('*.jpg'):
            output_file = Path(output_path) / (jpg_path.stem.split('_')[-1] + '.jpg')
            future = executor.submit(
                resize_image, str(jpg_path), str(output_file)
            )
            future_list.append(future)

        count = 1
        for future in as_completed(future_list):
            output_filename = future.result()
            print(f'({count}/{len(future_list)}) {output_filename}')
            count += 1
