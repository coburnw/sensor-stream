# systemd-app-manager
simple bash script menu for managing a service in systemd

a bash menu to help manage an apps systemd unit configuration file

To use as a python app template, clone this repository
then delete the .git folder removing all history, then git init to
start your new app.

The included .gitignore is configured to ignore the lib directory and
its contents.  I find that cloning python libraries into the lib directory
works out well as the libraries are easily included from my app, yet
not tracked by my apps git instance.