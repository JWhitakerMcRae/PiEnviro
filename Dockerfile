# Install base image
FROM resin/raspberrypi3-debian:latest

# Enable systemd
ENV INITSYSTEM on

# Install base OS tools and dependencies
RUN apt-get update && apt-get -y install \
    build-essential \
    net-tools \
    openssh-server \
    pkgconf \
    rpi-update \
    vim
RUN apt-get update && apt-get -y install \
    python3 \
    python3-pip

# Install Python 3.6.4
#RUN apt-get update && apt-get install -y \
#    make \
#    build-essential \
#    libssl-dev \
#    zlib1g-dev \
#    libbz2-dev \
#    libreadline-dev \
#    libsqlite3-dev \
#    wget \
#    curl \
#    llvm \
#    libncurses5-dev \
#    libncursesw5-dev \
#    xz-utils \
#    tk-dev
#RUN wget https://www.python.org/ftp/python/3.6.4/Python-3.6.4.tgz && \
#    tar xvf Python-3.6.4.tgz && \
#    cd Python-3.6.4 && \
#    ./configure --with-ensurepip=install --enable-optimizations && \
#    make -j8 && \
#    sudo make install
#    ln -s /usr/local/bin/python3.6 /usr/local/bin/python3 && \
#    ln -s /usr/local/bin/python3.6 /usr/local/bin/python
#RUN python3.6 -m ensurepip --upgrade
#    ln -s /usr/local/bin/pip3.6 /usr/local/bin/pip3 && \
#    ln -s /usr/local/bin/pip3.6 /usr/local/bin/pip

# Install SenseHat utilities
RUN apt-get install --reinstall \
    raspberrypi-bootloader
CMD modprobe i2c-dev && apt-get update && apt-get -y install \
    sense-hat

# Install Bluetooth utilities
#RUN apt-get update && apt-get -y install \
#    bluetooth \
#    bluez \
#    libbluetooth-dev \
#    libboost-all-dev \
#    libboost-python-dev \
#    libglib2.0-dev \
#    python3-dev \
#    python3-pip
#RUN pip3 install -U \
#    gattlib \
#    pybluez

# Install remaining PiEnviro requirements
RUN pip3 install -U \
    flask \
    netifaces \
    Pint \
    PyYAML \
    requests

# Add user credentials
RUN useradd -m "pienviro" && \
    echo "root:pienviro1!" | chpasswd && \
    echo "pienviro:pienviro1!" | chpasswd && \
    echo "pienviro ALL=(ALL:ALL) ALL" >> /etc/sudoers

# Setup app environment
COPY start.sh config/* src/* /app/
RUN chmod 744 /app/start.sh

# Start app
CMD ["bash", "/app/start.sh"]
