# CPU-Name
Small py script to change your CPU name if it shows as Unknown in About This Mac

To install, do the following one line at a time in Terminal:

    git clone https://github.com/corpnewt/CPU-Name
    cd CPU-Name
    chmod +x CPU-Name.command
    
Then run with either `./CPU-Name.command` or by double-clicking *CPU-Name.command*

# macOS Big Sur (11.0 Beta)
System Integrity Protection (SIP) has to be temporarily disabled for your Mac/Hackintosh.

1. Reboot to Recovery and run the Terminal and enter `csrutil disable` and run `reboot`.
3. Open Terminal and run `sudo mount -uw /`
4. Navigate to this repo's folder and run `chmod +x CPU-Name.command`
4. Run `./CPU-Name.command`
5. Reboot to Recovery and run the Terminal and enter `csrutil clear` and then enter `csrutil enable`.

