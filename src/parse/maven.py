# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; specifically version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat (c) 2023 and Avocado contributors

import os
import sys
import re
import yaml
import requests
from lxml import etree
from src.parse.basic_parse import BasicParse
from src.utils.cmd_util import check_makefile_exist
from src.config.yamls import yaml_path
from src.log import logger


class MavenParse(BasicParse):
    def __init__(self, source, version=""):
        super().__init__(source)
        if source.group == "" and source.path == "":
            logger.error("lack of groupId input")
            sys.exit(6)
        self.build_system = "maven"
        self.maven_path = ""
        with open(os.path.join(yaml_path, f"{self.build_system}.yaml"), "r") as f:
            yaml_text = f.read()
        self.metadata = yaml.safe_load(yaml_text)
        self.version = version if version != "" else source.version
        self.group = source.group
        self.source = source
        self.plugin_map = {}
        self.var_map = {}
        self.profile_map = {}
        self.package_names = set()
        self.ns = {"ns": "http://maven.apache.org/POM/4.0.0"}
        self.spec_map = {'@groovyGroupId@': 'org.codehaus.groovy'}
        self.__url = f"https://repo1.maven.org/maven2/{self.group}/{self.pacakge_name}/{self.version}/" \
                     f"{self.pacakge_name}-{self.version}.pom"

    def parse_api_info(self):
        # 指定 groupId, artifactId 和 version

        # 构造请求的 URL 和参数
        url = "https://search.maven.org/solrsearch/select"
        params = {
            'q': f'g:"{self.group}" AND a:"{self.pacakge_name}" AND v:"{self.version}"',
            'rows': '20',
            'wt': 'json'
        }

        # 发送 GET 请求
        response = requests.get(url, params=params)

        # 检查响应状态码是否为200
        if response.status_code == 200:
            # 解析 JSON 数据
            data = response.json()
            # 遍历并打印结果
            for doc in data['response']['docs']:
                print(f"GroupId: {doc['g']}, ArtifactId: {doc['a']}, Version: {doc['v']}")
        else:
            print("Error:", response.status_code)

    def check_compilation_file(self):
        if "autopkg" in self.metadata and "buildSystemFiles" in self.metadata["autopkg"]:
            build_system_file = self.metadata["autopkg"]["buildSystemFiles"]
            if build_system_file not in self.source.files:
                self.maven_path = check_makefile_exist(self.source.files, file_name="pom.xml")
                return self.maven_path != ""
            return True
        return False

    def check_compilation(self):
        result = self.check_compilation_file()
        if result:
            self.parse_pom_xml()
        return result

    def remove_plugin_config(self, name):
        self.metadata.setdefault("removePlugin", []).append(name)

    def disable_module_config(self, name):
        self.metadata.setdefault("disableModule", []).append(name)

    def parse_dependencies(self, dependencies, dependency_text_set):
        for dependency in dependencies.findall('./ns:dependency', self.ns):
            tag = self.parse_single_dependency_or_plugin(dependency)
            # if self.package_names not in tag:
            dependency_text_set.add(tag)
        return dependency_text_set

    def parse_single_dependency_or_plugin(self, dependency):
        def get_text_info(tag):
            return dependency.find(f'./ns:{tag}', self.ns).text if dependency.find(
                f'./ns:{tag}', self.ns) is not None else None
        group_id = self.replace_vars(get_text_info('groupId'))
        artifact_id = self.replace_vars(get_text_info('artifactId'))
        return self.get_tag(group_id, artifact_id)

    def parse_pom_xml(self):
        pom_path = os.path.join(self.source.path, "pom.xml")
        if not os.path.exists(pom_path):
            return
        tree = etree.parse(pom_path)
        root = tree.getroot()
        default_package = root.find("./ns:groupId", self.ns)
        if default_package is not None:
            pkg_text = self.replace_vars(default_package)
            self.var_map['groupId'] = pkg_text
            self.var_map['project.groupId'] = pkg_text
            self.var_map['project.parent.groupId'] = pkg_text
            self.spec_map['@project.groupId@'] = pkg_text

            parent_artifact = root.find('./ns:parent/ns:artifactId', self.ns)
            art_text = self.replace_vars(parent_artifact.text)
            self.var_map['artifactId'] = art_text
            self.spec_map['@project.artifactId@'] = art_text

            parent_package_name = self.get_tag(pkg_text, art_text)
            self.package_names.add(parent_package_name)
            self.default_dependency.add(parent_package_name)
            self.default_dependency.add(parent_package_name + ':pom:')
        self.var_map = self.parse_properities(tree, self.ns)

        default_dependencies = root.find('./ns:dependencies', self.ns)
        if default_dependencies is not None:
            self.default_dependency = self.parse_dependencies(default_dependencies, self.default_dependency)
        another_default_dependencies = root.find('./ns:dependencyManagement/ns:dependencies', self.ns)
        if another_default_dependencies is not None:
            self.default_dependency = self.parse_dependencies(another_default_dependencies, self.default_dependency)

        # plugins first, as profiles may depend on plugins
        plugins = tree.find('./ns:build/ns:plugins', self.ns)
        if plugins is not None:
            self.parse_plugins(plugins, self.plugin_map)
        another_plugins = tree.find('./ns:build/ns:pluginManagement/ns:plugins', self.ns)
        if another_plugins is not None:
            self.parse_plugins(another_plugins, self.plugin_map)

        profiles = tree.find('./ns:profiles', self.ns)
        if profiles is not None:
            self.parse_profiles(profiles, self.profile_map)
        ## at least, fill all the plugins to the default_dependency
        for plugin_id in self.plugin_map:
            self.default_dependency.add(plugin_id)
            plugin_dependencies = self.plugin_map[plugin_id]
            for plugin_dependency in plugin_dependencies:
                self.default_dependency.add(plugin_dependency)
        self.parse_all_other_deps(tree, self.ns)
        self.metadata["pomInfo"] = {
            "plugin_map": self.plugin_map,
            "var_map": self.var_map,
            "profile_map": self.profile_map,
            "package_names": list(self.package_names),
        }

    def parse_properities(self, tree, ns):
        for mvn_property in tree.findall('ns:properties', ns):
            children = mvn_property.getchildren()
            for child in children:
                tag = child.tag
                if isinstance(tag, str):
                    tag = tag.replace('{http://maven.apache.org/POM/4.0.0}', '')
                    text = self.replace_vars(child.text)
                    self.var_map[tag] = text
        return self.var_map

    def parse_all_other_deps(self, tree, ns):
        for mvn_executable in tree.findall('.//ns:executable', ns):
            text = mvn_executable.text
            if isinstance(text, str):
                text = text.replace('{http://maven.apache.org/POM/4.0.0}', '')
                self.default_dependency.add(text)

    def replace_vars(self, given_str):
        if given_str is None:
            return ''
        if '${' not in given_str and '@' not in given_str:
            return given_str
        return_str = given_str
        if '${' in return_str:
            matches = re.findall(r"\$\{(.*?)\}", return_str)
            if len(matches) > 0:
                for match in matches:
                    if match in self.var_map:
                        return_str = return_str.replace('${' + match + '}', self.var_map[match])
        if '@' in return_str:
            for key in self.spec_map:
                if key in return_str:
                    return_str = return_str.replace(key, self.spec_map[key])
        return return_str

    @staticmethod
    def get_tag(group_id, artifact_id):
        if group_id is None:
            return artifact_id
        return str(group_id) + ':' + str(artifact_id)

    def parse_plugins(self, plugins, given_map):
        plugin_set = plugins.findall('./ns:plugin', self.ns)
        for plugin in plugin_set:
            tag = self.parse_single_dependency_or_plugin(plugin)
            dependencies = plugin.find('./ns:dependencies', self.ns)
            dependency_text_set = set()
            if dependencies is not None:
                dependency_text_set = self.parse_dependencies(dependencies, dependency_text_set)
            if tag not in given_map:
                given_map[tag] = dependency_text_set
            else:
                given_map[tag] = given_map[tag] | dependency_text_set
        return given_map

    def parse_profiles(self, profiles, given_map):
        for profile in profiles.findall('./ns:profile', self.ns):
            profile_id_ins = profile.find('./ns:id', self.ns)
            if profile_id_ins is not None:
                profile_id = profile.find('./ns:id', self.ns).text
            else:
                profile_id = ''
            dependencies = profile.find('./ns:dependencies', self.ns)
            dependency_text_set = set()
            if dependencies is not None:
                dependency_text_set = self.parse_dependencies(dependencies, dependency_text_set)
            # parse the plugins
            inner_plugin = profile.find('./ns:build/ns:plugins', self.ns)
            if inner_plugin is not None:
                inner_plugin_map = self.parse_plugins(inner_plugin, {})
                for plugin_id in inner_plugin_map:
                    dependency_text_set.add(plugin_id)
                    plugin_dependencies = inner_plugin_map[plugin_id]
                    dependency_text_set = dependency_text_set | plugin_dependencies
                    # load the plugin map again
                    if plugin_id in self.plugin_map:
                        dependency_text_set = dependency_text_set | self.plugin_map[plugin_id]
            if profile_id not in given_map:
                given_map[profile_id] = dependency_text_set
            else:
                given_map[profile_id] = given_map[profile_id] | dependency_text_set
        return given_map
