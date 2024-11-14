FROM openeuler-22.03-lts-sp2:latest

WORKDIR /root
RUN sed -i 's/openeuler.org\/openeuler/mirrors.huaweicloud.com/g' /etc/yum.repo.d/openEuler.repo
RUN yum makecache
RUN yum install -y git make gcc cmake python3-pip ruby ruby-devel rubygems-devel npm maven automake perl wget curl golang

# 设置pip源
RUN echo "[global]" > ~/.config/pip/pip.conf
RUN echo "index-url = https://mirrors.aliyun.com/pypi/simple/" >> ~/.config/pip/pip.conf
# 设置gem源
RUN cat > ~/.gemrc << EOF
---
:sources:
  - https://mirrors.aliyun.com/rubygems/
EOF
RUN pip install shyaml
CMD ["bash"]