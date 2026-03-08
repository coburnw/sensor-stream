#!/bin/bash
service="mud_phish"

# choose user or system control
systemctl="systemctl --user"
systemd=~/.config/systemd/user

#systemctl="systemctl --system"
#systemd="/usr/lib/systemd/system"

echo "systemd user $service.service unit manager"
echo
echo "https://github.com/torfsen/python-systemd-tutorial"
echo "https://wiki.archlinux.org/index.php/Systemd"
echo
OPTIONS="install edit show-linger linger-on reload enable disable start stop status log quit"

select choice in $OPTIONS; do
    if [ "$choice" = "edit" ]; then
        # edit service file
        cmd="nano $systemd/$service.service"
	echo $cmd
	$cmd
    
    elif [ "$choice" = "install" ]; then
        # transfer the service file to systemd's control
	#ln -s “$service.service” /etc/systemd/system/$service.service
        cmd="cp $service.service $systemd"
	echo $cmd
	$cmd

    elif [ "$choice" = "show-linger" ]; then
        # allow user.service to start on boot without login
	# not applicable to system.service
        cmd="loginctl --property=Linger show-user $USER"
	echo $cmd
	$cmd
	
    elif [ "$choice" = "linger-on" ]; then
        # allow user.service to start on boot without login
	# not applicable to system.service
        cmd="loginctl enable-linger"
	echo $cmd
	$cmd
	
    elif [ "$choice" = "linger-off" ]; then
        # allow user.service to start on boot without login
	# not applicable to system.service
        cmd="loginctl disable-linger"
	echo $cmd
	$cmd
	
    elif [ "$choice" = "reload" ]; then
	# reload service file after edit
	cmd="$systemctl daemon-reload"
	echo $cmd
	$cmd

    elif [ "$choice" = "enable" ]; then
	# enable service
	cmd="$systemctl enable $service.service"
	echo $cmd
	$cmd

    elif [ "$choice" = "disable" ]; then
	# disable service
	cmd="$systemctl disable $service.service"
	echo $cmd
	$cmd

    elif [ "$choice" = "start" ]; then
	# start it up
	cmd="$systemctl start $service.service"
	echo $cmd
	$cmd

    elif [ "$choice" = "stop" ]; then
	# stop it
	cmd="$systemctl stop $service.service"
	echo $cmd
	$cmd

    elif [ "$choice" = "status" ]; then
	#check status
	cmd="$systemctl status $service.service"
	echo $cmd
	$cmd

    elif [ "$choice" = "log" ]; then
	# view log
	cmd="journalctl --user-unit $service"
	echo $cmd
	$cmd

    elif [ "$choice" = "quit" ]; then
	echo "Done"
	exit
    fi
done
