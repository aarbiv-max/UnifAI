# Use the specified Red Hat Universal Base Image 9 (UBI9)
FROM registry.access.redhat.com/ubi9/python-311
#FROM registry.access.redhat.com/ubi9/python-39

USER root
RUN dnf update -y && dnf install -y vim less iputils telnet && dnf clean all

# Install OpenShift CLI tools
RUN curl -L https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp/stable/openshift-client-linux.tar.gz -o oc.tar.gz && \
    tar -xvzf oc.tar.gz -C /usr/local/bin/ && \
    rm -f oc.tar.gz && \
    chmod +x /usr/local/bin/oc /usr/local/bin/kubectl

# Install Helm
RUN curl -sSL https://get.helm.sh/helm-v3.14.0-linux-amd64.tar.gz -o helm.tar.gz && \
    tar -xvzf helm.tar.gz && \
    mv linux-amd64/helm /usr/local/bin/helm && \
    chmod +x /usr/local/bin/helm && \
    rm -rf linux-amd64 helm.tar.gz && \
    dnf clean all

USER default
# Add your application files (including supervisord.conf placed in ./backend)
ADD  --chown=default:root --chmod=777 ./backend $HOME/backend
ADD  --chown=default:root --chmod=777 ./rag     $HOME/rag
ADD  --chown=default:root --chmod=777 ./pipelines $HOME/pipelines
ADD  --chown=default:root --chmod=777 ./prompt_lab $HOME/prompt_lab
ADD  --chown=default:root --chmod=777 ./data_pre   $HOME/data_pre

WORKDIR $HOME/backend
RUN mkdir -p -m 777 $HOME/backend/venv $HOME/backend/logs
RUN ls -lia
RUN chmod -R g+w .


# Upgrade pip and install virtualenv
RUN pip3 install --upgrade pip virtualenv

# Create the virtual environment
RUN virtualenv venv

# Activate the virtual environment and install required Python packages
RUN /bin/bash -c "source venv/bin/activate && \
    pip install -r requirementsBE.txt && \
    python -m spacy download en_core_web_sm"

# Ensure we install the local package inside the virtual environment
RUN /bin/bash -c "source venv/bin/activate && pip install ../prompt_lab"

# Start Supervisor (using the supervisord.conf located in $HOME/backend)
CMD ["/bin/sh", "-c", ". ./venv/bin/activate && supervisord -c supervisord.conf"]
