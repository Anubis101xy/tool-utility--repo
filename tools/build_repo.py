#!/usr/bin/env python3
"""Tool Utility Repo builder.

Put new add-on zips in  incoming/  and run:   python tools/build_repo.py
It files each zip under zips/<addon id>/, refreshes zips/addons.xml + addons.xml.md5 (what Kodi checks for
updates), rebuilds the repository add-on zip and the index.html front page. Then upload everything to GitHub."""
import hashlib
import os
import re
import shutil
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZIPS = os.path.join(ROOT, "zips")
INCOMING = os.path.join(ROOT, "incoming")
REPO_SRC = os.path.join(ROOT, "repository.toolutility")
KEEP = 2  # versions of each add-on to keep (the newest + one to go back to)


def vkey(v):
    return [int(x) if x.isdigit() else x for x in re.split(r"[.\-~+]", v)]


def read_addon_xml(zpath):
    with zipfile.ZipFile(zpath) as z:
        names = [n for n in z.namelist() if n.count("/") == 1 and n.endswith("/addon.xml")]
        if not names:
            raise ValueError("%s has no <addon id>/addon.xml inside" % os.path.basename(zpath))
        data = z.read(names[0]).decode("utf-8")
        root = ET.fromstring(data)
        return root.get("id"), root.get("version"), data, names[0].split("/")[0], z


def copy_art(zpath, aid):
    """Kodi shows the icon/fanart from zips/<id>/<path in the add-on>."""
    with zipfile.ZipFile(zpath) as z:
        root = ET.fromstring(z.read(aid + "/addon.xml").decode("utf-8"))
        paths = {"icon.png", "fanart.jpg"}
        for el in root.iter():
            if el.tag in ("icon", "fanart", "banner", "clearlogo", "poster", "screenshot") and (el.text or "").strip():
                paths.add(el.text.strip())
        for p in paths:
            try:
                data = z.read("%s/%s" % (aid, p))
            except KeyError:
                continue
            out = os.path.join(ZIPS, aid, p)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out, "wb") as f:
                f.write(data)


def file_zip(zpath):
    aid, ver, _, folder, _ = read_addon_xml(zpath)
    if folder != aid:
        raise ValueError("%s: folder inside the zip is '%s' but the add-on id is '%s'" % (zpath, folder, aid))
    dest_dir = os.path.join(ZIPS, aid)
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, "%s-%s.zip" % (aid, ver))
    shutil.copyfile(zpath, dest)
    copy_art(dest, aid)
    old = sorted([f for f in os.listdir(dest_dir) if f.startswith(aid + "-") and f.endswith(".zip")],
                 key=lambda f: vkey(f[len(aid) + 1:-4]), reverse=True)
    for f in old[KEEP:]:
        os.remove(os.path.join(dest_dir, f))
    print("  %-34s %s" % (aid, ver))
    return aid, ver


def build_repo_addon():
    """Zip the repository add-on itself (repository.toolutility/) into zips/ and the front page."""
    root = ET.parse(os.path.join(REPO_SRC, "addon.xml")).getroot()
    aid, ver = root.get("id"), root.get("version")
    tmp = os.path.join(ROOT, "%s-%s.zip" % (aid, ver))
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for base, _, files in os.walk(REPO_SRC):
            for fn in sorted(files):
                full = os.path.join(base, fn)
                z.write(full, os.path.join(aid, os.path.relpath(full, REPO_SRC)))
    for f in os.listdir(ROOT):  # only the current repository zip on the front page
        if f.startswith(aid + "-") and f.endswith(".zip") and f != os.path.basename(tmp):
            os.remove(os.path.join(ROOT, f))
    file_zip(tmp)
    return os.path.basename(tmp)


def build_index(repo_zip):
    addons = []
    for aid in sorted(os.listdir(ZIPS)):
        d = os.path.join(ZIPS, aid)
        if os.path.isdir(d):
            vs = sorted([f for f in os.listdir(d) if f.endswith(".zip")], key=lambda f: vkey(f[len(aid) + 1:-4]), reverse=True)
            if vs:
                addons.append((aid, vs[0]))
    rows = "\n".join('    <li><a href="zips/%s/%s">%s</a></li>' % (a, z, z) for a, z in addons if a != "repository.toolutility")
    html = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tool Utility Repo</title>
<style>
body{font-family:system-ui,sans-serif;max-width:640px;margin:40px auto;padding:0 16px;background:#14161a;color:#e8e8e8;line-height:1.5}
a{color:#7cc4ff}h1{margin-bottom:4px}code{background:#262a31;padding:2px 6px;border-radius:4px}
.box{background:#1d2026;border-radius:10px;padding:14px 18px;margin:18px 0}
</style></head>
<body>
<h1>Tool Utility Repo</h1>
<p>Kodi repository for TorUtilityBox and friends.</p>
<div class="box"><b>Install the repository</b>
<ol>
<li>Kodi: Settings &gt; File manager &gt; Add source &gt; <code>https://anubis101xy.github.io/tool-utility--repo/</code></li>
<li>Add-ons &gt; Install from zip file &gt; pick that source &gt; <a href="%s">%s</a></li>
<li>Add-ons &gt; Install from repository &gt; Tool Utility Repo</li>
</ol></div>
<p><a href="%s">%s</a></p>
<p>Add-on zips (for reference - install them from the repository so they update by themselves):</p>
<ul>
%s
</ul>
</body>
</html>
""" % (repo_zip, repo_zip, repo_zip, repo_zip, rows)
    with open(os.path.join(ROOT, "index.html"), "w") as f:
        f.write(html)


def build_addons_xml():
    parts = []
    for aid in sorted(os.listdir(ZIPS)):
        d = os.path.join(ZIPS, aid)
        if not os.path.isdir(d):
            continue
        vs = sorted([f for f in os.listdir(d) if f.endswith(".zip")], key=lambda f: vkey(f[len(aid) + 1:-4]), reverse=True)
        if not vs:
            continue
        _, _, data, _, _ = read_addon_xml(os.path.join(d, vs[0]))
        data = re.sub(r"^\s*<\?xml[^>]*\?>\s*", "", data).strip()
        parts.append(data)
    xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n' + "\n\n".join(parts) + "\n</addons>\n"
    ET.fromstring(xml.encode("utf-8"))  # check it's valid before saving
    with open(os.path.join(ZIPS, "addons.xml"), "w", encoding="utf-8") as f:
        f.write(xml)
    with open(os.path.join(ZIPS, "addons.xml.md5"), "w") as f:
        f.write(hashlib.md5(xml.encode("utf-8")).hexdigest())


def main():
    os.makedirs(ZIPS, exist_ok=True)
    os.makedirs(INCOMING, exist_ok=True)
    new = sorted(f for f in os.listdir(INCOMING) if f.endswith(".zip"))
    print("Adding:" if new else "No new zips in incoming/ - just rebuilding the lists")
    for f in new:
        try:
            file_zip(os.path.join(INCOMING, f))
            os.remove(os.path.join(INCOMING, f))
        except Exception as e:
            print("  SKIPPED %s: %s" % (f, e))
    repo_zip = build_repo_addon()
    build_addons_xml()
    build_index(repo_zip)
    open(os.path.join(ROOT, ".nojekyll"), "w").close()
    print("Done - upload the whole folder to GitHub (zips/, index.html, %s, .nojekyll)." % repo_zip)


if __name__ == "__main__":
    sys.exit(main())
