import os, glob, shutil
path = r'C:\Users\17193\Desktop\发票整理工具\发票\output'
for f in glob.glob(os.path.join(path, '*.*')):
    if os.path.isfile(f):
        os.remove(f)
for d in os.listdir(path):
    full_path = os.path.join(path, d)
    if os.path.isdir(full_path):
        shutil.rmtree(full_path)
print('已清空output文件夹')
