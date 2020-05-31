FROM blumenthal/ropod-base-cpp:latest

RUN apt-get -y update && apt-get install -y \
    vim \
    git \
    cmake \
    build-essential \
    automake \
    libtool \
    libtool-bin \
    pkg-config \
    wget \
    curl \
    unzip \
    libssl-dev \
    libsasl2-dev \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

ADD . /opt/ropod/ropod_common/
WORKDIR /opt/ropod/ropod_common/pyropod
RUN python3 -m pip install --upgrade pip \
    && pip3 install -r requirements.txt && \
    python3 setup.py develop
