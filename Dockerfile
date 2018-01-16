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
    vim \
    wget

# Install pip and other script requirements
RUN apt-get update && apt-get -y install \
    python-dev \
    python-pip \
    sense-hat
RUN pip install -U \
    flask \
    netifaces \
    pint \
    PyYAML

# Add user credentials
RUN useradd -m "pienviro" && \
    echo "root:pienviro1!" | chpasswd && \
    echo "pienviro:pienviro1!" | chpasswd
RUN echo "pienviro ALL=(ALL:ALL) ALL" >> /etc/sudoers

# Setup app environment
COPY start.sh config/* scripts/* /app/
RUN chmod 744 /app/start.sh

# Start app
CMD ["bash", "/app/start.sh"]
