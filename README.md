# CPU-Name
Small py script to change your CPU name if it shows as Unknown in About This Mac

To install, do the following one line at a time in Terminal:

    git clone https://github.com/corpnewt/CPU-Name
    cd CPU-Name
    chmod +x CPU-Name.command
    
Then run with either `./CPU-Name.command` or by double-clicking *CPU-Name.command*

## Instructions for macOS Big Sur (11.0 Beta)
System Integrity Protection (SIP) has to be temporarily disabled for your Mac/Hackintosh.

1. Reboot to Recovery, start Terminal and run:

    csrutil disable
    reboot
    
3. In macOS open Terminal, navigate to this repo's folder and run:

    sudo mount -uw /
    chmod +x CPU-Name.command
    ./CPU-Name.command
   
4. Reboot to Recovery, start Terminal and run:

    csrutil clear
    csrutil enable
    reboot
