import os
import re
import yaml
from jinja2 import Environment, FileSystemLoader
from src.config import config_path
from src.config.config import configuration


def repr_str(dumper, data):
    if '\n' in data:
        return dumper.represent_scalar(u'tag:yaml.org,2002:str', data, style='|')
    return dumper.org_represent_str(data)


class SpecWriter(object):
    def __init__(self, name, path):
        self.spec_file = os.path.join(path, f"{name}.spec")
        self.metadata = {}
        self.target_metadata = {}

    def parse_subpackage(self):
        """
         {'subpackage': {'package1': { 'condition1': {'field1': {
                                                               'field1_condition1': 'field1_values',
                                                               'field1_condition2': 'field1_values'
                                                               }
                                                     },
                                      'condition2': {}
                                     },
                         'package2': { 'condition1': {}, 'condition2': {}}
                         }
         }
        """
        self.target_metadata['subpackage'] = {}
        for main_field in self.metadata:
            if main_field.startswith('subpackage.'):
                if main_field.__contains__(" rpmWhen "):
                    condition = main_field[main_field.find(" rpmWhen ") + 1:]
                    package_name = main_field[main_field.find('.') + 1:main_field.find(" rpmWhen ")]
                else:
                    condition = ''
                    package_name = main_field[main_field.find('.') + 1:]
                self.target_metadata['subpackage'].setdefault(package_name, {}).\
                    update({condition: self.metadata[main_field]})

                # 解析子包中所有字段
                values = {}
                for sub_filed in self.target_metadata['subpackage'][package_name][condition]:
                    sub_condition = ''
                    sub_values = self.target_metadata['subpackage'][package_name][condition][sub_filed]
                    if sub_filed.__contains__(' rpmWhen '):
                        sub_condition = sub_filed[sub_filed.find(' rpmWhen ') + 1:]
                        sub_filed = sub_filed[0:sub_filed.find(' rpmWhen ')]
                    values.setdefault(sub_filed, {}).update({sub_condition: sub_values})
                del self.target_metadata['subpackage'][package_name][condition]
                self.target_metadata['subpackage'][package_name][condition] = values

    def parse_simple_keys(self):
        """
        {'simple_key': {'condition1': 'value1', 'condition2': 'value2'}}
        :return:
        """
        KEYS = STR_KEYS + LIST_KEYS + DICT_KEYS
        for main_filed in self.metadata:
            for key in KEYS:
                if main_filed.startswith(key):
                    condition = ''
                    if main_filed.__contains__(' rpmWhen '):
                        condition = main_filed[main_filed.find(' rpmWhen ') + 1:]
                    if self.target_metadata.get(key,{}).get(condition):
                        self.target_metadata[key][condition].extend( self.metadata[main_filed])
                        break
                    self.target_metadata.setdefault(key, {}).\
                        update({condition: self.metadata[main_filed]})
                    break

    def format_meta(self):
        """
        trans metadata{'meta': {'file1': 'value1','file2': 'value2'}}
        to metadata{'file1': 'value1','file2': 'value2'}
        :return:
        """
        if 'meta' in self.metadata:
            for key in self.metadata['meta']:
                self.metadata[key] = self.metadata['meta'][key]
            del self.metadata['meta']
        for key in self.metadata:
            if key.startswith("subpackage"):
                value = self.metadata[key]
                if 'meta' in value:
                    for sub_key in value['meta']:
                        self.metadata[key][sub_key] = value['meta'][sub_key]
                    del self.metadata[key]['meta']

    def format_runtimePhase(self):
        for key in list(self.metadata.keys()):
            if key.startswith("runtimePhase."):
                value = self.metadata[key]
                del self.metadata[key]
                new_key = key.replace('runtimePhase.', "", 1)
                self.metadata[new_key] = value
            if key.startswith("subpackage."):
                sub_value = self.metadata[key]
                for sub_key in list(sub_value.keys()):
                    if sub_key.startswith("runtimePhase."):
                        value = sub_value[sub_key]
                        del self.metadata[key][sub_key]
                        new_key = sub_key.replace('runtimePhase.', "", 1)
                        self.metadata[key][new_key] = value

    def convert_double_percent_sign(self):
        for k, v in self.metadata.items():
            if type(v) is str:
                self.metadata[k] = v.replace("\%\%", "%%")
            if k.startswith("subpackage"):
                for sub_k, sub_v in self.metadata[k].items():
                    if type(sub_v) is str:
                        self.metadata[k][sub_k] = sub_v.replace("\%\%", "%%")

    def parse_macros(self):
        self.target_metadata['defineFlags'] = {}
        if 'rpmMacros' in self.metadata:
            self.target_metadata['rpmMacros'] = self.metadata['rpmMacros']
            self.parse_applied_macros()
        if 'rpmGlobal' in self.metadata:
            self.target_metadata['rpmGlobal'] = self.metadata['rpmGlobal']
        for field in self.metadata:
            if field.startswith('defineFlags'):
                condition = ''
                if field.__contains__(' rpmWhen '):
                    condition = field[field.find(' rpmWhen ') + 1:]
                becond_dict = self.metadata[field]
                target_dict = {}
                for k in becond_dict:
                    if k.startswith("+"):
                        target_k = "%bcond_without " + k[1:]
                    elif k.startswith("-"):
                        target_k = "%bcond_with " + k[1:]
                    else:
                        target_k = k
                    target_dict[target_k] = becond_dict[k]
                # todo defineFlags后的值添加为评论
                self.target_metadata['defineFlags'][condition] = target_dict
                break

    def parse_applied_macros(self):
        macros_line_list = self.target_metadata['rpmMacros'].split(os.linesep)
        remove_list = []
        for line in macros_line_list:
            if re.fullmatch("%\{load:%\{SOURCE\w*}}", line):
                remove_list.append(line)
        for line in remove_list:
            macros_line_list.remove(line)
        self.target_metadata['rpmMacros'] = os.linesep.join(macros_line_list)
        self.target_metadata.setdefault("appliedMacros", {}).setdefault("", os.linesep.join(remove_list))

    def merge_compile_flags(self):
        # configureFlags merge to phase.configure, cmakeFlags merge to phase.cmake
        compile_type = ""
        need_add_configure = False
        for main_field in self.metadata.copy():
            if not re.fullmatch("build\.(configure|cmake|make)\w*\.flags", main_field):
                continue
            compile_type = re.findall("build\.(configure|cmake|make)\w*\.flags", main_field)[0]
            func_name = "phase." + main_field.split(".")[1]
            if func_name not in self.metadata and compile_type == "configure":
                continue
            prefix = ""
            break_line = "\\"
            if compile_type == "cmake":
                prefix = "-D"
                break_line = "\\\\\\"
            elif compile_type == "make":
                break_line = "\\\\\\"
            elif compile_type == "configure":
                configure_name = main_field.split(".")[1]
                pre_command = ""
                if configure_name != "configure":
                    pre_command =  f"%define build_configure_flags %build_{configure_name}_flags{os.linesep}"
                if f"phase.{configure_name}" in self.metadata and \
                        re.search("^\.+/configure", self.metadata[f"phase.{configure_name}"]):
                    command = re.findall("^\.+/configure", self.metadata[f"phase.{configure_name}"])[0]
                    if f"build.{configure_name}.flags" in self.metadata and \
                            "%{?add_configure_flags}" not in self.metadata[f"phase.{configure_name}"]:
                        self.metadata[f"phase.{configure_name}"] = self.metadata[f"phase.{configure_name}"].replace(
                            command, pre_command + "%{?add_configure_flags} " + command)
                elif pre_command != "" and f"phase.{configure_name}" in self.metadata:
                    self.metadata[f"phase.{configure_name}"] = pre_command + self.metadata[f"phase.{configure_name}"]
            flags = copy.deepcopy(self.metadata.get(main_field))
            flags_value = "%global {0} {1}{2}".format(main_field.replace(".", "_"), break_line, os.linesep)
            for flag, value in flags.items():
                if isinstance(value, bool):
                    if compile_type == "cmake":
                        value = "ON" if value else "OFF"
                    elif compile_type == "configure" and value is False:
                        flag = flag.replace("enable", "disable").replace("--with-", "--without-")
                tmp_value = "=" + str(value)
                if compile_type == "configure" and isinstance(value, bool):
                    tmp_value = ""
                value = tmp_value
                if " rpmWhen " in flag:
                    base_key = flag.split(" rpmWhen ")[0]
                    conditions = flag.split(" rpmWhen ")[1:]
                    for condition in conditions:
                        flags_value += f'%if {condition} \\{os.linesep}'
                    flags_value += f"    {prefix}{base_key}{value} {break_line}{os.linesep}" + f"%endif \\{os.linesep}" * len(conditions)
                else:
                    flags_value += f"    {prefix}{flag}{value} {break_line}{os.linesep}"
            flags_value = flags_value.rstrip().rstrip("\\").rstrip() + os.linesep
            if "rpmMacros" not in self.target_metadata:
                self.target_metadata.setdefault("rpmMacros", flags_value)
            else:
                self.target_metadata["rpmMacros"] += flags_value

    def parse_config_settings(self):
        for config_name, config_path in CONFIG_SET_FILES.items():
            config_name = f"build.{config_name}"
            if config_name in self.metadata and isinstance(self.metadata.get(config_name), dict):
                set_str = ""
                arch = ""
                for key, value in self.metadata.get(config_name).items():
                    if key == "ARCH":
                        arch = value
                        continue
                    with open(config_name, "a+") as f:
                        f.write(f"{key}={value}{os.linesep}")
                if arch != "" and "phase.prep" in self.metadata:
                    config_path = config_path.format(arch)
                    self.metadata["phase.prep"] = self.metadata["phase.prep"].rstrip()
                    self.metadata["phase.prep"] += f"{os.linesep}merge_config.sh -m {config_path} " \
                                                   "%{_sourcedir}/"  + f"{config_name}{os.linesep}" \
                                                   f"mv .config {config_path} -f{os.linesep}"

    def parse_phase(self):
        # phase. prep build install check clean
        # move configure to build
        for main_field in self.metadata:
            if re.match("phase\.(configure|cmake).*", main_field):
                configure_name = main_field.split(".")[-1]
                if 'phase.build' in list(self.metadata):
                    lines = self.metadata['phase.build'].split("\n")
                    target_lines = []
                    for line in lines:
                        _line = line.strip()
                        if _line == configure_name:
                            target_lines.append(self.metadata[main_field].strip())
                        else:
                            target_lines.append(line)
                    self.metadata['phase.build'] = "\n".join(target_lines)
        # move phase. to self.target_metadata
        for main_field in self.metadata:
            if main_field.startswith('phase.') and 'rpm_macro_param' not in main_field and 'configure' not in main_field:
                condition = ''
                param = ''
                if main_field.__contains__(" rpmWhen "):
                    condition = main_field[main_field.find(" rpmWhen ") + 1:]
                    target_field = main_field[main_field.find('.') + 1:main_field.find(" rpmWhen ")]
                    target_param_filed = 'phase.' + target_field + ':rpm_macro_param ' + condition
                else:
                    target_field = main_field[main_field.find('.') + 1:]
                    target_param_filed = 'phase.' + target_field + ':rpm_macro_param'
                if target_param_filed in self.metadata:
                    param = self.metadata[target_param_filed]
                value = self.metadata[main_field]
                self.target_metadata.setdefault(target_field, []).\
                    append({'condition': condition, 'param': param, 'value': value})

    def trans_shell(self, meta_json, spec_key, condition, param):
        key_param = spec_key + ":rpm_macro_param"
        for key in meta_json:
            # 避免相同前缀, 如：pre, preun
            pattern = '^' + spec_key + '\\w+.*$'
            if re.match(pattern, key):
                continue
            if key.startswith(spec_key) and not key.startswith(key_param):
                value = meta_json[key]
                param_key = key.replace(spec_key, key_param, 1)
                if param_key in meta_json:
                    param += ' ' + meta_json[param_key]
                if key.__contains__(' rpmWhen '):
                    if condition:
                        key_condition = key[key.find(' rpmWhen ') + len(' rpmWhen '):]
                        if condition != "rpmWhen " + key_condition:
                            condition += ' && ' + key[key.find(' rpmWhen ') + len(' rpmWhen '):]
                    else:
                        condition = key[key.find(' rpmWhen '):]
                self.target_metadata.setdefault(spec_key, []).append(
                    {'condition': condition, 'param': param, 'value': value})
            # 只有参数
            if key.startswith(key_param):
                target_key = key.replace(key_param, spec_key, 1)
                if target_key not in meta_json:
                    value = ""
                    param += ' ' + meta_json[key]
                    if key.__contains__(' rpmWhen '):
                        if condition:
                            key_condition = key[key.find(' rpmWhen ') + len(' rpmWhen '):]
                            if condition != "rpmWhen " + key_condition:
                                condition += ' && ' + key_condition
                        else:
                            condition = key[key.find(' rpmWhen '):]
                    self.target_metadata.setdefault(spec_key, []).append(
                        {'condition': condition, 'param': param, 'value': value})

    def parse_shell(self):
        """
        trans matadata{'pre': 'values1', 'subpackage.package1': {'pre': 'values_sub1'}}
        to target_metadata{'pre': [{'condition': '', 'param': '', 'values': 'values1'},
        {'condition': '', 'parm': '-n package1', 'values': 'values_sub1'}]
        """
        KEYS = RUNTIMEPHASE_KEYS + FILES_KEYS
        for spec_key in KEYS:
            param = ''
            condition = ''
            self.trans_shell(self.metadata, spec_key, condition, param)
            for key in self.metadata:
                if key.startswith('subpackage.'):
                    if key.__contains__(' rpmWhen '):
                        sub_name = key[key.find(".") + 1:key.find(' rpmWhen ')]
                        condition = key[key.find(' rpmWhen ') + 1:]
                    else:
                        sub_name = key[key.find(".") + 1:]
                        condition = ""
                    sub_values = self.metadata[key]
                    param = "-n " + sub_name
                    self.trans_shell(sub_values, spec_key, condition, param)

    def parse(self):
        self.format_meta()
        self.format_runtimePhase()
        self.convert_double_percent_sign()
        self.parse_macros()
        self.parse_simple_keys()
        self.parse_subpackage()
        self.merge_compile_flags()
        self.parse_config_settings()
        self.parse_phase()
        self.parse_shell()

    def trans_compile_args(self):
        """
        转换编译选项

        :return:
        """
        if "build" in self.metadata:
            # check is only make or not
            build_info_list = self.metadata["phase.build"].split(os.linesep)
            only_make = False
            configure_make = False
            for line in build_info_list:
                if re.search("#.*make", line) is None and "make" in line and "cmake" not in line and not configure_make:
                    only_make = True
                if re.search("#.*configure", line) is None and ("/configure" in line or "%configure" in line):
                    only_make = False
                    configure_make = True
            # compileExport 是列表，在%build字段中
            if "compileExport" in self.metadata and isinstance(self.metadata["compileExport"], dict):
                export_list = []
                for export_name, export_value in self.metadata["compileExport"].items():
                    if isinstance(export_value, list):
                        export_value = ",".join(export_value)
                    export_list.append("export " + export_name + "=\"" + export_value + "\"")
                self.metadata["compileExport"] = export_list
            # env.CC, env.LDFLAGS, env.CFLAGS都是字符串
            if "env.CC" in self.metadata:
                self.metadata["phase.build"] = "export CC=\"" + self.metadata["env.CC"] + "\"" + os.linesep + self.metadata[
                    "build"]
            if "env.CFLAGS" in self.metadata:
                if only_make:
                    self.metadata["build"] = "export CFLAGS=\"" + self.metadata["env.CFLAGS"] + "\"" + os.linesep + \
                                             self.metadata["build"]
                else:
                    if "rpmMacros" in self.metadata:
                        self.metadata["rpmMacros"].append("%global optflags %optflags " + self.metadata["env.CFLAGS"])
                    else:
                        self.metadata["rpmMacros"] = ["%global optflags %optflags " + self.metadata["env.CFLAGS"]]
            if "env.LDFLAGS" in self.metadata:
                if only_make:
                    self.metadata["build"] = "export LDFLAGS=\"" + self.metadata["env.LDFLAGS"] + "\"" + os.linesep + \
                                             self.metadata["build"]
                else:
                    if "rpmMacros" in self.metadata:
                        self.metadata["rpmMacros"].append(
                            "%global build_optflags %build_optflags " + self.metadata["env.LDFLAGS"])
                    else:
                        self.metadata["rpmMacros"] = [
                            "%global build_optflags %build_optflags " + self.metadata["env.LDFLAGS"]]

    def parse_when(self, line):
        """
        根据条件表达式还原spec中的%if表达式
        :param line: 条件表达式
        :return:
        """
        if re.search("rpmWhen\s+[+-][\w_]+", line) is not None:
            results = re.findall("rpmWhen\s+[+-][\w_]+", line)
            for result in results:
                if "+" in result:
                    condition = result.split("+")[1]
                    line = line.replace(result, "%if %{with " + condition + "}")
                elif "-" in result:
                    condition = result.split("-")[1]
                    line = line.replace(result, "%if %{without " + condition + "}")
            # do(rpmWhen %%%{rpmGlobal.openEuler}=>%if 0%{?openEuler})
        if re.search("rpmWhen\s+0?%\{\??[\w.]+}.*0?%\{\??[\w.]+}", line) is not None:
            results = re.findall("rpmWhen\s+0?%\{\??[\w.]+}.*0?%\{\??[\w.]+}", line)
            for result in results:
                line = line.replace(result, result.replace("rpmWhen", "%if"))
        elif re.search("rpmWhen\s+0?%\{\??[\w.]+}", line) is not None:
            results = re.findall("rpmWhen\s+0?%\{\??[\w.]+}", line)
            for result in results:
                line = line.replace(result, result.replace("rpmGlobal.", "").replace("rpmWhen", "%if"))
            # do(rpmWhen arch in=>%ifarch|%ifos|%ifnarch|%ifnos)
        if re.search("rpmWhen arch|os in [\w.]+", line) is not None:
            results = re.findall("rpmWhen arch in [\w.]+", line) + re.findall("rpmWhen os in [\w.]+", line)
            for result in results:
                line = line.replace(result,
                                    result.replace("rpmWhen arch in", "%ifarch").replace("rpmWhen os in", "%ifos"))
        if re.search("rpmWhen arch|os not in [\w.]+", line) is not None:
            results = re.findall("rpmWhen arch not in [\w.]+", line) + re.findall("rpmWhen os not in [\w.]+", line)
            for result in results:
                line = line.replace(result, result.replace("rpmWhen arch not in", "%ifnarch").replace(
                    "rpmWhen os not in", "%ifnos"))
        if "rpmWhen" in line:
            results = re.findall("rpmWhen\s+.*", line)
            for result in results:
                line = line.replace(result, result.replace("rpmWhen not", "%if !").replace("rpmWhen", "%if"))
        if line.endswith("\n"):
            line = line[0:-1]
        return line.replace(" %if", " \n%if")

    def print_endif(self, condition):
        """
        在spec中，一个%if条件对应一个%endif,
        condition存在多个条件嵌套，例如：rpmWhen arch in x86 rpmrpmWhen +benchtests,
        所以根据rpmWhen的个数确定%endif的个数
        :param condition:
        :return:
        """
        end_str = ''
        results = re.findall("rpmWhen", condition)
        for _ in results:
            end_str += "%endif\n"
        return end_str

    def print_value(self, value):
        """
        输出spec内容时，有可能存在不合理逻辑的情况，可以在这里做整理
        :param value:
        :return:
        """
        inline_conditions = re.findall("%if", value)
        inline_endif = re.findall("%endif", value)
        end_count = len(inline_conditions) - len(inline_endif)
        if end_count >= 0:
            for _ in range(end_count):
                value = value.rstrip() + "\n%endif\n"
        else:
            value = value.replace("%endif\n", "", abs(end_count))
        return value

    def trans_data_to_spec(self, metadata, change_log=""):
        self.metadata = metadata
        self.parse()
        j2_loader = FileSystemLoader("/")
        env = Environment(loader=j2_loader)
        spec_j2 = env.get_template(os.path.join(config_path, "spec.j2"))
        spec_content = spec_j2.render({
            'metadata': self.target_metadata,
            'parse_when': self.parse_when,
            'print_endif': self.print_endif,
            'print_value': self.print_value,
            'changelog': change_log
        })

        def collation_spec_content(content):
            """
            整理模板引擎处理过后的spec数据
            :param content:
            :return:
            """
            while "\n\n\n\n" in content:
                content = content.replace("\n\n\n\n", "\n\n\n")
            return content

        spec_content = collation_spec_content(spec_content)
        file = open(self.spec_file, "w")
        file.write(spec_content)
        file.close()


class YamlWriter(object):
    def __init__(self, name, path):
        self.name = name
        self.path = path
        self.main_yaml = "package.yaml"
        self.file_yaml = "files.yaml"
        self.compile_script = "phase.sh"

    def create_yaml(self, metadata):
        with open(os.path.join(configuration.download_path, self.main_yaml), "w") as f:
            yaml.SafeDumper.org_represent_str = yaml.SafeDumper.represent_str
            yaml.add_representer(str, repr_str, Dumper=yaml.SafeDumper)
            f.write(yaml.safe_dump(metadata, sort_keys=False))

    def create_phase_script(self, metadata: dict):
        functions = {}
        # change spec-mode to dict-mode
        for _key, value in metadata.items():
            for phase in configuration.phase_member:
                if _key == phase or re.match(f"{phase}_\w+", _key):
                    functions[_key] = value
        # write function dict into shell file
        with open(os.path.join(configuration.download_path, self.compile_script), "w") as ph:
            for function, text in functions.items():
                ph.write(f"function {function}() " + "{" + os.linesep)
                ph.write(text.strip())
                ph.write("}" + os.linesep * 3)

    def create_files(self, metadata):
        files_data = {}
        for package, file in metadata.items():
            if package == "files":
                files_data.setdefault("files", os.linesep.join(list(file)))
            elif package.startswith("subpackage.") and package.endswith(".files"):
                files_data.setdefault(f"subpackage.{package}.files", os.linesep.join(list(file)))
        with open(os.path.join(configuration.download_path, self.file_yaml), "w") as f:
            yaml.SafeDumper.org_represent_str = yaml.SafeDumper.represent_str
            yaml.add_representer(str, repr_str, Dumper=yaml.SafeDumper)
            f.write(yaml.safe_dump(files_data, sort_keys=False))

    def create_yaml_package(self, metadata):
        self.create_yaml(metadata)
        self.create_files(metadata)
        self.create_phase_script(metadata)
