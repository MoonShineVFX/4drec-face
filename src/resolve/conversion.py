# execute by hython
from optparse import OptionParser
import os

os.environ["DRACO_PATH"] = "G:/app"
from pathlib import Path


if __name__ == "__main__":
    # parse args
    parser = OptionParser()
    parser.add_option("-f", "--frame", help="frame number")
    parser.add_option("-i", "--input", help="output folder")
    options, args = parser.parse_args()

    # load file
    output_path = options.input.replace("\\", "/")
    print("Convert 4dh files in " + output_path + " at frame " + options.frame)
    hou.hipFile.load("G:/app/4drec-face/tools/load_4dh.hip")

    # ensure transform fix not on
    transform_node = hou.node("/obj/geo1/transform_180")
    transform_node.bypass(0)

    # get file path
    parm_file_path = hou.node("/obj/geo1/load_4dh_header").parm("file_path")
    parm_file_path.set(output_path + "/geo/$F4.4dh")

    hou.session.set_time_range_from_4d_files()
    hou.setFrame(int(options.frame))

    # conversion
    # gltf
    rop_gltf_mini = hou.node("/obj/geo1/rop_gltf_mini")
    rop_gltf_hires = hou.node("/obj/geo1/rop_gltf_hires")
    rop_gltf_mini.render()
    rop_gltf_hires.render()

    # 4dr
    hou.session.draco_convert_drc(source_glb_path=None, is_hd=False, log=None)
    hou.session.draco_convert_drc(source_glb_path=None, is_hd=True, log=None)

    load_path = parm_file_path.eval()
    root_path = Path(load_path).parent.parent

    hou.session.hou_log(f"Resize texture 2k {root_path}")
    print("Resize texture 2k", root_path)
    hou.session.resize_texture(root_path, options.frame, is_hd=False)

    hou.session.hou_log("Resize texture 4k")
    print("Resize texture 4k")
    hou.session.resize_texture(root_path, options.frame, is_hd=True)
