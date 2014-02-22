#!/bin/bash
#############################################
# 1) Disable SELINUX if required.
# 2) Set swappiness to minimum
# 3) Disable not-required services.
# 4) Download and install mysql connector
# 5) Un-mount /mnt mounting point and remove it from fstab.
# 6) Go through all the different drives, create the FS and mount them
# 7) Configure NTP
#############################################


#############################################
# Distribution automatic detection
echo Distribution detection > init_script.log
REDHAT=false
DEBIAN=false
if [ -f /etc/redhat-release ]; then REDHAT=true; fi
if [ -f /etc/os-release ]; then DEBIAN=true; fi
if $REDHAT; then
  echo RedHat detected >> init_script.log
fi
if $DEBIAN; then
  echo Debian/Ubuntu detected >> init_script.log
fi
if ((! $REDHAT && ! $DEBIAN) || ($REDHAT && $DEBIAN)); then 
  echo Impossible to identify linux distribution. >> init_script.log
  echo Please check and adjust the script. >> init_script.log
  #exit
fi
#############################################


#############################################
# (RedHat) Disable SELINUX
if $REDHAT; then
  echo Disable SELINUX >> init_script.log
  sed -e 's/^SELINUX=enforcing/SELINUX=disabled/' -i /etc/selinux/config >> init_script.log
  sed -e 's/^SELINUX=permissive/SELINUX=disabled/' -i /etc/selinux/config >> init_script.log
fi

# (Ubuntu) Disable SELINUX
# Not required.
#############################################



#############################################
# Set swappiness to minimum
echo Turn swappiness to minimum >> init_script.log
sh -c 'echo "vm.swappiness = 0" >> /etc/sysctl.conf'
#############################################



#############################################
# (RedHat) Disable some not-required services.
if $REDHAT; then
  echo Disable/enable required services >> init_script.log
  chkconfig cups off
  chkconfig postfix off
  chkconfig iptables off
  chkconfig ip6tables off
fi

# (Ubuntu) Disable some not-required services
# Not required.
#############################################



#############################################
# Download and install mysql connector
echo Donwload and install mysql connector >> init_script.log
wget -O mysql-connector-java-5.1.28.tar.gz http://dev.mysql.com/get/Downloads/Connector-J/mysql-connector-java-5.1.28.tar.gz
tar xzf mysql-connector-java-5.1.28.tar.gz
cp mysql-connector-java-5.1.28/mysql-con	nector-java-5.1.28-bin.jar /usr/share/java/mysql-connector-java.jar
rm -rf mysql-connector-java-5.1.28*
#############################################



#############################################
# (RedHat) Un-mount /mnt mounting point and remove it from fstab.
if $REDHAT; then
  echo Clear already mounted drive >> init_script.log
  umount /mnt
  cat /etc/fstab | grep -v "/mnt" > /tmp/fstab.new
  mv /tmp/fstab.new /etc/fstab
fi

# (Ubuntu) Un-mount /mnt mounting point and remove it from fstab. 
if $DEBIAN; then
  echo Clear already mounted drive >> init_script.log
  umount /mnt
  cat /etc/fstab | grep -v "/mnt" > /tmp/fstab.new
  mv /tmp/fstab.new /etc/fstab
fi
#############################################



#############################################
# Go through all the different drives, create the FS and mount them
echo Create and mount all available block devices. >> init_script.log
counter=1
one=1
for i in `ls /dev/xv* | grep -v xvda | grep -v 1 | cut -d"/" -f3`; do
  echo Create and mount $i >> init_script.log
  echo Create partition on /dev/$i >> init_script.log
  (echo o; echo n; echo p; echo 1; echo; echo; echo w) | fdisk /dev/$i &>> init_script.err
  echo Create file system on /dev/$i$one >> init_script.log
  mkfs.ext4 -m 0 /dev/$i$one &>> init_script.err
  echo Create mount point /dev/$i$one in /data/$counter >> init_script.log
  mkdir -p /data/$counter  >> init_script.err
  echo Update of fstab script  >> init_script.log
  mountline="/dev/$i$one /data/$counter ext4 noatime 0 0"
  sh -c "echo $mountline >> /etc/fstab" >> init_script.err
  counter=`expr $counter + 1`
done
mount -a
#############################################


#############################################
# (RedHat) Ensure NTPDate is turned on
if $REDHAT; then
  chkconfig ntpd on
fi

# (Ubuntu) Ensure NPTDate is on the cron file.
if $DEBIAN; then
  (crontab -l ; echo "0 0    * * *   root    /usr/sbin/ntpdate-debian") | crontab -
fi
#############################################

#############################################
# Resize root partition
start_block=`echo p | fdisk /dev/xvda | grep /dev/xvda1 | awk {'print $2'}`

(echo d; echo n; echo p; echo 1; echo $start_block; echo; echo w;) | fdisk /dev/xvda

#############################################
# Output log for completion
touch /tmp/init-complete
echo Initialisation completed on this node >> init_script.log
#############################################
