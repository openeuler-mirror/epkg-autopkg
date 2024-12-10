import os
import re
from src.config.config import configuration
from src.log import logger


class MavenLogAnalysis:
    def __init__(self, metadata):
        self.metadata = metadata
        pom_jars_pat = r"Could not resolve dependencies for project ([a-zA-Z0-9.:-]+):(jar|war):([0-9a-zA-Z.]+)" \
                             r": The following artifacts could not be resolved:[\s]+([a-zA-Z0-9-_.:]+(, ){0,1}){1,}"
        pom_jar_pat = r"Could not resolve dependencies for project ([a-zA-Z0-9.:-]+):([a-zA-Z0-9.:-]+:)+([0-9a" \
                           r"-zA-Z.]+): Cannot access ([a-zA-Z0-9-]+) \([a-zA-Z0-9.://-]+\) in offline mode and the" \
                           r" artifact ([a-zA-Z0-9.\-:]+):(jar|war)(:[0-9a-zA-Z.]+)?:([0-9a-zA-Z.]+) has not been d" \
                           r"ownloaded from it before"
        pom_plugin_pat = r"Plugin ([a-zA-Z\-.:]+):([0-9.]+) or one of its dependencies could not be resolved"
        pom_plugins_pat = r"Unable to generate requires on unresolvable artifacts: ([a-zA-Z0-9-.:]+(, ){0,1}){1,}"
        pom_plugin_miss_pat = r"The parameters '([a-zA-Z0-9]+)' for goal [a-zA-Z0-9-.:]+:[a-zA-Z]+ are missing or invalid"
        pom_compile_error_pat = r"(on project ([0-9a-zA-Z.-]+): Compilation failure|COMPILATION ERROR)"
        pom_package_not_exist_pat = r"((/[a-zA-Z0-9.-]+)+.[a-zA-Z0-9-]+):(.+) package [0-9a-zA-Z.-]+ does not exist"
        pom_cannot_find_symbol_pat = r"((/[a-zA-Z0-9.-]+)+.[a-zA-Z0-9-]+):\[[0-9,]+\] error: cannot find symbol"
        # pom_system_scope_pat = r"Failed to execute goal (.+) on project .+: Some reactor artifacts have dependencies with scope \"system\". "
        pom_maven_plugin_pat = r"Failed to execute goal org.apache.maven.plugins:(.+?):([0-9.]+)"
        pom_failed_plugin_pat = r"Failed to execute goal ((?!org.apache.maven.plugins)([a-zA-Z0-9.:-]+):(.+?)):([0-9.]+)"
        # pom_non_resolvable_parent_pom_pat = r"Non-resolvable parent POM for ([a-zA-Z0-9.:-]+):([a-zA-Z0-9.:-]+:)+([a-zA-Z0-9.]+): Cannot access ([a-zA-Z0-9-]+) \([a-zA-Z0-9.://-]+\) in offline mode and the artifact (.+):([0-9.]+) has not been downloaded from it before"
        self.analysis_methods = {
            pom_jars_pat: self.failed_pattern_update_by_java_jars,
            pom_jar_pat: self.failed_pattern_update_by_java_jar,
            pom_plugin_pat: self.failed_pattern_update_by_java_plugin,
            pom_plugins_pat: self.failed_pattern_update_by_java_plugins,
            pom_plugin_miss_pat: self.failed_pattern_update_by_java_plugin_miss,
            pom_package_not_exist_pat: self.add_pom_remove_dir,
            pom_cannot_find_symbol_pat: self.add_pom_remove_dir,
            pom_maven_plugin_pat: self.add_pom_remove_plugin,
            pom_failed_plugin_pat: self.failed_pattern_update_by_java_failed_plugin,
            pom_compile_error_pat: ""
        }

    def analysis_single_pattern(self, line):
        for pattern, method in self.analysis_methods.items():
            pat = re.compile(pattern)
            match = pat.search(line)
            if match:
                target = match.group(1)
                if method == "":
                    return False
                logger.info("maven_method: " + pattern)
                return method(target, line=line)
        return False

    def failed_pattern_update_by_java_plugin(self, plugin_fullname, line=""):
        plugin_name = plugin_fullname.split(":")[1]
        if f'mvn({plugin_fullname})' in self.metadata["buildRequires"]:
            self.metadata.setdefault("mavenRemovePlugins", []).append(plugin_name)
            self.metadata["buildRequires"].remove(f'mvn({plugin_fullname})')
        else:
            self.add_pom_remove_plugin(target=plugin_name, line=line)

    def failed_pattern_update_by_java_failed_plugin(self, plugin_fullname):
        plugin_name = plugin_fullname.split(":")[1]
        if f'mvn({plugin_fullname})' in self.metadata["buildRequires"]:
            self.add_java_remove_plugins(plugin_name)
            self.metadata["buildRequires"].remove(f'mvn({plugin_fullname})')
        else:
            self.add_java_remove_plugins(plugin_name)
            return True

    def failed_pattern_update_by_java_plugin_miss(self, obj, line=""):
        match = re.search(r'goal\s([a-zA-Z0-9-.:]+)', line)
        pluginFullName = match.group(1)
        pluginName = pluginFullName.split(":")[1]
        self.add_java_remove_plugins(pluginName)
        return True

    def add_pom_remove_plugin(self, target=None, line=""):
        match = re.search(
            r'and the artifact ([a-zA-Z0-9.\-:]+):(jar|war):([0-9.]+) has not been downloaded from it before', line)
        if match is None and target is not None:
            jarName = target
        elif match is None:
            logger.info("No match in error log!!!")
            return False
        else:
            jarFullName = match.group(1)
            jarName = jarFullName.split(":")[1]
        logger.info("jarName: " + jarName)
        modulePomNames = self.get_modules_and_pom_by_jar_name(jarName)
        remove_plugins = []
        remove_plugins_root_pom = False
        for modulePomName in modulePomNames:
            if modulePomName != "pom_xml" and "pom_xml" in modulePomName:
                remove_plugins.append("{} {}".format(jarName, modulePomName.replace('/pom_xml', '')))
            if modulePomName == "pom_xml":
                remove_plugins_root_pom = True
                break
        if remove_plugins_root_pom:
            self.add_java_remove_plugins(jarName)
            return True
        else:
            for remove_plugin in remove_plugins:
                self.add_java_remove_plugins(remove_plugin)
            return len(remove_plugins) > 0

    def add_pom_disable_module(self, jar_name):
        modulePomNames = self.get_modules_and_pom_by_jar_name(jar_name)
        module_dir = modulePomNames[0].split('/')[0]
        self.add_java_disable_modules(module_dir)
        return True

    def failed_pattern_update_by_java_jars(self, module_fullname, line):
        match = re.search(r'The following artifacts could not be resolved:[\s]+(([a-zA-Z0-9-_.:]+(, ){0,1}){1,})', line)
        jarFullNamesStr = match.group(1)
        jarFullNames = jarFullNamesStr.split(", ")
        for jarFullName in jarFullNames:
            jarName = jarFullName.split(":jar")[0]
            self.process_single_java_jar(jarName, module_fullname)

    def process_single_java_jar(self, jar_fullname, module_fullname):
        jarName = jar_fullname.split(":")[1]

        if jarName in configuration.maven_disable_modules:
            self.add_pom_disable_module(module_fullname.split(":")[1])
            return

    def failed_pattern_update_by_java_plugins(self, line):
        artifacts = line.split(": ")[2].split(", ")
        for pluginFullName in artifacts:
            pluginName = pluginFullName.split(":")[1]
            self.add_java_remove_plugins(pluginName)

    def add_pom_remove_dir(self, full_path, line):
        if 'does not exist' in line:
            match = re.search(r'package ([0-9a-zA-Z.-]+) does not exist', line)
            if match:
                moduleName = full_path.split("/")[5]
                self.add_java_disable_modules(moduleName)
                return True

        directories = full_path.split("/")[5:]
        _dir = "/".join(directories[0:len(directories) - 1])
        self.add_java_remove_dir(_dir)

    def add_pom_remove_system_scope_dep(self):
        pom_paths_str = self.metadata["pomInfo"]
        pom_paths = pom_paths_str.splitlines()
        for pom_path in pom_paths:
            # groupId = self.get_output("grep '<scope>system</scope>' -B 4 {} |grep -oP '(?<=<groupId>).*?(?=</groupId>)'|uniq".format(pom_path))
            group_id = self.metadata["pomInfo"]["groupID"]
            # artifactId = self.get_output("grep '<scope>system</scope>' -B 4 {} |grep -oP '(?<=<artifactId>).*?(?=</artifactId>)'|uniq".format(pom_path))
            artifact_id = self.metadata["pomInfo"]["artifactId"]
            # self.add_java_remove_deps("{}:{} {}".format(group_id, artifact_id, pom_path))

    def failed_pattern_update_by_java_jar(self, module_fullname, line):
        match = re.search(
            r'and the artifact ([a-zA-Z0-9.\-:]+):(jar|war)(:[0-9a-zA-Z.]+)?:([0-9a-zA-Z.]+) has not been downloaded from it before',
            line)
        self.process_single_java_jar(match.group(1), module_fullname)

    @staticmethod
    def add_java_remove_plugins(plugin):
        if not plugin:
            return False
        plugin.strip()
        if plugin in configuration.maven_remove_plugins:
            return False
        configuration.maven_remove_plugins.add(plugin)
        return True

    @staticmethod
    def add_java_disable_modules(module):
        if not module:
            return False
        module.strip()
        if module in configuration.maven_disable_modules:
            return False
        configuration.maven_disable_modules.add(module)
        return True

    @staticmethod
    def add_java_remove_dir(directory):
        if not directory:
            return False
        directory.strip()
        if dir in configuration.maven_delete_dirs:
            return False
        configuration.maven_delete_dirs.add(directory)
        return True

    def get_modules_and_pom_by_jar_name(self, jar_name):
        pom_names = []
        for pom_name in self.metadata:
            if "pom_xml" in pom_name and isinstance(self.metadata[pom_name], dict):
                if "build" in self.metadata[pom_name] and "plugins" in self.metadata[pom_name]["build"]:
                    for plugin in self.metadata[pom_name]["build"]["plugins"]["plugin"]:
                        if isinstance(plugin, dict) and plugin["artifactId"] == jar_name:
                            logger.info("================>>>>" + jar_name)
                            pom_names.append(pom_name)
        return pom_names
