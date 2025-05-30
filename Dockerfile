# Use the official Ubuntu 22.04 LTS as a base image
FROM ubuntu:22.04

# Set DEBIAN_FRONTEND to noninteractive to avoid prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

# Install Python 3.10 and required dependencies
RUN apt-get update && apt-get install -y python3.10 python3.10-venv python3.10-dev python3-pip gnupg software-properties-common qgis cmake openmpi-bin openmpi-common openssh-client openssh-server libopenmpi-dev unzip nano imagemagick libmagickwand-dev gdal-bin libgdal-dev python3-gdal ffmpeg cdo

# Install the Python package cjfx
RUN pip3 install hydroeval wand cython
RUN pip3 install matplotlib
RUN pip3 install cjfx
RUN pip3 install netcdf4 fiona
RUN pip3 install numpy==1.23.4 pandas==1.5.3 xarray==2022.12.0 matplotlib==3.6.3 rasterio==1.3.4
RUN pip3 install ccfx

# Set Python 3.10 as the default python3
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1

RUN wget https://celray.chawanda.com/assets/downloads/swatplus-linux.tgz -O /tmp/swatplus-linux.tgz
RUN mkdir -p /tmp/swatplus-linux/
RUN tar -xvzf /tmp/swatplus-linux.tgz -C /tmp/swatplus-linux/
RUN cd /tmp/swatplus-linux/ && ./installforme.sh

# because we really do not have a monitor and we need to simulate display
ENV QT_QPA_PLATFORM=offscreen
RUN echo 'export XDG_RUNTIME_DIR=/tmp/runtime-root' >> ~/.bashrc
RUN mkdir -p /tmp/runtime-root
RUN chmod 700 /tmp/runtime-root

ENV OMPI_ALLOW_RUN_AS_ROOT=1
ENV OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1

# Copy the CoSWAT-Global-Model folder into the Docker image
RUN mkdir -p /CoSWAT-Global-Model/data-preparation/resources
COPY data-preparation/resources /CoSWAT-Global-Model/data-preparation/resources

# unzip the regions and QSWATPlus zip files. If exists, remove the existing directories first.
RUN if [ -d "/CoSWAT-Global-Model/data-preparation/resources/regions" ]; then rm -rf /CoSWAT-Global-Model/data-preparation/resources/regions; fi
RUN if [ -d "/CoSWAT-Global-Model/data-preparation/resources/QSWATPlus" ]; then rm -rf /CoSWAT-Global-Model/data-preparation/resources/QSWATPlus; fi

RUN unzip /CoSWAT-Global-Model/data-preparation/resources/regions.zip -d /CoSWAT-Global-Model/data-preparation/resources
RUN unzip /CoSWAT-Global-Model/data-preparation/resources/QSWATPlus.zip -d /CoSWAT-Global-Model/data-preparation/resources

# add paths to path and pythonpath in bashrc
RUN echo 'export PATH=$PATH:/CoSWAT-Global-Model' >> ~/.bashrc
RUN echo 'export PYTHONPATH=$PYTHONPATH:/CoSWAT-Global-Model' >> ~/.bashrc
RUN echo 'export PATH=$PATH:/CoSWAT-Global-Model/data-preparation' >> ~/.bashrc 
RUN echo 'export PYTHONPATH=$PYTHONPATH:/CoSWAT-Global-Model/data-preparation' >> ~/.bashrc
RUN echo 'export PATH=$PATH:/CoSWAT-Global-Model/main-scripts' >> ~/.bashrc 
RUN echo 'export PYTHONPATH=$PYTHONPATH:/CoSWAT-Global-Model/main-scripts' >> ~/.bashrc

RUN cp /root/.local/share/SWATPlus/SWATPlusEditor/resources/app.asar.unpacked/static/api_dist/swatplus_api /CoSWAT-Global-Model/data-preparation/resources/swatplus_api

# set executable
RUN chmod +x /CoSWAT-Global-Model/data-preparation/resources/swatplus_api
RUN chmod +x /CoSWAT-Global-Model/data-preparation/*


# Create entrypoint script
RUN echo '#!/bin/bash\n\
if [ -d "/CoSWAT-Global-Model/main-scripts" ] && [ "$(ls -A /CoSWAT-Global-Model/main-scripts/ 2>/dev/null)" ]; then\n\
  chmod +x /CoSWAT-Global-Model/main-scripts/*\n\
  echo "made scripts in main-scripts executable"\n\
fi\n\
exec "$@"' > /entrypoint.sh

# Make the entrypoint script executable
RUN chmod +x /entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Set the default command to run when the container starts
CMD ["bash"]
