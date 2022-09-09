ffmpeg -r 30 -start_number 0 -i .\texture\bridge_curse_2-jiachi_2_%04d.jpg -i audio.wav -vf scale=2048:-1 -pix_fmt yuv420p -movflags +faststart texture.mp4
