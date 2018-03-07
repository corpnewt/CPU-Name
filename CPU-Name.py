import plistlib
import sys
import os
import time
import tempfile
import shutil
import subprocess
import re
import threading
try:
    from Queue import Queue, Empty
except:
    from queue import Queue, Empty
# Python-aware urllib stuff
if sys.version_info >= (3, 0):
    from urllib.request import urlopen
else:
    from urllib2 import urlopen

class CPUName:

    def __init__(self):

        # Check the OS first
        if not str(sys.platform) == "darwin":
            self.head("Incompatible System")
            print(" ")
            print("This script can only be run from macOS/OS X.")
            print(" ")
            print("The current running system is \"{}\".".format(sys.platform))
            print(" ")
            self.grab("Press [enter] to quit...")
            print(" ")
            exit(1)

        self.lang     = "English" # this is the name before the .lproj
        self.str_path = "/System/Library/PrivateFrameworks/AppleSystemInfo.framework/Versions/A/Resources/"
        self.file_n   = "AppleSystemInfo.strings"

        self.sip_checked = False

        # Populate our "strings file" with the default contents
        # self.strings  = plistlib.readPlist(self._get_lproj(self.lang))

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

    def _read_output(self, pipe, q):
        while True:
            try:
                c = pipe.read(1)
                q.put(c)
            except ValueError:
                break

    def _get_cpu_name(self):
        # Gets the cpu name via sysctl
        output = self.run({"args" : ["sysctl", "-n", "machdep.cpu.brand_string"]})
        if output[2] == 0:
            return output[0].replace("\n", "")
        return None

    def _stream_output(self, comm, shell = False):
        output = error = ""
        p = ot = et = None
        try:
            if shell and type(comm) is list:
                comm = " ".join(comm)
            if not shell and type(comm) is str:
                comm = comm.split()
            p = subprocess.Popen(comm, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1, universal_newlines=True)
            # Threading!
            oq, eq = Queue(), Queue()
            ot = threading.Thread(target=self._read_output, args=(p.stdout, oq))
            et = threading.Thread(target=self._read_output, args=(p.stderr, eq))
            ot.daemon, et.daemon = True, True
            ot.start()
            et.start()

            while True:
                c = z = None
                try:
                    c = oq.get_nowait()
                    output += c
                    sys.stdout.write(c)
                except Empty:
                    pass
                try:
                    z = eq.get_nowait()
                    error += z
                    sys.stdout.write(z)
                except Empty:
                    pass
                sys.stdout.flush()
                p.poll()
                if not c and not z and p.returncode is not None:
                    break
            o, e = p.communicate()
            ot.exit()
            et.exit()
            return (output+o, error+e, p.returncode)
        except:
            if ot or et:
                try: ot.exit()
                except: pass
                try: et.exit()
                except: pass
            if p:
                return (output, error, p.returncode)
            return ("", "Command not found!", 1)

    def _run_command(self, comm, shell = False):
        c = None
        try:
            if shell and type(comm) is list:
                comm = " ".join(comm)
            if not shell and type(comm) is str:
                comm = comm.split()
            p = subprocess.Popen(comm, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            c = p.communicate()
            return (c[0].decode("utf-8"), c[1].decode("utf-8"), p.returncode)
        except:
            if c == None:
                return ("", "Command not found!", 1)
            return (c[0].decode("utf-8"), c[1].decode("utf-8"), p.returncode)

    def run(self, command_list, leave_on_fail = False):
        # Command list should be an array of dicts
        if type(command_list) is dict:
            # We only have one command
            command_list = [command_list]
        output_list = []
        for comm in command_list:
            args   = comm.get("args",   [])
            shell  = comm.get("shell",  False)
            stream = comm.get("stream", False)
            sudo   = comm.get("sudo",   False)
            stdout = comm.get("stdout", False)
            stderr = comm.get("stderr", False)
            mess   = comm.get("message", None)
            
            if not mess == None:
                print(mess)

            if not len(args):
                # nothing to process
                continue
            if sudo:
                # Check if we have sudo
                out = self._run_command(["which", "sudo"])
                if "sudo" in out[0]:
                    # Can sudo
                    args.insert(0, "sudo")
            
            if stream:
                # Stream it!
                out = self._stream_output(args, shell)
            else:
                # Just run and gather output
                out = self._run_command(args, shell)
                if stdout and len(out[0]):
                    print(out[0])
                if stderr and len(out[1]):
                    print(out[1])
            # Append output
            if type(out) is str:
                # We streamed - assume success?
                out = ( out, "", 0 )
            output_list.append(out)
            # Check for errors
            if leave_on_fail and out[2] != 0:
                # Got an error - leave
                break
        if len(output_list) == 1:
            # We only ran one command - just return that output
            return output_list[0]
        return output_list

    def check_sip(self):
        # Checks our sip status and warns if needed
        sip_stats = self.run({"args" : ["csrutil", "status"], "stream" : True})[0]
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
        self.head("SIP Is " + title)
        print(" ")
        print(msg)
        print("This may prevent this script's changes.")
        print(" ")
        menu = self.grab("Would you like to continue? (y/n):  ")

        if not len(menu):
            return self.check_sip()
        
        if menu[:1].lower() == "n":
            return False
        elif menu[:1].lower() == "y":
            return True

        return self.check_sip()

    # Helper methods
    def grab(self, prompt):
        if sys.version_info >= (3, 0):
            return input(prompt)
        else:
            return str(raw_input(prompt))

    # Header drawing method
    def head(self, text = "CPU Name", width = 50):
        os.system("clear")
        print("  {}".format("#"*width))
        mid_len = int(round(width/2-len(text)/2)-2)
        middle = " #{}{}{}#".format(" "*mid_len, text, " "*((width - mid_len - len(text))-2))
        if len(middle) > width+1:
            # Get the difference
            di = len(middle) - width
            # Add the padding for the ...#
            di += 3
            # Trim the string
            middle = middle[:-di] + "...#"
        print(middle)
        print("#"*width)

    def custom_quit(self):
        self.head("CPU Name")
        print("by CorpNewt\n")
        print("Thanks for testing it out, for bugs/comments/complaints")
        print("send me a message on Reddit, or check out my GitHub:\n")
        print("www.reddit.com/u/corpnewt")
        print("www.github.com/corpnewt\n")
        print("Have a nice day/night!\n\n")
        exit(0)

    def restore_backup(self):
        if not self.sip_checked:
            res = self.check_sip()
            if res == None or res == True:
                # Likely on Yosemite?
                self.sip_checked = True
            else:
                return

        self.head("Restoring Backup {}".format(self.file_n))
        print(" ")
        string_path = os.path.join(self._get_lproj(self.lang), self.file_n)
        bak_path    = string_path + ".bak"
        if not os.path.exists(bak_path):
            # Create a backup
            print("Backup doesn't exist...")
            time.sleep(5)
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
        self.run(c, True)
        print(" ")
        print("Done.")
        time.sleep(5)
        return

    def delete_backup(self):
        self.head("Deleting Backup {}".format(self.file_n))
        print(" ")
        string_path = os.path.join(self._get_lproj(self.lang), self.file_n + ".bak")
        if not os.path.exists(string_path):
            # Create a backup
            print("Backup doesn't exist...")
            time.sleep(5)
            return
        # Removing
        print("Removing " + string_path + "...")
        self.run({"args":["rm", string_path],"sudo":True, "stream" : True})
        print(" ")
        print("Done.")
        time.sleep(5)
        return

    def set_cpu(self, cpu):
        if not self.sip_checked:
            res = self.check_sip()
            if res == None or res == True:
                # Likely on Yosemite?
                self.sip_checked = True
            else:
                return

        self.head("Setting CPU to {}".format(cpu))
        print(" ")
        os.chdir(os.path.dirname(os.path.realpath(__file__)))

        # Start our command list
        c = []

        string_path = os.path.join(self._get_lproj(self.lang), self.file_n)

        try:
            string_plist = plistlib.readPlist(string_path)
        except:
            print("Failed to read {}...".format(self.file_n))
            time.sleep(5)
            return
        if not os.path.exists(string_path + ".bak"):
            # Create a backup
            self.run({
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
        plistlib.writePlist(string_plist, temp_file)
        # Build and run commands
        c = [
            {
                "args" : ["mv", "-f", temp_file, string_path],
                "sudo" : True,
                "stream" : True
            }
        ]
        self.run(c, True)
        # Remove temp
        if os.path.exists(temp_folder):
            shutil.rmtree(temp_folder)
        print(" ")
        print("Done.")
        time.sleep(5)
        return

    def main(self):
        self.head("CPU Name")
        print(" ")
        os.chdir(os.path.dirname(os.path.realpath(__file__)))

        cpu_name = self._get_cpu_name()

        print("Current Language:    {}".format(self.lang))
        string_path = os.path.join(self._get_lproj(self.lang), self.file_n)
        try:
            string_plist = plistlib.readPlist(string_path)
            print("Current Unknown CPU: {}".format(string_plist["UnknownCPUKind"]))
        except:
            print("Language lproj doesn't exist!")
        print(" ")

        if cpu_name:
            print("C. Use: {}".format(cpu_name))
        bak = False
        if os.path.exists(string_path+".bak"):
            bak = True
            print("D. Delete Backup")
            print("R. Restore Backup")
        print("Q. Quit")
        print(" ")
        menu = self.grab("Please enter a new CPU name - or a new language (must end in .lproj):  ")

        if not len(menu):
            return
        if menu.lower() == "q":
            self.custom_quit()
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
            self.lang = ".".join(menu.split(".")[:-1])
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
