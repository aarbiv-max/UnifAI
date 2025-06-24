
# Use the specified Red Hat Universal Base Image 9 (UBI9)
FROM registry.access.redhat.com/ubi9/python-311
ARG comp="multi-agent"

USER root
RUN dnf update --nobest -y && dnf install -y vim less iputils telnet && dnf clean all

COPY ./multi-agent/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# USER default
# RUN ls -lia

ADD  --chown=default:root --chmod=777 ./$comp $HOME/$comp
ADD  --chown=default:root --chmod=777 ./global_utils $HOME/global_utils

WORKDIR $HOME/$comp
RUN pwd
RUN mkdir -p -m 777 $HOME/$comp/venv $HOME/$comp/logs
RUN ls -lia
RUN chmod -R g+w .

USER default
RUN ls -lia

RUN pip3 install --upgrade pip virtualenv
RUN python3 -m venv venv

RUN /bin/bash -c "source venv/bin/activate && \
    pip install -r requirements.txt "

# Activate the virtual environment and install required global_utils
RUN /bin/bash -c "source venv/bin/activate && \
    pip install -e ../global_utils/"

ENTRYPOINT ["/entrypoint.sh"]