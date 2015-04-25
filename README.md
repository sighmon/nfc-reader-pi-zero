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

Who
---

By [Pix](https://twitter.com/xiq) & [Simon](https://twitter.com/sighmon).

[Read more on the wiki](http://hackerspace-adelaide.org.au/wiki/Key_Master)
