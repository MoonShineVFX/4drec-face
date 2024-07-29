# execute by hython, reduce mesh and export to glb
from optparse import OptionParser


if __name__ == "__main__":
    # parse args
    parser = OptionParser()
    parser.add_option("-i", "--input-4dframe", help="input 4dframe file")
    parser.add_option("-o", "--output-glb", help="output glb file")
    options, args = parser.parse_args()

    # load file
    input_path = options.input_4dframe.replace("\\", "/")
    output_path = options.output_glb.replace("\\", "/")

    print("Convert 4dh files from: " + input_path + " to: " + output_path)
    hou.hipFile.load("G:/app/4drec-face/tools/load_4df.hip")

    # set input path
    hou.node("/obj/geo1/load_4df_header").parm("file_path").set(input_path)

    # set output path
    rop_glb = hou.node("/obj/geo1/rop_glb")
    rop_glb.parm("file").set(output_path)
    rop_glb.render()
