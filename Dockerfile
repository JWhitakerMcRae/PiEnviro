# Install base image
FROM resin/raspberrypi3-ubuntu:latest

# Enable systemd
ENV INITSYSTEM on

# Install base OS tools and dependencies
RUN apt-get update && apt-get -y install \
    build-essential \
    net-tools \
    openssh-server \
    pkgconf \
    rpi-update \
    vim \
    wget
RUN apt-get install --reinstall \
    raspberrypi-bootloader

# Install pip and other script requirements
RUN apt-get update && apt-get -y install \
    python3-dev \
    python3-pip \
    sense-hat
#RUN apt-get update && apt-get -y install \
#    bluetooth \
#    bluez \
#    libbluetooth-dev \
#    libboost-all-dev \
#    libboost-python-dev \
#    libglib2.0-dev \
RUN pip3 install -U \
    flask \
#    gattlib \
    netifaces \
    Pint \
#    pybluez \
    PyYAML

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
