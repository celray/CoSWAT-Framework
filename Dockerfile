# Use the official Ubuntu 22.04 LTS as a base image
FROM ubuntu:22.04

# Set DEBIAN_FRONTEND to noninteractive to avoid prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

# Install Python 3.10 and required dependencies
RUN apt-get update && apt-get install -y sudo ca-certificates python3.10 python3.10-venv python3.10-dev python3-pip gnupg software-properties-common qgis cmake openmpi-bin openmpi-common openssh-client openssh-server libopenmpi-dev unzip nano imagemagick libmagickwand-dev gdal-bin libgdal-dev python3-gdal ffmpeg cdo

# Install the Python package cjfx
RUN pip3 install hydroeval wand cython
RUN pip3 install matplotlib
RUN pip3 install cjfx
RUN pip3 install netcdf4 fiona
RUN pip3 install ccfx
RUN pip3 install numpy==1.23.4
RUN pip3 install pandas==1.5.3 xarray==2022.12.0 matplotlib==3.6.3 rasterio==1.3.4 numexpr==2.8.4 bottleneck==1.3.6
RUN pip3 install numpy==1.23.4

# Set Python 3.10 as the default python3
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1

# Create user with sudo privileges
ARG USERNAME=developer
ARG UID=1000
ARG GID=1000

# Create group/user, unlock account, grant passwordless sudo
RUN groupadd -g $GID $USERNAME || true \
 && useradd -m -u $UID -g $GID -s /bin/bash $USERNAME || true \
 && usermod -U $USERNAME \
 && install -m 0440 /dev/stdin /etc/sudoers.d/90-$USERNAME <<EOF
$USERNAME ALL=(ALL) NOPASSWD:ALL
EOF

RUN wget https://celray.chawanda.com/assets/downloads/swatplus-linux.tgz -O /tmp/swatplus-linux.tgz
RUN mkdir -p /tmp/swatplus-linux/
RUN tar -xvzf /tmp/swatplus-linux.tgz -C /tmp/swatplus-linux/
RUN cd /tmp/swatplus-linux/ && ./installforme.sh

# because we really do not have a monitor and we need to simulate display
ENV QT_QPA_PLATFORM=offscreen
RUN echo 'export XDG_RUNTIME_DIR=/tmp/runtime-$USERNAME' >> /home/$USERNAME/.bashrc
RUN mkdir -p /tmp/runtime-$USERNAME
RUN chmod 700 /tmp/runtime-$USERNAME
RUN chown $USERNAME:$USERNAME /tmp/runtime-$USERNAME

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
RUN echo 'export PATH=$PATH:/CoSWAT-Global-Model' >> /home/$USERNAME/.bashrc
RUN echo 'export PYTHONPATH=$PYTHONPATH:/CoSWAT-Global-Model' >> /home/$USERNAME/.bashrc
RUN echo 'export PATH=$PATH:/CoSWAT-Global-Model/data-preparation' >> /home/$USERNAME/.bashrc 
RUN echo 'export PYTHONPATH=$PYTHONPATH:/CoSWAT-Global-Model/data-preparation' >> /home/$USERNAME/.bashrc
RUN echo 'export PATH=$PATH:/CoSWAT-Global-Model/main-scripts' >> /home/$USERNAME/.bashrc 
RUN echo 'export PYTHONPATH=$PYTHONPATH:/CoSWAT-Global-Model/main-scripts' >> /home/$USERNAME/.bashrc
RUN echo 'export PYTHONDONTWRITEBYTECODE=1' >> /home/$USERNAME/.bashrc    # removes __pycache__ directories at the expense of start up overhead

# Copy SWAT+ files to user accessible locations
RUN mkdir -p /home/$USERNAME/.local/share/SWATPlus/Databases
RUN mkdir -p /home/$USERNAME/.local/share/QGIS/QGIS3/profiles/default/python/plugins/QSWATPlusLinux3_64/QSWATPlus
RUN cp -r /root/.local/share/SWATPlus/* /home/$USERNAME/.local/share/SWATPlus/
RUN cp -r /root/.local/share/QGIS/* /home/$USERNAME/.local/share/QGIS/
RUN chown -R $USERNAME:$USERNAME /home/$USERNAME/.local

# RUN cp /root/.local/share/SWATPlus/SWATPlusEditor/resources/app.asar.unpacked/static/api_dist/swatplus_api /CoSWAT-Global-Model/data-preparation/resources/swatplus_api
RUN rm /home/$USERNAME/.local/share/SWATPlus/Databases/swatplus_datasets.sqlite
RUN cp /CoSWAT-Global-Model/data-preparation/resources/swatplus_datasets.sqlite /home/$USERNAME/.local/share/SWATPlus/Databases/swatplus_datasets.sqlite


RUN cp /home/$USERNAME/.local/share/QGIS/QGIS3/profiles/default/python/plugins/QSWATPlusLinux3_64/QSWATPlus/polygonizeInC.cpython-310-x86_64-linux-gnu.so /CoSWAT-Global-Model/data-preparation/resources/QSWATPlus/polygonizeInC.cpython-310-x86_64-linux-gnu.so
RUN cp /home/$USERNAME/.local/share/QGIS/QGIS3/profiles/default/python/plugins/QSWATPlusLinux3_64/QSWATPlus/polygonizeInC.cpython-311-x86_64-linux-gnu.so /CoSWAT-Global-Model/data-preparation/resources/QSWATPlus/polygonizeInC.cpython-311-x86_64-linux-gnu.so

RUN cp /home/$USERNAME/.local/share/QGIS/QGIS3/profiles/default/python/plugins/QSWATPlusLinux3_64/QSWATPlus/dataInC.cpython-310-x86_64-linux-gnu.so /CoSWAT-Global-Model/data-preparation/resources/QSWATPlus/dataInC.cpython-310-x86_64-linux-gnu.so
RUN cp /home/$USERNAME/.local/share/QGIS/QGIS3/profiles/default/python/plugins/QSWATPlusLinux3_64/QSWATPlus/dataInC.cpython-311-x86_64-linux-gnu.so /CoSWAT-Global-Model/data-preparation/resources/QSWATPlus/dataInC.cpython-311-x86_64-linux-gnu.so

RUN cp /home/$USERNAME/.local/share/QGIS/QGIS3/profiles/default/python/plugins/QSWATPlusLinux3_64/QSWATPlus/jenks.cpython-310-x86_64-linux-gnu.so /CoSWAT-Global-Model/data-preparation/resources/QSWATPlus/jenks.cpython-310-x86_64-linux-gnu.so
RUN cp /home/$USERNAME/.local/share/QGIS/QGIS3/profiles/default/python/plugins/QSWATPlusLinux3_64/QSWATPlus/jenks.cpython-311-x86_64-linux-gnu.so /CoSWAT-Global-Model/data-preparation/resources/QSWATPlus/jenks.cpython-311-x86_64-linux-gnu.so

RUN cp /home/$USERNAME/.local/share/QGIS/QGIS3/profiles/default/python/plugins/QSWATPlusLinux3_64/QSWATPlus/polygonizeInC2.cpython-310-x86_64-linux-gnu.so /CoSWAT-Global-Model/data-preparation/resources/QSWATPlus/polygonizeInC2.cpython-310-x86_64-linux-gnu.so
RUN cp /home/$USERNAME/.local/share/QGIS/QGIS3/profiles/default/python/plugins/QSWATPlusLinux3_64/QSWATPlus/polygonizeInC2.cpython-311-x86_64-linux-gnu.so /CoSWAT-Global-Model/data-preparation/resources/QSWATPlus/polygonizeInC2.cpython-311-x86_64-linux-gnu.so

# Set ownership and permissions for CoSWAT directory
RUN chown -R $USERNAME:$USERNAME /CoSWAT-Global-Model

# set executable
RUN chmod +x /CoSWAT-Global-Model/data-preparation/resources/swatplus_api
RUN chmod +x /CoSWAT-Global-Model/data-preparation/*

# Set working directory
WORKDIR /CoSWAT-Global-Model

# Create entrypoint script
RUN echo '#!/bin/bash\n\
if [ -d "/CoSWAT-Global-Model/main-scripts" ] && [ "$(ls -A /CoSWAT-Global-Model/main-scripts/ 2>/dev/null)" ]; then\n\
  chmod +x /CoSWAT-Global-Model/main-scripts/*\n\
  echo "made scripts in main-scripts executable"\n\
fi\n\
if [ -d "/CoSWAT-Global-Model/data-preparation" ] && [ "$(ls -A /CoSWAT-Global-Model/data-preparation/ 2>/dev/null)" ]; then\n\
  chmod +x /CoSWAT-Global-Model/data-preparation/*\n\
  echo "made scripts in data-preparation executable"\n\
fi\n\
exec "$@"' > /entrypoint.sh

# Make the entrypoint script executable
RUN chmod +x /entrypoint.sh

# Switch to non-root user
USER $USERNAME

# Set the entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Set the default command to run when the container starts
CMD ["bash"]
