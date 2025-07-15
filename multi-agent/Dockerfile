
# Use the specified Red Hat Universal Base Image 9 (UBI9)
FROM registry.access.redhat.com/ubi9/python-311
#ARG comp="multi-agent"

USER root
#the line below is meant to add mongosh to the image (not the server though), this is for debugging option
# NOTE: the version we use here is mongo 8 if building this part fails you might need to find the latest available mongo shell repo.
RUN echo -e "[mongodb-org-8.0]\nname=MongoDB Repository\nbaseurl=https://repo.mongodb.org/yum/redhat/\$releasever/mongodb-org/8.0/\$basearch/\ngpgcheck=1\nenabled=1\ngpgkey=https://www.mongodb.org/static/pgp/server-8.0.asc" > /etc/yum.repos.d/mongodb-org-8.0.repo
RUN dnf update --nobest -y && dnf install -y vim less iputils telnet mongodb-mongosh && dnf clean all



# USER default
# RUN ls -lia

ADD  --chown=default:root --chmod=777 ./multi-agent $HOME/app
ADD  --chown=default:root --chmod=777 ./global_utils $HOME/global_utils

WORKDIR $HOME
COPY ./multi-agent/entrypoint.sh ./app/entrypoint.sh
RUN chmod +x ./app/entrypoint.sh
RUN pwd
RUN mkdir -p -m 777 $HOME/app/venv $HOME/app/logs
RUN ls -lia
RUN chmod -R g+w .

USER default
RUN ls -lia

RUN pip3 install --upgrade pip virtualenv
RUN python3 -m venv --prompt "virtualenv" venv
ENV VIRTUAL_ENV=$HOME/app/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN /bin/bash -c "pip install -r ./app/requirements.txt "

RUN /bin/bash -c "pip install -e ./global_utils/"

ENTRYPOINT ["./app/entrypoint.sh"]