# Use the specified Red Hat Universal Base Image 9 (UBI9)
FROM registry.access.redhat.com/ubi9/python-311

USER root
RUN dnf update -y && dnf install -y vim less iputils telnet && dnf clean all

COPY ./DataPipelineHub/backend/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER default

ADD  --chown=default:root --chmod=777 ./DataPipelineHub/backend $HOME/backend
ADD  --chown=default:root --chmod=777 ./global_utils $HOME/global_utils

WORKDIR $HOME/backend
RUN chmod -R g+w .

RUN pip3 install --upgrade pip virtualenv

RUN python3 -m venv venv

RUN /bin/bash -c "source venv/bin/activate && \
    pip install -r requirements.txt && \
    pip install ../global_utils/"

ENTRYPOINT ["/entrypoint.sh"]
