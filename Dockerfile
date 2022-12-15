# syntax=docker/dockerfile:1
FROM ubuntu
# FROM yukinying/chrome-headless-browser-selenium
# RUN adduser -D baeldung
# USER baeldung
WORKDIR /scraping_flask
# RUN apt-get update && apt-get install -y apt-transport-https
# RUN echo 'deb http://private-repo-1.hortonworks.com/HDP/ubuntu14/2.x/updates/2.4.2.0 HDP main' >> /etc/apt/sources.list.d/HDP.list
# RUN echo 'deb http://private-repo-1.hortonworks.com/HDP-UTILS-1.1.0.20/repos/ubuntu14 HDP-UTILS main'  >> /etc/apt/sources.list.d/HDP.list
# RUN echo 'deb [arch=amd64] https://apt-mo.trafficmanager.net/repos/azurecore/ trusty main' >> /etc/apt/sources.list.d/azure-public-trusty.list
RUN apt-get update
RUN apt-get -y install sudo
RUN apt-get install -y wget
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
RUN apt-get install -y ./google-chrome-stable_current_amd64.deb
# RUN sudo apt install google-chrome-stable
# RUN useradd -ms /selenium_docker newuser
# USER newuser
# RUN sudo chown "$USER":"$USER" /home/"$USER"/.docker -R
# RUN sudo chmod g+rwx "$HOME/.docker" -R
# RUN apt-get -y install sudo
# RUN apt-get -qq -y install curl
RUN apt-get install -y wget
RUN apt-get update && apt-get install -y gnupg
# RUN useradd -m docker && echo "docker:docker" | chpasswd && adduser docker sudo
# USER docker
# # CMD /bin/bash
# # RUN apt-get -y install curl
# RUN wget -nc https://dl-ssl.google.com/linux/linux_signing_key.pub
# RUN cat linux_signing_key.pub | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/linux_signing_key.gpg  >/dev/null
# RUN sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/chrome.list'
# RUN sudo apt update
# RUN sudo apt install google-chrome-stable
# RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
#     && echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list
# RUN apt-get update && apt-get -y install google-chrome-stable
# RUN sudo apt-get install -y whatever
RUN sudo apt install -y python3-pip
# RUN apt-get update && apt-get install -y \
    # php5-mcrypt \
    # python3-pip
RUN python3 -m pip install --upgrade pip
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .

CMD ["python3", "app.py"]
EXPOSE 5000
