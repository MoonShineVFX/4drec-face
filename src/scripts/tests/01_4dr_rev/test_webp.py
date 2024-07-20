from PIL import Image


JPEG_PATH = r"C:\Users\eli.hung\Desktop\4dr_test\0000.jpg"

image = Image.open(JPEG_PATH)
image.save(JPEG_PATH.replace(".jpg", "_l100.webp"), "WEBP", quality=100)
image.save(JPEG_PATH.replace(".jpg", "_l90.webp"), "WEBP", quality=90)
