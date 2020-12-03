import os
import shutil
import time
import zipfile

if __name__ == "__main__":

    if os.path.isdir("build"):
        shutil.rmtree("build")
    if os.path.isdir("dist"):
        shutil.rmtree("dist")
    if os.path.isdir("magicgen"):
        shutil.rmtree("magicgen")
    os.system("pyinstaller magicgen.py --onefile --window")
    # ugly for permissions
    #time.sleep(3)
    os.rename("dist", "magicgen")
    os.system("pyinstaller magicgenGUI.pyw --onefile")
    #time.sleep(3)
    shutil.copy("dist/magicgenGUI.exe", "magicgen/magicgenGUI.exe")

    shutil.copy("LICENSE", "magicgen/LICENSE")
    shutil.copy("docs.md", "magicgen/docs.md")
    shutil.copy("readme.md", "magicgen/readme.md")
    shutil.copy("changelog.txt", "magicgen/changelog.txt")

    shutil.copy("baseu.csv", "magicgen/baseu.csv")
    shutil.copy("effects_weapons.csv", "magicgen/effects_weapons.csv")
    shutil.copy("fort_leader_types_by_nation.csv", "magicgen/fort_leader_types_by_nation.csv")
    shutil.copy("spells.csv", "magicgen/spells.csv")
    shutil.copy("weapons.csv", "magicgen/weapons.csv")
    shutil.copytree("data", "magicgen/data")
    shutil.copytree("unitdescr", "magicgen/unitdescr")

    zipf = zipfile.ZipFile("magicgen.zip", "w", zipfile.ZIP_DEFLATED)
    for root, dirs, files in os.walk("magicgen"):
        for file in files:
            zipf.write(os.path.join(root, file))

    zipf.close()
