# This script should NOT BE EXECUTED DIRECTLY
# use "python setup.py build" instead (this is how you correctly invoke cx_freeze)

import os
import shutil
import zipfile
import time
import re
import cx_Freeze

if os.path.isdir("build"):
    shutil.rmtree("build")
	


# Apparently importing the actual script that is built is bad practice and may cause issues
ver = None
with open("magicgen.py", "r") as f:
	for line in f:
		m = re.match('ver = "(.*)"', line)
		if m is not None:
			ver = m.groups()[0]
			print(f"Found version: {ver}")
			break
			
if ver is None:
	raise Exception("Failed to find version")

build_exe_options = {"include_msvcr":False, "excludes":["distutils", "test"]}

cx_Freeze.setup(name="MagicGen", version=ver, description="MagicGen: A procedural spellbook generator for Dominions 5", options={"build_exe":build_exe_options}, executables=[cx_Freeze.Executable("magicgen.py"), cx_Freeze.Executable("magicgengui.pyw", base="Win32GUI")])

# Permissions.
time.sleep(5)

buildfilename = os.listdir("build")[0]
os.rename(f"build/{buildfilename}", f"build/magicgen-{ver}")

# cx_Freeze tries to include a bunch of dlls that Windows users may not have permissions to distribute
# but should be present on any recent system (and available through the MS VC redistributables if not)
# therefore clear them from the distribution

for root, dirs, files in os.walk(f"build/magicgen-{ver}"):
	for file in files:
		if file.startswith("api-ms") or file in ["ucrtbase.dll", "vcruntime140.dll"]:
			print(f"Strip file {file} from output")
			os.unlink(os.path.join(f"build/magicgen-{ver}", file))
		elif "api-ms" in file:
			print(file)

shutil.copy("LICENSE", f"build/magicgen-{ver}/LICENSE")
shutil.copy("docs.md", f"build/magicgen-{ver}/docs.md")
shutil.copy("readme.md", f"build/magicgen-{ver}/readme.md")
shutil.copy("changelog.txt", f"build/magicgen-{ver}/changelog.txt")

shutil.copy("data/BaseU.csv", f"build/magicgen-{ver}/baseu.csv")
shutil.copy("data/effects_weapons.csv", f"build/magicgen-{ver}/effects_weapons.csv")
shutil.copy("data/VanillaLeaderMaps/fort_leader_types_by_nation.csv", f"build/magicgen-{ver}/fort_leader_types_by_nation.csv")
shutil.copy("data/spells.csv", f"build/magicgen-{ver}/spells.csv")
shutil.copy("data/weapons.csv", f"build/magicgen-{ver}/weapons.csv")
shutil.copy("data/nations.csv", f"build/magicgen-{ver}/nations.csv")
shutil.copytree("data", f"build/magicgen-{ver}/data")
shutil.copytree("unitdescr", f"build/magicgen-{ver}/unitdescr")
os.mkdir(f"build/magicgen-{ver}/output")

# change working dir so the /build folder doesn't end up in the zip
os.chdir("build")

zipf = zipfile.ZipFile(f"magicgen-{ver}.zip", "w", zipfile.ZIP_DEFLATED)
for root, dirs, files in os.walk(f"magicgen-{ver}"):
    for file in files:
        zipf.write(os.path.join(root, file))

zipf.close()