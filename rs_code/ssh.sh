#!/bin/bash

# example: bash /mnt/glusterfs/ssh.sh 172.16.0.96 'touch /mnt/glusterfs/a.txt'

sshpass -p 'nydsj888999' ssh chronos@$1 $2 
