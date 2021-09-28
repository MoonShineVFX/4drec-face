import subprocess

cmd = subprocess.Popen(r'C:\Users\eli.hung\PycharmProjects\4drec-face\src\resolve.bat --frame 196 --resolve_stage resolve --yaml_path "G:/jobs/4cdd8d/87be91/3d9a44/job.yml"')

cmd.communicate()[0]

return_code = cmd.wait()
print(f'return code is : {return_code}')
