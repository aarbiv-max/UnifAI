# Use the specified Red Hat Universal Base Image 9 (UBI9)
FROM registry.access.redhat.com/ubi9/python-311
#FROM registry.access.redhat.com/ubi9/python-39
USER root
RUN dnf update -y && dnf install -y vim less iputils telnet && dnf clean all
RUN curl -L https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp/stable/openshift-client-linux.tar.gz -o oc.tar.gz && \
    tar -xvzf oc.tar.gz -C /usr/local/bin/ && \
    rm -f oc.tar.gz && \
    chmod +x /usr/local/bin/oc /usr/local/bin/kubectl

RUN curl -sSL https://get.helm.sh/helm-v3.14.0-linux-amd64.tar.gz -o helm.tar.gz && \ 
    tar -xvzf helm.tar.gz && \ 
    mv linux-amd64/helm /usr/local/bin/helm && \ 
    chmod +x /usr/local/bin/helm && \ 
    rm -rf linux-amd64 helm.tar.gz && \ 
    dnf clean all

RUN curl -fsSL https://rpm.nodesource.com/setup_18.x | bash - && \
dnf install -y nodejs && \
npm install -g yarn

USER default
ADD  --chown=default:root --chmod=777 ./backend $HOME/backend
ADD  --chown=default:root --chmod=777 ./rag  $HOME/rag
ADD  --chown=default:root --chmod=777 ./pipelines $HOME/pipelines
ADD  --chown=default:root --chmod=777 ./prompt_lab $HOME/prompt_lab
ADD  --chown=default:root --chmod=777 ./data_pre $HOME/data_pre

WORKDIR $HOME/backend/node_tools
RUN yarn install --immutable

WORKDIR $HOME/backend
RUN mkdir -p -m 777 $HOME/backend/venv $HOME/backend/logs
RUN ls -lia
RUN chmod -R g+w .

# Upgrade pip and install virtualenv
RUN pip3 install --upgrade pip virtualenv

# Create and activate a virtual environment
RUN virtualenv venv

# Activate the virtual environment and install required Python packages
RUN /bin/bash -c "source venv/bin/activate && \
    pip install -r requirementsBE.txt && \
    python -m spacy download en_core_web_sm"

# Ensure we install inside the virtual environment
RUN /bin/bash -c "source venv/bin/activate && pip install ../prompt_lab"

# Set the default command to activate the virtual environment and keep the container running
CMD ["/bin/bash", "-c", "source venv/bin/activate && python app.py"]
