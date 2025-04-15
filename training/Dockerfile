FROM images.paas.redhat.com/genie/prompt_lab:latest

# Install necessary dependencies
RUN dnf update -y
RUN dnf install -y git procps-ng bash strace libstdc++    
#gmp-devel mpfr-devel libmpc-devel gcc gcc-c++ make libtool autoconf automake

#download and install screen 
RUN curl -O https://dl.fedoraproject.org/pub/epel/9/Everything/x86_64/Packages/s/screen-4.8.0-6.el9.x86_64.rpm
RUN dnf install -y screen-4.8.0-6.el9.x86_64.rpm && rm -rf screen-4.8.0-6.el9.x86_64.rpm
RUN chmod -R 777 /run/screen

#explicitly install cuda-toolkit
RUN dnf config-manager --add-repo http://developer.download.nvidia.com/compute/cuda/repos/rhel8/x86_64/cuda-rhel8.repo
RUN dnf clean all
RUN dnf install -y cuda-toolkit
RUN git clone --depth 1 https://github.com/hiyouga/LLaMA-Factory.git

#workaround in order to be able to run the llama-factory as the user here is root and our OC doesn't allow root containers
RUN mkdir /.cache
RUN chmod -R 777 /.cache
WORKDIR /app
#COPY api-server.py /app
ADD ./scripts/entrypoint.py .
ADD ./scripts/api-server.py .
ADD ./scripts/templates ./templates
#RUN chmod 777 ./entrypoint.py
RUN chmod -R 777 *
WORKDIR /app/LLaMA-Factory


#Install deps in a virtual environment
ENV VIRTUAL_ENV=/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN pip install --upgrade pip
# Install PyTorch first (make sure it's compatible with your CUDA version)
RUN pip install torch torchvision torchaudio
RUN pip install -e ".[torch,metrics]"
RUN pip install wheel nvitop liger-kernel hf_transfer bitsandbytes huggingface_hub gunicorn Jinja2
RUN pip install flash-attn --no-build-isolation

EXPOSE 7860
EXPOSE 8080
# Set entrypoint
ENTRYPOINT ["gunicorn --daemon -w 4 -b 0.0.0.0:8080 api-server:app --chdir /app && python /app/entrypoint.py"]
#ENTRYPOINT ["bash"]
