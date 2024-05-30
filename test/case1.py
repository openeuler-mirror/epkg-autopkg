import sys

from pypi_json import PyPIJSON


src_urls = []
all_depends = set()
def get_src_url_and_depends(client, pkg):
    success = False
    try_num = 0
    while not success:
        try:
            requests_metadata = client.get_metadata(pkg)
            print(pkg)
            success = True
        except Exception as e:
            print(str(e))
            success = False
            try_num += 1
            print(pkg, 'tried times: ', str(try_num))
            if try_num > 20:
                print(pkg, 'has tried 20 times.')
                break
    try:
        src_url = requests_metadata.info['project_urls']['Source']
        src_urls.append(src_url)
    except Exception as e:
        print(str(e))
        print(pkg, ' has no source')
    try:
        depends = requests_metadata.info['requires_dist']
        print("depends===============>>>", depends)
        for dep in depends:
            dep_pkg0 = dep.split()[0].strip()
            dep_pkg1 = dep_pkg0.split("<")[0].strip()
            dep_pkg2 = dep_pkg1.split("<")[0].strip()
            dep_pkg3 = dep_pkg2.split("<")[0].strip()
            dep_pkg4 = dep_pkg3.split("<")[0].strip()
            dep_pkg5 = dep_pkg4.split("<")[0].strip()
            if dep_pkg5 not in all_depends:
                get_src_url_and_depends(client, dep_pkg5)
                all_depends.add(dep_pkg5)
            print("all_depends: ", all_depends)
    except Exception as e:
        print(str(e))

sys.setrecursionlimit(1000000)
top_pkgs = ["requests", "numpy"]
i = 0
with PyPIJSON() as client:
    for top_pkg in top_pkgs:
        get_src_url_and_depends(client, top_pkg)

print(src_urls)

