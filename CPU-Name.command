#!/usr/bin/env python
from Scripts import *
import sys, os, time, tempfile, shutil
try:
    from Queue import Queue, Empty
except:
    from queue import Queue, Empty

class CPUName:

    def __init__(self):
        self.r = run.Run()
        self.u = utils.Utils("CPU-Name")
        # Check the OS first
        if not str(sys.platform) == "darwin":
            self.u.head("Incompatible System")
            print(" ")
            print("This script can only be run from macOS/OS X.")
            print(" ")
            print("The current running system is \"{}\".".format(sys.platform))
            print(" ")
            self.u.grab("Press [enter] to quit...")
            print(" ")
            exit(1)

        # Set up a dict that has the normalized languages
        # and their locale codes
        self.l_dict   = {
            "nl_US" : "Dutch",
            "en_US" : "English",
            "fr_US" : "French",
            "de_US" : "German",
            "it_US" : "Italian",
            "ja_US" : "Japanese",
            "es_US" : "Spanish"
        }
        self.lang     = self._get_locale()
        self.str_path = "/System/Library/PrivateFrameworks/AppleSystemInfo.framework/Versions/A/Resources/"
        self.file_n   = "AppleSystemInfo.strings"
        self.sip_checked = False

    def _get_locale(self):
        # Runs an applescript to determine the current system locale
        locale = self.r.run({"args":["defaults","read",".GlobalPreferences","AppleLanguages"]})[0].strip()
        # This will be a list of languages, we need to cut it up and get the top one
        try:
            # Get the top item of the list between quotes, and convert - to _
            locale = locale.split("\n")[1].split('"')[1].replace("-","_")
        except:
            # Not found - default to English
            return "English"
        # Returns the normalized locale if in the l_dict - or the returned locale
        return self.l_dict.get(locale,locale)

    def _p(self, text):
        # Attempts to print unicode chars safely... attempts...
        if sys.version_info >= (3, 0):
            if isinstance(text, bytes):
                text = text.decode("utf-8")
        else:
            if isinstance(text, (str,unicode)):
                text = text.encode("utf-8")
        return text

    def _get_lproj(self, lang_name):
        # Returns the lang_name.lproj if it exists
        lang_name = os.path.basename(os.path.normpath(os.path.abspath(lang_name)))
        if os.path.exists(os.path.join(self.str_path, lang_name)):
            # Exists
            return os.path.join(self.str_path, lang_name)
        lang_name += ".lproj"
        if os.path.exists(os.path.join(self.str_path, lang_name)):
            # Exists with .lproj extension
            return os.path.join(self.str_path, lang_name)
        return None

    def _get_cpu_name(self):
        # Gets the cpu name via sysctl
        output = self.r.run({"args" : ["sysctl", "-n", "machdep.cpu.brand_string"]})
        if output[2] == 0:
            return output[0].replace("\n", "")
        return None

    def _get_plist_dict(self, path):
        # Returns a dict of the plist data as a dict
        if not os.path.exists(path):
            return None
        # Load it with the plist module
        try:
            with open(path,"rb") as f:
                d = plist.load(f)
            return d
        except:
            return None

    def check_sip(self):
        # Checks our sip status and warns if needed
        sip_stats = self.r.run({"args" : ["csrutil", "status"]})[0]
        msg = "Unknown SIP Configuration!\n"
        title = "Unknown"
        if not sip_stats.startswith("System Integrity Protection status:"):
            # Error getting SIP status
            return None
        if sip_stats.startswith("System Integrity Protection status: disabled."):
            # SIP is disabled - return true to imply we have the "go ahead"
            return True
        if sip_stats.startswith("System Integrity Protection status: enabled (Custom Configuration)."):
            # SIP is partially enabled - determine if fs protection and kext signing is disabled
            if "Filesystem Protections: disabled" in sip_stats and "Kext Signing: disabled" in sip_stats:
                # Still good - let's roll
                return True
            title = "Partially Disabled"
            msg = "SIP is only partially disabled!\nKext signing and/or fs protection are eanbled!\n"
            
        if sip_stats == "System Integrity Protection status: enabled.":
            # SIP is enabled completely
            title = "Enabled"
            msg = "System Integrity Protection is completely enabled!\n"
        self.u.head("SIP Is " + title)
        print(" ")
        print(msg)
        print("This may prevent this script's changes.")
        print(" ")
        menu = self.u.grab("Would you like to continue? (y/n):  ")

        if not len(menu):
            return self.check_sip()
        
        if menu[:1].lower() == "n":
            return False
        elif menu[:1].lower() == "y":
            return True

        return self.check_sip()

    def restore_backup(self):
        if not self.sip_checked:
            res = self.check_sip()
            if res == None or res == True:
                # Likely on Yosemite?
                self.sip_checked = True
            else:
                return

        self.u.head("Restoring Backup {}".format(self.file_n))
        print(" ")
        string_path = os.path.join(self._get_lproj(self.lang), self.file_n)
        bak_path    = string_path + ".bak"
        if not os.path.exists(bak_path):
            # Create a backup
            self.u.grab("Backup doesn't exist...",timeout=5)
            return
        # Doing things
        c = [
            { 
                "args" : ["rm", string_path], 
                "sudo" : True, 
                "message" : "Removing " + string_path + "...\n",
                "stream" : True
            },
            { 
                "args" : ["sudo", "mv", "-f", bak_path, string_path], 
                "sudo" : True,
                "message" : "Renaming {}.bak to {}...".format(self.file_n, self.file_n),
                "stream" : True
            }
        ]
        self.r.run(c, True)
        print(" ")
        self.u.grab("Done.",timeout=5)
        return

    def delete_backup(self):
        self.u.head("Deleting Backup {}".format(self.file_n))
        print(" ")
        string_path = os.path.join(self._get_lproj(self.lang), self.file_n + ".bak")
        if not os.path.exists(string_path):
            # Create a backup
            self.u.grab("Backup doesn't exist...",timeout=5)
            return
        # Removing
        print("Removing " + string_path + "...")
        self.r.run({"args":["rm", string_path],"sudo":True, "stream" : True})
        print(" ")
        self.u.grab("Done.",timeout=5)
        return

    def set_cpu(self, cpu):
        if not self.sip_checked:
            res = self.check_sip()
            if res == None or res == True:
                # Likely on Yosemite?
                self.sip_checked = True
            else:
                return

        self.u.head("Setting CPU to {}".format(self._p(cpu)))
        print(" ")
        os.chdir(os.path.dirname(os.path.realpath(__file__)))

        # Start our command list
        c = []
        try:
            string_path = os.path.join(self._get_lproj(self.lang), self.file_n)
            string_plist = self._get_plist_dict(string_path)
        except:
            string_plist = string_path = None

        if string_plist == None:
            self.u.grab("Failed to read {}...".format(self.file_n),timeout=5)
            return
        if not os.path.exists(string_path + ".bak"):
            # Create a backup
            self.r.run({
                "args" : ["cp", string_path, string_path+".bak"],
                "sudo" : True,
                "message" : "Creating backup...\n",
                "stream" : True
            })

        # Change the build number and write to the main plist
        print("Patching strings for CPU \"{}\"...".format(cpu))
        string_plist["UnknownCPUKind"] = cpu
        # Make a temp folder for our plist
        temp_folder = tempfile.mkdtemp()
        # Write the changes
        temp_file   = os.path.join(temp_folder, self.file_n)
        with open(temp_file, "wb") as f:
            plist.dump(string_plist, f)
        # Build and run commands
        c = [
            {
                "args" : ["mv", "-f", temp_file, string_path],
                "sudo" : True,
                "stream" : True
            }
        ]
        self.r.run(c, True)
        # Remove temp
        if os.path.exists(temp_folder):
            shutil.rmtree(temp_folder)
        print(" ")
        self.u.grab("Done.", timeout=5)
        return

    def main(self):
        self.u.head("CPU Name")
        print(" ")
        os.chdir(os.path.dirname(os.path.realpath(__file__)))

        cpu_name = self._get_cpu_name()

        print("Current Language:    {}\n".format(self.lang))
        try:
            string_path = os.path.join(self._get_lproj(self.lang), self.file_n)
            string_plist = self._get_plist_dict(string_path)
        except:
            string_path = string_plist = None
        if string_plist == None:
            if string_path and os.path.exists(string_path):
                print("{} is unreadable!".format(self.file_n))
            else:
                print("{} doesn't exist!".format(self.file_n))
        else:
            print("Current Unknown CPU: {}".format(self._p(string_plist["UnknownCPUKind"])))
        print(" ")

        if cpu_name:
            print("C. Use: {}".format(cpu_name))
        bak = False
        if string_path and os.path.exists(string_path+".bak"):
            bak = True
            print("D. Delete Backup")
            print("R. Restore Backup")
        print("Q. Quit")
        print(" ")
        menu = self.u.grab("Please enter a new CPU name - or a new language (must end in .lproj):  ")

        if not len(menu):
            return
        if menu.lower() == "q":
            self.u.custom_quit()
        elif menu.lower() == "d" and bak:
            self.delete_backup()
            return
        elif menu.lower() == "r" and bak:
            self.restore_backup()
            return
        elif menu.lower() == "c" and cpu_name:
            self.set_cpu(cpu_name)
            return
        # Check for lproj
        if menu.lower().endswith(".lproj"):
            test = ".".join(menu.split(".")[:-1])
            if not self._get_lproj(test):
                self.u.head("Language Not Found")
                print("")
                print("{} doesn't appear to exist.".format(menu))
                self.u.grab("",timeout=5)
                return
            self.lang = test
            return

        # Should be a new cpu
        self.set_cpu(menu)
        return

c = CPUName()

while True:
    try:
        c.main()
    except Exception as e:
        print(e)
        time.sleep(5)
