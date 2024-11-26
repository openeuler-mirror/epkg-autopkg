#!/usr/bin/env bash


python_build() {
  pip install setuptools wheel -i https://mirrors.aliyun.com/pypi/simple/
  if [ ! -f "requirements.txt " ]; then
    pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
  fi
  python3 setup.py build '--executable=/usr/bin/python3 -s'
}

python_install() {
  rm -rf /opt/buildroot
  mkdir /opt/buildroot
  python3 setup.py install -O1 --skip-build --root /root/buildroot
}
