Key Master
==========
An Arduino based RFID/NFC door access system that sends users welcome information to LED signs in the hackerspace, as well as pinging the future hackerspace website to count user visits to the space.

Features
--------
* Use any RFID/NFC device to check-in to a hack session.
* Sends a welcome message to an LED display.
* POSTs info to the [hackadl.org](http://hackadl.org) website.

Hardware
--------
* ACR122 Contactless Reader

Software
--------
* Python

RaspberryPi
----

When running on a Raspberri Pi, you need to install these:

<code>$ sudo apt-get install python-pyscard</code><br />
<code>$ sudo apt-get install pcscd</code><br />
<code>$ sudo apt-get install pcsc-tools</code>

If the reader isn't showing up, solve it using this:
http://enjoy-rfid.blogspot.com.au/2015/03/raspberry-pi-nfc.html

Which gets you to create a blacklist file:
<code>/etc/modprobe.d/raspi-blacklist.conf</code>

	blacklist pn533
	blacklist nfc
	
**Wifi**

To use a TP-Link TL-WN322G Wifi USB, install:

<code>$ sudo apt-get install zd1211-firmware</code>

Then add the wireless hotspot information by running:

<code>$ wpa_passphrase ssid-name passphrase > tmp.txt</code>

<code>$ sudo wpa_supplicant -B -i wlan0 -c tmp.txt</code>

You might need to restart the Pi, but it should be able to connect then.

**Wifi - connect to multiple networks**

If you'd like your pi to connect to home/work/hackerspace networks, you'll need to use a wpa-roam setup.

The two files you need to edit are <code>/etc/network/interfaces</code> and <code>/etc/wpa_supplicant/wpa_supplicant.conf</code>

	# /etc/network/interfaces
	
	auto lo
	iface lo inet loopback
	iface eth0 inet dhcp

	allow-hotplug wlan0
	iface wlan0 inet manual
	wpa-roam /etc/wpa_supplicant/wpa_supplicant.conf

	iface networkName1 inet dhcp
	iface networkName2 inet dhcp

And then use the same names here:

	# /etc/wpa_supplicant/wpa_supplicant.conf
	
	ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
	update_config=1

	network={
	    ssid="funnySSID"
	    psk="superSekret"
	    id_str="networkName1"
	}

	network={
	    ssid="workSSID"
	    psk="suuuuuuperSekret"
	    id_str="networkName2"
	}
	
Restart the Pi and it should auto-connect to the network.

**GPIO pins**

Using *wiringpi2*

<code>$ sudo apt-get install python-dev python-pip</code>

<code>$ sudo pip install wiringpi2</code>

Then with the RaspberryPi pointing with the SD card to the top, connect the buzzer to:

* Ground to the third pin down from the top on the right column.
* Power to the eighth pin down from the top on the right column.

Run the Hackerspace card reader on boot
---

To get this script to run at boot, add the following line to <code>/etc/rc.local</code>

<code>echo -n 'p\nc\n' | python /home/pi/hackerspace/Key-Master/keymaster.py | logger -t keymaster &</code>

The ```echo``` command enters 'p' for production, and 'c' for checkin.
It then tries to run the python script, and output that to logger with the tag 'keymaster'. The ```&``` symbol makes it run in the background.


Who
---

By [Pix](https://twitter.com/xiq) & [Simon](https://twitter.com/sighmon).

[Read more on the wiki](http://hackerspace-adelaide.org.au/wiki/Key_Master)
