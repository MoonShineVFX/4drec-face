import subprocess

cmd = subprocess.Popen(r'G:\app\4drec-face\src\resolve.bat --frame 0 --resolve_stage initialize --yaml_path "G:/jobs/9e9802/6b6242/e2d153/job.yml"')

cmd.communicate()[0]

return_code = cmd.wait()
print(f'return code is : {return_code}')
