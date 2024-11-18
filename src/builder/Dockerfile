FROM openeuler-22.03-lts-sp2:latest

WORKDIR /root
RUN sed -i 's/openeuler.org\/openeuler/mirrors.huaweicloud.com/g' /etc/yum.repo.d/openEuler.repo
RUN yum makecache
RUN yum install -y git make gcc cmake python3-pip ruby ruby-devel rubygems-devel npm maven automake perl wget curl golang binutils bison
# 升级go1.18版本
RUN curl -s -S -L https://raw.githubusercontent.com/moovweb/gvm/master/binscripts/gvm-installer|sh
RUN sed -i s#GO_SOURCE_URL=https://#GO_SOURCE_URL=git://172.168.131.2:9418/upstream/#g /root/.gvm/scripts/install
RUN source /root/.gvm/scripts/gvm
RUN gvm install go1.20.6;gvm use go1.20.6;
RUN gvm install go1.22.4;gvm use go1.22.4;
RUN gvm uninstall go1.20.6
RUN gvm uninstall system
RUN yum remove -y golang

# 设置pip源
RUN echo "[global]" > ~/.config/pip/pip.conf
RUN echo "index-url = https://mirrors.aliyun.com/pypi/simple/" >> ~/.config/pip/pip.conf
# 设置gem源
RUN cat > ~/.gemrc << EOF
---
:sources:
  - https://mirrors.aliyun.com/rubygems/
EOF
RUN echo "export GOPROXY=https://goproxy.cn" >> /root/.bashrc
CMD ["bash"]