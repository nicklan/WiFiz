#! /usr/bin/python2

# Importing Standard Libraries #
import os
import sys
import re
import subprocess
import fcntl
import signal

# Importing Third Party Libraries #
from wx import *
from wx.lib.wordwrap import wordwrap
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin
import wx.lib.mixins.listctrl as listmix
from wx import wizard as wiz
import taskbar as tbi

# Import local libraries #
import interface
import netctl

# Setting some base app information #
progVer = '0.9.0'
iwlist_file = os.getcwd() + '/iwlist.log'
iwconfig_file = os.getcwd() + "/iwconfig.log"
int_file = os.getcwd() + "/interface.cfg"
pid_file = os.getcwd() + 'program.pid'
conf_dir = "/etc/netctl/"
pid_number = os.getpid()

#print sys.argv
# do as we're told #
for arg in sys.argv:
    if arg == '--help' or arg == '-h':
        print "WiFiz; The netctl gui! \nNeeds to be root."
        sys.exit(0)

# Lets make sure we're root as well #
euid = os.geteuid()
if euid != 0:
    print ("WiFiz needs to be run as root, we're going to sudo for you. \n"
            "You can Ctrl+c to exit... (maybe)")
    args = ['sudo', sys.executable] + sys.argv + [os.environ]
    os.execlpe('sudo', *args)

# Allow only one instance #
fp = open(pid_file, 'w')
try:
    fcntl.lockf(fp, fcntl.LOCK_EX|fcntl.LOCK_NB)
except IOError:
    print "We only allow one instance of WiFiz at a time for now."
    sys.exit(1)
fp.write(str(pid_number) + "\n")
fp.flush()

# main class #
class WiFiz(wx.Frame):
    def __init__(self, parent, title):
        super(WiFiz, self).__init__(None, title="WiFiz",
                            style = wx.DEFAULT_FRAME_STYLE)
        self.TrayIcon = tbi.Icon(self, wx.Icon("./imgs/logo.png",
                                    wx.BITMAP_TYPE_PNG), "WiFiz")
        self.index = 0
        self.InitUI()

    def InitUI(self):

        iconFile = "./imgs/logo.png"
        mainIcon = wx.Icon(iconFile, wx.BITMAP_TYPE_PNG)
        self.SetIcon(mainIcon)

        # Menu Bar #
        self.mainMenu = wx.MenuBar()

        fileMenu = wx.Menu()
        ScanAPs = fileMenu.Append(wx.ID_ANY, "Scan for New Networks",
                                    "Scan for New Wireless Networks.")
        fileMenu.AppendSeparator()
        fileQuit = fileMenu.Append(wx.ID_EXIT, "Quit", "Exit the Program.")
        self.mainMenu.Append(fileMenu, "&File")

        profilesMenu = wx.Menu()
        profiles = os.listdir("/etc/netctl/")
        for i in profiles:
            if os.path.isfile("/etc/netctl/" + i):
                profile = profilesMenu.Append(wx.ID_ANY, i)
                self.Bind(wx.EVT_MENU, self.OnMConnect, profile)
        self.mainMenu.Append(profilesMenu, "Profiles")

        helpMenu = wx.Menu()
        helpItem = helpMenu.Append(wx.ID_HELP, "Help with WiFiz",
                                            "Get help with WiFiz")
        helpItem.Enable(False)
        helpMenu.AppendSeparator()
        reportIssue = helpMenu.Append(wx.ID_ANY, "Report an Issue...",
                                    "Report a bug, or give a suggestion.")
        helpMenu.AppendSeparator()
        aboutItem = helpMenu.Append(wx.ID_ABOUT, "About WiFiz",
                                        "About this program...")
        self.mainMenu.Append(helpMenu, "&Help")

        self.SetMenuBar(self.mainMenu)

        # End Menu Bar #

        # Create Popup Menu #
        self.PopupMenu = wx.Menu()
        popCon = self.PopupMenu.Append(wx.ID_ANY, "Connect to Network",
                                            "Connect to selected network.")
        popDCon = self.PopupMenu.Append(wx.ID_ANY, "Disconnect from Network",
                                        "Disconnect from selected network.")

        # Create Toolbar Buttons #
        toolbar = self.CreateToolBar()
        newTool = toolbar.AddLabelTool(wx.ID_NEW, 'New',
            wx.ArtProvider.GetBitmap(wx.ART_NEW), wx.NullBitmap,
            wx.ITEM_NORMAL, 'New Connection')
        ReScanAPs = toolbar.AddLabelTool(wx.ID_ANY, 'Scan',
            wx.Bitmap('imgs/APScan.png'), wx.NullBitmap,
            wx.ITEM_NORMAL, 'Scan')
        connectSe = toolbar.AddLabelTool(wx.ID_ANY, 'Connect',
            wx.Bitmap('imgs/connect.png'), wx.NullBitmap,
            wx.ITEM_NORMAL, 'Connect')
        dConnectSe = toolbar.AddLabelTool(wx.ID_ANY, 'Disconnect',
            wx.Bitmap('imgs/disconnect.png'), wx.NullBitmap,
            wx.ITEM_NORMAL, 'Disconnect')
        toolbar.AddSeparator()
        quitTool = toolbar.AddLabelTool(wx.ID_EXIT, 'Quit',
            wx.ArtProvider.GetBitmap(wx.ART_QUIT), wx.NullBitmap,
            wx.ITEM_NORMAL, 'Quit')
        toolbar.Realize()
        # End Toolbar #

        self.APList = AutoWidthListCtrl(self)

        self.APList.setResizeColumn(0)
        self.APList.InsertColumn(0, "SSID", width=150)
        self.APList.InsertColumn(1, "Connection Strength", width=200)
        self.APList.InsertColumn(2, "Security Type", width=150)
        self.APList.InsertColumn(3, "Connected?", width=150)

        # Create Status Bar #
        self.CreateStatusBar()
        # End Status Bar #

        # Binding Events #
        self.Bind(wx.EVT_MENU, self.OnClose, fileQuit)
        self.Bind(wx.EVT_TOOL, self.OnConnect, connectSe)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_MENU, self.OnAbout, aboutItem)
        self.Bind(wx.EVT_MENU, self.OnScan, ScanAPs)
        self.Bind(wx.EVT_TOOL, self.OnScan, ReScanAPs)
        self.Bind(wx.EVT_TOOL, self.OnNew, newTool)
        self.Bind(wx.EVT_TOOL, self.OnDConnect, dConnectSe)
        self.Bind(wx.EVT_CONTEXT_MENU, self.OnShowPopup)
        self.Bind(wx.EVT_CONTEXT_MENU, self.OnConnect, popCon)
        self.Bind(wx.EVT_CONTEXT_MENU, self.OnDConnect, popDCon)
        self.Bind(wx.EVT_MENU, self.OnReport, reportIssue)
        # End Bindings #

        self.SetSize((700,390))
        self.Center()
        #self.Show()

        # Get interface name: From file or from user.
        self.UIDvalue = GetInterface(self)
        #interface.up(self.UIDValue)
        #self.OnScan(self)

    # TODO rename this funct
    def OnMConnect(self, profile):
        #item = self.mainMenu.FindItemById(e.GetId())
        #profile = item.GetText()
        netinterface = GetInterface(self)
        interface.down(netinterface)
        netctl.stopall()
        netctl.start(profile)

    def OnPref(self, e):
        prefWindow = Preferences(self, wx.ID_ANY, title="Preferences")
        prefWindow.CenterOnParent()
        prefWindow.Show()

    def OnEdit(self, e):
        editWindow = EditProfile(None)

    # TODO rename this section.
    def OnConnect(self, e):
        # TODO rewrite this section, we sould be grabbing this
        # info from eleswhere.
        index = str(self.getSelectedIndices()).strip('[]')
        index = int(index)
        nmp = self.APList.GetItem(index, 0)
        nameofProfile = nmp.GetText()
        tos = self.APList.GetItem(index, 2)
        typeofSecurity = tos.GetText()
        typeofSecurity = str(typeofSecurity).strip()
        typeofSecurity = typeofSecurity.lower()
        # HACK TODO REMOVE
        if typeofSecurity == open:
            typeofSecurity = 'none'

        filename = str("wifiz" + u'-' + nameofProfile).strip()
        filename = filename.strip()

        # We need to make this section optional
        # TODO and move it out of here
        print filename
        if os.path.isfile(conf_dir + filename):
            interface.down(self.UIDValue)
            netctl.start(filename)
            # Missing function TODO
            if IsConnected():
                wx.MessageBox("You are now connected to " +
                    str(nameofProfile) + ".", "Connected.")
            else:
                wx.MessageBox("There has been an error, please try again. "
                    "If it persists, please contact Cody Dostal at "
                    "dostalcody@gmail.com.", "Error!")
        else:
            if str(typeofSecurity).strip() is not "none":
                passw = wx.TextEntryDialog(self, "What is the password?",
                                           "Password", "")
                if passw.ShowModal() == wx.ID_OK:
                    network_key = passw.GetValue()
                else:
                    print "Something went wrong getting the network password.\n"
                    network_key = None
            else:
                network_key = None

            CreateConfig(nameofProfile, self.UIDValue, typeofSecurity, key)
            # Currently unworking TODO!
            # pref = wx.TextEntryDialog(self, "Is this network preferred? "
            #     "(In range of multiple profiles, connect to this first?)"
            #                                     "Preferred Network?", "")
            # if pref.ShowModal() == wx.ID_OK:
            #     f.write("#preferred=yes\n")
            # else:
            #     f.write("#preferred=no\n")
            f.write("IP=dhcp\n")
            f.close()


            try:
                interface.down(self.UIDValue)
                netctl.start(filename)
                wx.MessageBox("You are now connected to " +
                            str(nameofProfile).strip() + ".", "Connected.")
            except:
                wx.MessageBox("There has been an error, please try again. If"
                        " it persists, please contact Cody Dostal at "
                        "dostalcody@gmail.com.", "Error!")
            self.OnScan(self)

    def getSelectedIndices(self, state =  wx.LIST_STATE_SELECTED):
        indices = []
        lastFound = -1
        while True:
            index = self.APList.GetNextItem(
                lastFound,
                wx.LIST_NEXT_ALL,
                state,
            )
            if index == -1:
                break
            else:
                lastFound = index
                indices.append( index )
        return indices

    def OnReport(self, e):
        wx.MessageBox("To report a message, send an email to "
                            "cody@seafiresoftware.org", "e-Mail")

    def OnShowPopup(self, e):
        x, y = e.GetPosition()
        pos = self.APList.ScreenToClientXY(x, y)
        self.APList.PopupMenu(self.PopupMenu, pos)

    def OnDConnect(self, e):
        index = str(self.getSelectedIndices()).strip('[]')
        index = int(index)
        item = self.APList.GetItem(index, 0)
        nameofProfile = item.GetText()
        netctl.stop(filename)
        interface.down(self.UIDValue)
        self.OnScan(self)
        wx.MessageBox("You are now disconnected from " +
                    nameofProfile + ".", "Disconnected.")

    def OnNew(self, e):
        newProf = NewProfile(parent=None)

    def OnScan(self, e):
        '''Scan on [device], save output'''
        # Scan for access points
        interface.up(self.UIDValue)
        output = str(subprocess.check_output("iwlist " + self.UIDValue +
                                                        " scan", shell=True))
        f = open(iwlist_file, 'w')
        f.write(output)
        f.close()
        # Clear APList
        self.APList.DeleteAllItems()
        self.index = 0
        # Write iwconfig status
        outputs = str(subprocess.check_output("iwconfig " + self.UIDValue ,
                                                                shell=True))
        d = open(iwconfig_file, 'w')
        d.write(outputs)
        d.close()
        # I'd rather use regex and get an array
        iwlist = open(iwlist_file, 'r').read()
        # Split by access point
        ap_list = re.split(r'Cell \d\d -', iwlist)

        for ap in ap_list:
            # Split by line
            ap_data = re.split("\n+",ap)
            for line in ap_data:
                kv = re.split(":", line.strip())
                if kv[0] == "ESSID":
                    self.APList.SetStringItem(self.index, 0,
                            kv[1].strip().replace('"', ""))
                if kv[0] == "Encryption key":
                    if kv[1] == "off":
                        encrypt = "Open"
                        file_encrypt = "none"
                    elif kv[1] == "on":
                        encrypt = "Probably WEP"
                    self.APList.SetStringItem(self.index, 2, encrypt)
                if "WPA" in line:
                    encrypt = "WPA"
                    self.APList.SetStringItem(self.index, 2, encrypt)
                if "WPA2" in line:
                    encrypt = "WPA2"
                    self.APList.SetStringItem(self.index, 2, encrypt)

                # TODO conver this line!
                if "Quality" in line:
                    lines = "Line %s" % self.index
                    self.APList.InsertStringItem(self.index, lines)
                    self.index + 1
                    s = str(line)[28:33]
                    # Courtesy of gohu's iwlistparse.py, slightly modified.
                    # https://bbs.archlinux.org/viewtopic.php?id=88967
                    s3 = str(int(round(float(s[0])/float(s[3])*100))).rjust(3)+" %"
                    self.APList.SetStringItem(self.index, 1, s3)

                # profiles = os.listdir("/etc/netctl/")
                # if any(essid.strip() in s for s in profiles):
                #     profile = "wifiz-" + essid.strip()
                #     if os.path.isfile(conf_dir + profile):
                #         for line in open(conf_dir + profile):
                #             if "#preferred" in line:
                #                 if "yes" in line:
                #                     profile = profile
                #                 else:
                #                     pass

        f = open(iwconfig_file, 'w')
        f.write(outputs)
        f.close()

        # TODO if atocnnt enabled DO
        # try:
        #     self.AutoConnect()
        # except:
        #     print "Auto connect failed!"
        # else:
        #     pass
    # TODO unworking
    def AutoConnect(self, e):
        try:
            interface.down(self.UIDValue)
            netctl.start(self.profile)
            wx.MessageBox("You are now connected to " + str(self.profile).strip() + ".", "Connected.")
        except:
            wx.MessageBox("There has been an error, please try again. "
                        "If it persists, please contact Cody Dostal "
                        "at dostalcody@gmail.com.", "Error!")

    def OnClose(self, e):
        self.Hide()

    def OnFullClose(self, e):
        open(iwlist_file, 'w').close()
        app.Exit()

    def OnAbout(self, e):
        description = """WiFiz is a simple to use, frontend for NetCTL."""
        licence = open('Wifiz.licence', 'r').read()

        info = wx.AboutDialogInfo()

        info.SetIcon(wx.Icon('./imgs/aboutLogo.png', wx.BITMAP_TYPE_PNG))
        info.SetName('WiFiz')
        info.SetVersion(str(progVer))
        info.SetDescription(description)
        info.SetCopyright("(C) 2012 Cody Dostal (a.k.a. Pivotraze)")
        info.SetWebSite("https://www.github.com/codywd")
        info.SetLicence(wordwrap(licence, 350, wx.ClientDC(self)))
        info.AddDeveloper('Cody Dostal')
        info.AddDocWriter('Cody Dostal')
        info.AddArtist('Sam Stuewe')
        info.AddTranslator('Cody Dostal (English)')

        wx.AboutBox(info)

# Class to manually create new network profile
class NewProfile(wx.Dialog):
    def __init__(self, parent):
        super(NewProfile, self).__init__(None)
        self.InitUI()

    def InitUI(self):
        wizard = wx.wizard.Wizard(None, -1, "New Profile Wizard")
        page1 = TitledPage(wizard, "Interface")
        page1.Sizer.Add(wx.StaticText(page1, -1, "Please type the name of the"
            " interface you will be \nusing to connect to the network. "
            "Examples are \nwlan0, eth0, etc..."))
        page1.Sizer.Add(wx.StaticText(page1, -1, ""))
        intFaces = os.listdir("/sys/class/net")
        for i in intFaces:
            page1.Sizer.Add(wx.RadioButton(page1, -1, i))
        page2 = TitledPage(wizard, "Connection Type")
        page2.Sizer.Add(wx.StaticText(page2, -1,
            "Please type the type of connection you will be using."))
        page2.Sizer.Add(wx.StaticText(page2, -1, ""))
        choiceWiFi = wx.RadioButton(page2, -1, "Wireless", style=wx.RB_GROUP)
        choiceEth = wx.RadioButton(page2, -1, "Ethernet")
        page2.Sizer.Add(choiceWiFi)
        page2.Sizer.Add(choiceEth)
        page3 = TitledPage(wizard, "Security Type")
        page3.Sizer.Add(wx.StaticText(page3, -1,
            "Please type the security type of the connection."))
        page3.Sizer.Add(wx.StaticText(page3, -1, ""))
        choiceWEP = wx.RadioButton(page3, -1, "WEP", style=wx.RB_GROUP)
        choiceWPA = wx.RadioButton(page3, -1, "WPA/WPA2")
        choiceNONE = wx.RadioButton(page3, -1, "None")
        page3.Sizer.Add(choiceWEP)
        page3.Sizer.Add(choiceWPA)
        page3.Sizer.Add(choiceNONE)
        page4 = TitledPage(wizard, "SSID")
        page4.Sizer.Add(wx.StaticText(page4, -1,
            "Please type the name of the network you wish to connect to."))
        page4.Sizer.Add(wx.StaticText(page4, -1, ""))
        SSIDV = wx.TextCtrl(page4)
        page4.Sizer.Add(SSIDV, flag=wx.EXPAND)
        SSID = SSIDV.GetValue()
        page5 = TitledPage(wizard, "Security Key")
        page5.Sizer.Add(wx.StaticText(page5, -1,
            "Please type the password of the network you wish to connect to."))
        page5.Sizer.Add(wx.StaticText(page5, -1, ""))
        self.securePass = wx.TextCtrl(page5, style=wx.TE_PASSWORD)
        page5.Sizer.Add(self.securePass, flag=wx.EXPAND)
        self.password = self.securePass.GetValue()
        page6 = TitledPage(wizard, "Hidden Network")
        page6.Sizer.Add(wx.StaticText(page6, -1,
            "Is the network hidden? If so, check the checkbox."))
        page6.Sizer.Add(wx.StaticText(page6, -1, ""))
        page6.Sizer.Add(wx.CheckBox(page6, -1, "Network is Hidden"))

        wx.wizard.WizardPageSimple.Chain(page1, page2)
        wx.wizard.WizardPageSimple.Chain(page2, page3)
        wx.wizard.WizardPageSimple.Chain(page3, page4)
        wx.wizard.WizardPageSimple.Chain(page4, page5)
        wx.wizard.WizardPageSimple.Chain(page5, page6)
        wizard.FitToPage(page1)
        wizard.RunWizard(page1)
        wizard.Destroy()

        self.Bind(wiz.EVT_WIZARD_CANCEL, self.closeDialog)
        self.Bind(wiz.EVT_WIZARD_FINISHED, self.saveProfile)

    def saveProfile(self, e):
        wx.MessageBox(self.interfaceName, self.interfaceName, wx.ID_OK)
        wx.MessageBox(self.connectionType, self.connectionType, wx.ID_OK)

    def closeDialog(self, e):
        dial = wx.MessageDialog(None, "Are you sure you want to cancel?",
            "Cancel?", wx.YES_NO|wx.NO_DEFAULT|wx.ICON_QUESTION)
        ret = dial.ShowModal()
        if ref == wx.ID_YES:
            self.Destroy()
        else:
            e.Veto()

class AutoWidthListCtrl(wx.ListCtrl, ListCtrlAutoWidthMixin):
    def __init__(self, parent):
        wx.ListCtrl.__init__(self, parent, -1, style=wx.LC_REPORT)
        ListCtrlAutoWidthMixin.__init__(self)

class TitledPage(wiz.WizardPageSimple):
    def __init__(self, parent, title):
        wiz.WizardPageSimple.__init__(self, parent)

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        title = wx.StaticText(self, -1, title)
        title.SetFont(wx.Font(18, wx.SWISS, wx.NORMAL, wx.BOLD))
        sizer.Add(title, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALL, 5)
        sizer.Add(wx.StaticLine(self, -1), 0, wx.EXPAND|wx.ALL, 5)

def GetInterface(wxobj):
    if os.path.isfile(int_file):
        f = open(int_file)
        interface = f.readline()
        f.close()
        return str(interface).strip()
    else:
        wxobj.UID = wx.TextEntryDialog(wxobj, "What is your Interface Name? "
            "(wlan0, wlp2s0)", "Wireless Interface", "")
        if wxobj.UID.ShowModal() == wx.ID_OK:
            # rename this var!! TODO
            wxobj.UIDValue = wxobj.UID.GetValue()
            # TODO error checking for null values
            f = open(int_file, 'w')
            f.write(wxobj.UIDValue)
            f.close()

def CreateConfig(name, interface, security, key=None, ip='dhcp'):
    print "Creating Config File!\n"
    # TODO genertate better filename
    filename =  name + "-wifiz"
    f = open(conf_dir + filename, "w")
    f.write("Description='A profile generated by Wifiz for "+str(name)+"'\n" +
    "Interface=" + str(interface) + "\n" +
    "Connection=wireless\n" +
    "Security=" + str(security) + "\n" +
    "ESSID='" + str(name) + "'\n")
    if key:
        f.write(r'Key=\"' + key + "\n")
    else:
        f.write(r'Key=None\n')
    f.write("IP=dhcp\n")
    f.close()

def IsConnected(interface):
    '''Query the selected interface, return True if up else return False'''
    ip = subprocess.check_output('ip -o link show '+ interface)
    status = re.split('\s', ip)
    if status[9] == 'UP': return True
    else: return False

def cleanUp():
    # Clean up time
    fcntl.lockf(fp, fcntl.LOCK_UN)
    fp.close()
    os.unlink(pid_file)
    # os.unlink(int_file)   # I cant decide if we want to keep this file or
                            # or do something else with it?
    try:
        os.unlink(iwlist_file)
        os.unlink(iwconfig_file)
    except:
        pass

def sigInt(signal, frame):
    print "CTRL-C Caught, cleaning up..."
    cleanUp()
    print "done. BYE!"
    sys.exit(0)

# Start App #
if __name__ == "__main__":
    wxAppPid = os.fork() # Consider pty module instead? TODO
    if wxAppPid:
        # We'll handle ctrl-c
        signal.signal(signal.SIGINT, sigInt)
        os.waitpid(wxAppPid,0)
        print "Child died here\n"
        cleanUp()
        sys.exit(0)
    else:
        # Child mode
        # Prepare app
        app = wx.App(False)
        WiFiz(None, title="WiFiz")
        # Run app
        app.MainLoop()
