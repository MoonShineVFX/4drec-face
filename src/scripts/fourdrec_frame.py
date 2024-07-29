from common.fourdrec_frame import FourdrecFrame

file_path = (
    r"G:/submit/0722_wen/shots/shot_4/jobs/resolve_3/output/frame/0000.4dframe"
)
frame = FourdrecFrame(file_path)

texture_output = r"C:\Users\eli.hung\Desktop\texture.jpg"
frame.export_texture(texture_output)
