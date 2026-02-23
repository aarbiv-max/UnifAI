FROM registry.access.redhat.com/ubi9/python-311

USER root
RUN dnf update -y && dnf install -y vim less iputils && dnf clean all

USER default

ADD  --chown=default:root --chmod=777 ./backend $HOME/backend
ADD  --chown=default:root --chmod=777 ./global_utils $HOME/global_utils

WORKDIR $HOME/backend

RUN chmod -R g+w .

RUN pip3 install --upgrade pip virtualenv
RUN python3 -m venv venv

RUN /bin/bash -c "source venv/bin/activate && \
    pip install -r requirements.txt && \
    pip install -e ../global_utils/"

EXPOSE 8003

CMD ["venv/bin/gunicorn", "-w", "2", "-b", "0.0.0.0:8003", "run.wsgi:application"]
