import os
import shutil
import zipfile

if __name__ == "__main__":

    if os.path.isdir("build"):
        shutil.rmtree("build")
    if os.path.isdir("dist"):
        shutil.rmtree("dist")
    if os.path.isdir("magicgen"):
        shutil.rmtree("magicgen")
        
    os.mkdir("magicgen")
        
    os.system("python -m nuitka --follow-imports magicgen.py")
    
    shutil.copy("magicgen.exe", "magicgen/magicgen.exe")

    os.system("python -m nuitka --follow-imports --windows-disable-console magicgengui.pyw")
    shutil.copy("magicgenGUI.exe", "magicgen/magicgenGUI.exe")
    shutil.copy("python38.dll", "magicgen/python38.dll")

    shutil.copy("LICENSE", "magicgen/LICENSE")
    shutil.copy("docs.md", "magicgen/docs.md")
    shutil.copy("readme.md", "magicgen/readme.md")
    shutil.copy("changelog.txt", "magicgen/changelog.txt")

    shutil.copy("baseu.csv", "magicgen/baseu.csv")
    shutil.copy("effects_weapons.csv", "magicgen/effects_weapons.csv")
    shutil.copy("fort_leader_types_by_nation.csv", "magicgen/fort_leader_types_by_nation.csv")
    shutil.copy("spells.csv", "magicgen/spells.csv")
    shutil.copy("weapons.csv", "magicgen/weapons.csv")
    shutil.copy("nations.csv", "magicgen/nations.csv")
    shutil.copytree("data", "magicgen/data")
    shutil.copytree("unitdescr", "magicgen/unitdescr")
    os.mkdir("magicgen/output")

    zipf = zipfile.ZipFile("magicgen.zip", "w", zipfile.ZIP_DEFLATED)
    for root, dirs, files in os.walk("magicgen"):
        for file in files:
            zipf.write(os.path.join(root, file))

    zipf.close()
