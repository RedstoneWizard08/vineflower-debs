#!/usr/bin/env python3

import os
import re
import glob
import json
import semver
import requests
import subprocess

base_dir = os.path.join(os.curdir, "src")
vineflower_dir = os.path.join(base_dir, "usr", "share", "vineflower")
items = glob.glob(os.path.join(vineflower_dir, "*.jar"))

for item in items:
    print(f"Cleaning old jar: {item}")

    os.remove(item)

def get_latest_version():
    releases = requests.get("https://api.github.com/repos/Vineflower/vineflower/releases").text
    releases = json.loads(releases)
    versions = []

    for release in releases:
        versions.append({
            "id": release["id"],
            "tag": semver.Version.parse(release["tag_name"]),
            "raw_tag": release["tag_name"],
        })

    return max(versions, key=lambda x: x["tag"])

def get_jar_asset(version_id):
    assets = requests.get(f"https://api.github.com/repos/Vineflower/vineflower/releases/{version_id}/assets").text
    assets = json.loads(assets)

    for asset in assets:
        if asset["name"].endswith(".jar"):
            return asset

    return None

version = get_latest_version()
version_tag = version["raw_tag"]
version_id = version["id"]

print(f"Found latest Vineflower version: v{version_tag} ({version_id})")

asset = get_jar_asset(version_id)
asset_name = asset["name"]
asset_url = asset["browser_download_url"]
asset_path = os.path.join(vineflower_dir, asset_name)

print(f"Found JAR asset: {asset_name}")
print("Downloading JAR...")

with open(asset_path, "wb") as out:
    res = requests.get(asset_url).content
    out.write(res)

print("Written JAR bytes to file.")

target_path = os.path.join(vineflower_dir, "vineflower.jar")
os.symlink(asset_name, target_path)

print(f"Created symlink to {target_path}.")

control_path = os.path.join(base_dir, "DEBIAN", "control")
regex = re.compile(r"Version\:.*$", re.M)

with open(control_path, "r") as ctrl:
    ctrl_data = ctrl.read()

ctrl_data = regex.sub(f"Version: {version_tag}", ctrl_data)

with open(control_path, "w") as ctrl:
    ctrl.write(ctrl_data)

print(f"Updated control file.")
print("Building package...")

subprocess.run(
    ["dpkg-deb", "--build", base_dir, f"vineflower-{version_tag}.deb"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    cwd=os.curdir
)

print("Package built!")
