#!/usr/bin/env bash


remove_plugin() {
  if [ $# -eq 0 ]; then
    # 如果没有参数，直接返回
    return
  else
    # 如果有参数，执行命令
    for param in "$@"; do
      python3 /usr/share/java-utils/pom_editor.py pom_remove_plugin -r :"$param"
    done
  fi
}

disable_module() {
  if [ $# -eq 0 ]; then
    # 如果没有参数，直接返回
    return
  else
    # 如果有参数，执行命令
    for param in "$@"; do
      python3 /usr/share/java-utils/pom_editor.py pom_disable_module -r :"$param"
    done
  fi
}

delete_dir() {
  if [ $# -eq 0 ]; then
    # 如果没有参数，直接返回
    return
  else
    # 如果有参数，执行命令
    for param in "$@"; do
      rm -rf "$param"
    done
  fi
}

maven_build() {
  yum install maven-local -y
  if [ -n "${mavenPath}" ]; then
    pushd ${mavenPath}
  fi
  remove_plugin "$maven_remove_plugins"
  disable_module "$maven_disable_modules"
  delete_dir "$maven_rm_dirs"
  python3 /usr/share/java-utils/mvn_build.py -b -f
  if [ $? -eq 0 ]; then
    echo "maven build finished"
  else
    echo "maven build failed"
    exit 1
  fi
}

maven_install() {
  if [ ! -f /root/package.yaml ]; then
    echo "package.yaml 文件不存在"
    exit 1
  fi
  # 使用 grep 和 awk 读取 name 字段的值
  name_value=$(grep -oP '^name:\s*\K.*' /root/package.yaml)
  # 检查 name 字段是否存在
  if [ -z "$name_value" ]; then
    echo "name 字段不存在"
  else
    echo "name 字段的值是: $name_value"
  fi
  xmvn-install -R .xmvn-reactor -n "$name_value" -d /opt/buildroot
  if [ $? -eq 0 ]; then
    echo "maven install finished"
  else
    echo "maven install failed"
    exit 1
  fi
}

