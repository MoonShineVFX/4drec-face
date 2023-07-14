# execute by hython
from optparse import OptionParser
import os
os.environ['DRACO_PATH'] = 'G:/app'

if __name__ == '__main__':
    # parse args
    parser = OptionParser()
    parser.add_option('-f', '--frame', help='frame number')
    parser.add_option('-i', '--input', help='4dh folder')  # G:/postprocess/export/0712fam-shot_4/geo
    options, args = parser.parse_args()

    # load file
    input_path = options.input.replace('\\', '/')
    print('Convert 4dh files in ' + input_path + ' at frame ' + options.frame)
    hou.hipFile.load('G:/app/4drec-face/tools/load_4dh.hip')

    parm_file_path = hou.node('/obj/geo1/load_4dh_header').parm('file_path')
    parm_file_path.set(input_path + '/$F4.4dh')

    hou.session.set_time_range_from_4d_files()
    hou.setFrame(int(options.frame))

    # conversion
    rop_gltf_mini = hou.node('/obj/geo1/rop_gltf_mini')
    rop_gltf_hires = hou.node('/obj/geo1/rop_gltf_hires')
    rop_gltf_mini.render()
    rop_gltf_hires.render()
    hou.session.draco_convert_glb_mini()
