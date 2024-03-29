import errno
import os
import numpy as np
import torch
from torchvision import transforms
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from common.bg_remover import data_loader, u2net


MODEL_PATH = r'G:\resource\bgremoval\u2net_human_seg.pth'


def load_model():
    net = u2net.U2NET(3, 1)

    if not torch.cuda.is_available():
        raise ValueError('No cuda available')

    try:
        net.load_state_dict(torch.load(MODEL_PATH))
        net.to(torch.device("cuda"))
    except FileNotFoundError:
        raise FileNotFoundError(
            errno.ENOENT, os.strerror(errno.ENOENT), MODEL_PATH
        )

    net.eval()

    return net


def norm_pred(d):
    ma = torch.max(d)
    mi = torch.min(d)
    dn = (d - mi) / (ma - mi)

    return dn


def preprocess(payload):
    path, image = payload
    label_3 = np.zeros(image.shape)
    label = np.zeros(label_3.shape[0:2])

    if 3 == len(label_3.shape):
        label = label_3[:, :, 0]
    elif 2 == len(label_3.shape):
        label = label_3

    if 3 == len(image.shape) and 2 == len(label.shape):
        label = label[:, :, np.newaxis]
    elif 2 == len(image.shape) and 2 == len(label.shape):
        image = image[:, :, np.newaxis]
        label = label[:, :, np.newaxis]

    transform = transforms.Compose(
        [data_loader.RescaleT(320), data_loader.ToTensorLab(flag=0)]
    )
    sample = transform({"imidx": np.array([0]), "image": image, "label": label})

    return path, sample


def generate_mask(images, width, height, output_path):
    net = load_model()

    print('Preprocess')
    samples = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_list = []
        for image in images:
            future = executor.submit(
                preprocess, image
            )
            future_list.append(future)

        count = 1
        for future in as_completed(future_list):
            samples.append(future.result())
            print(f'Preprocess {count}/{len(future_list)}')
            count += 1

    result = []

    print('Detect mask')
    with torch.no_grad():
        if not torch.cuda.is_available():
            raise ValueError('Cuda not avaiable')

        count = len(samples)
        idx = 1
        for sample_item in samples:
            path, sample = sample_item
            print(f'Detect {idx}/{count}')
            inputs_test = torch.cuda.FloatTensor(
                sample["image"].unsqueeze(0).cuda().float()
            )

            d1, d2, d3, d4, d5, d6, d7 = net(inputs_test)

            pred = d1[:, 0, :, :]
            predict = norm_pred(pred)

            predict = predict.squeeze()
            predict_np = predict.cpu().detach().numpy()
            result.append((path, predict_np))

            del d1, d2, d3, d4, d5, d6, d7, pred, predict, predict_np, inputs_test, sample
            idx += 1

    del net

    print('Save')
    count = 1
    for path, predict_np in result:
        save_path = save_mask(path, predict_np, width, height, output_path)
        print(f'{count}/{len(future_list)} {save_path}')
        count += 1

    print('Release VRAM')
    torch.cuda.empty_cache()


def save_mask(path, predict_np, width, height, output_path):
    from PIL import Image
    output_image = Image.fromarray(predict_np * 255)
    output_image = output_image.resize(
        (width, height), Image.LANCZOS
    ).convert("RGB")
    filename = Path(path).stem
    save_path = rf'{output_path}\{filename}.png'
    output_image.save(save_path)

    del predict_np, output_image
    return save_path
