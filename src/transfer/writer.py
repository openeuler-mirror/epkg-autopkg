import os
import re
import yaml
from jinja2 import Environment, FileSystemLoader
from src.config import config_path
from src.config.config import configuration


STR_KEYS = ('name',
            'version',
            'release',
            'epoch',
            'group',
            'prefix',
            'summary',
            'description',
            'license',
            'homepage',
            'buildRoot',
            'exclusiveArch',
            'buildArch',
            'autoReq',
            'autoProv',
            'autoReqProv',
            )

LIST_KEYS = ('recommends',
             'excludeArch',
             'buildRequires',
             'suggests',
             'requires',
             'requiresPre',
             'requiresPost',
             'requiresPreun',
             'requiresPostun',
             'requiresPretrans',
             'requiresPosttrans',
             'buildConflicts',
             'provides',
             'conflicts',
             'includeSource',
             'obsoletes'
             )

DICT_KEYS = ('source',
             'patchset'
             )

PHASE_KEYS = ('prep',
              'build',
              'install',
              'check',
              'clean',
              )

RUNTIMEPHASE_KEYS = ('pre',
                     'preun',
                     'pretrans',
                     'preuntrans',
                     'post',
                     'postun',
                     'posttrans',
                     'postuntrans',
                     'verify',
                     'triggerprein',
                     'triggerin',
                     'triggerun',
                     'triggerpostun',
                     'filetriggerin',
                     'filetriggerun',
                     'filetriggerpostun',
                     'transfiletriggerin',
                     'transfiletriggerun',
                     'transfiletriggerpostun',
                     )

FILES_KEYS = ('files',)


def repr_str(dumper, data):
    if '\n' in data:
        return dumper.represent_scalar(u'tag:yaml.org,2002:str', data, style='|')
    return dumper.org_represent_str(data)


class SpecWriter(object):
    def __init__(self, name, path):
        self.spec_file = os.path.join(path, f"{name}.spec")
        self.metadata = {}

    def transform_type(self):
        target_metadata = self.metadata.copy()
        for k, v in target_metadata.items():
            if isinstance(v, set):
                self.metadata[k] = list(v)

    def parse(self):
        self.transform_type()

    def print_params(self, value):
        """
        输出spec内容时，有可能存在不合理逻辑的情况，可以在这里做整理
        :param value:
        :return:
        """
        if re.fullmatch("subpackage.*\.files", value):
            tmp_list = value.split(".")
            return "%files " + tmp_list[1]
        return value

    def trans_data_to_spec(self, metadata, change_log=""):
        self.metadata = metadata
        self.parse()
        j2_loader = FileSystemLoader("/")
        env = Environment(loader=j2_loader)
        spec_j2 = env.get_template(os.path.join(config_path, "spec.j2"))
        spec_content = spec_j2.render({
            'metadata': self.metadata,
            'print_params': self.print_params,
            'changelog': change_log
        })

        def collation_spec_content(content):
            """
            整理模板引擎处理过后的spec数据
            :param content:
            :return:
            """
            while "\n\n\n\n" in content:
                content = content.replace("\n\n\n\n", "{%- if 'subpackage.' in packagename -%}\n\n\n")
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
