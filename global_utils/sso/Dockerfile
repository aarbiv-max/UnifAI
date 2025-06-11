# Use the specified Red Hat Universal Base Image 9 (UBI9)
FROM registry.access.redhat.com/ubi9/python-311
USER root
RUN dnf update -y && dnf install -y vim less iputils telnet && dnf clean all

USER default
ADD requirements.txt .
RUN pip3 install --upgrade pip virtualenv
RUN virtualenv venv
ENV VIRTUAL_ENV=/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

ENTRYPOINT [ "/bin/bash" ]
