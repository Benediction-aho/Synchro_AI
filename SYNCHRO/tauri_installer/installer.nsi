; SYNCHRO Auto-Installer NSIS Script
; Detects MT5, installs EA, configures bridge, verifies connection

!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"
!include "WinCore.nsh"
!include "x64.nsh"

!define PRODUCT_NAME "SYNCHRO Trading Agent"
!define PRODUCT_VERSION "1.0.0"
!define PRODUCT_PUBLISHER "SYNCHRO Trading Systems"
!define PRODUCT_WEB_SITE "https://synchro.trade"

; Request admin privileges
RequestExecutionLevel admin

; Modern UI
!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Icons\modern-install.ico"
!define MUI_UNICON "${NSISDIR}\Icons\modern-uninstall.ico"

!insertmacro MUI_PAGE_WELCOME
!define MUI_PAGE_CUSTOMFUNCTION_PRE LicensePagePre
!insertmacro MUI_PAGE_LICENSE "LICENSE.md"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\SYNCHRO.exe"
!define MUI_FINISHPAGE_RUN_NOTCHECKED
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; Languages
!insertmacro MUI_LANGUAGE "English"

; Installation directory
InstallDir "$PROGRAMFILES64\SYNCHRO"
InstallDirRegKey HKLM "Software\SYNCHRO" "InstallDir"

; Components
!define COMPONENT_MAIN "Main Application"
!define COMPONENT_BRIDGE "MQL5 Bridge"

Section /o "${COMPONENT_MAIN}" SecMain
  SectionIn RO
  
  ; Main application
  SetOutPath "$INSTDIR"
  File /r "..\frontend\dist\*"
  
  ; Tauri executable
  File "..\tauri_installer\target\release\SYNCHRO.exe"
  
  ; Uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  
  ; Registry
  WriteRegStr HKLM "Software\SYNCHRO" "InstallDir" "$INSTDIR"
  WriteRegStr HKLM "Software\SYNCHRO" "Version" "${PRODUCT_VERSION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\SYNCHRO" "DisplayName" "${PRODUCT_NAME}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\SYNCHRO" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\SYNCHRO" "Publisher" "${PRODUCT_PUBLISHER}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\SYNCHRO" "URLInfoAbout" "${PRODUCT_WEB_SITE}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\SYNCHRO" "UninstallString" "$INSTDIR\Uninstall.exe"
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\SYNCHRO" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\SYNCHRO" "NoRepair" 1
  
  ; Start menu shortcuts
  CreateDirectory "$SMPROGRAMS\SYNCHRO"
  CreateShortcut "$SMPROGRAMS\SYNCHRO\SYNCHRO Trading Agent.lnk" "$INSTDIR\SYNCHRO.exe"
  CreateShortcut "$SMPROGRAMS\SYNCHRO\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
  CreateShortcut "$SMPROGRAMS\SYNCHRO\SYNCHRO Website.lnk" "https://synchro.trade"
  
  ; Desktop shortcut
  CreateShortcut "$DESKTOP\SYNCHRO Trading Agent.lnk" "$INSTDIR\SYNCHRO.exe"
SectionEnd

Section "${COMPONENT_BRIDGE}" SecBridge
  SectionIn 1
  
  ; Bridge directory
  SetOutPath "$INSTDIR\bridge"
  File /r "..\mql5_bridge\bridge\*"
  
  ; EA files
  SetOutPath "$INSTDIR\bridge\ea"
  File /r "..\mql5_bridge\ea\*"
  
  ; Bridge config template
  SetOutPath "$INSTDIR\bridge\config"
  File "..\mql5_bridge\bridge\config.py"
  
  ; Bridge root directory (will be created at runtime)
  ; C:\SynchroBridge\
  
  ; Bridge service installation
  SetOutPath "$INSTDIR\bridge"
  File "..\mql5_bridge\bridge\main.py"
  File "..\mql5_bridge\bridge\config.py"
  File "..\mql5_bridge\bridge\crypto.py"
  
  ; Python requirements for bridge
  File "..\mql5_bridge\bridge\requirements.txt"
  
  ; Register bridge as Windows service (optional)
  ; ExecWait '"$SYSDIR\sc.exe" create "SYNCHROBridge" binPath= "$INSTDIR\bridge\bridge_service.exe" start= auto'
SectionEnd

; Custom functions
Function LicensePagePre
  ; Check for MT5 installation
  Push $R0
  Push $R1
  
  ; Check common MT5 paths
  StrCpy $R0 0
  
  ; Check Program Files
  ${If} ${FileExists} "$PROGRAMFILES\MetaTrader 5\terminal64.exe"
    StrCpy $R0 1
  ${ElseIf} ${FileExists} "$PROGRAMFILES\MetaTrader 5\terminal.exe"
    StrCpy $R0 1
  ${ElseIf} ${FileExists} "$PROGRAMFILES(X86)\MetaTrader 5\terminal64.exe"
    StrCpy $R0 1
  ${ElseIf} ${FileExists} "$PROGRAMFILES(X86)\MetaTrader 5\terminal.exe"
    StrCpy $R0 1
  ${ElseIf} ${FileExists} "$LOCALAPPDATA\MetaTrader 5\terminal64.exe"
    StrCpy $R0 1
  ${ElseIf} ${FileExists} "$LOCALAPPDATA\MetaTrader 5\terminal.exe"
    StrCpy $R0 1
  ${EndIf}
  
  ${If} $R0 == 0
    MessageBox MB_ICONWARNING|MB_YESNO "MetaTrader 5 not found in standard locations. Continue anyway?" IDNO Abort
  ${EndIf}
  
  Pop $R1
  Pop $R0
FunctionEnd

; Post-install: Auto-detect MT5 and configure
Function .onInstSuccess
  ; Run auto-configuration
  ExecWait '"$INSTDIR\SYNCHRO.exe" --auto-configure'
  
  ; Start bridge service
  ; ExecWait '"$SYSDIR\sc.exe" start "SYNCHROBridge"'
FunctionEnd

; Uninstaller
Section Uninstall
  ; Stop and remove bridge service
  ; ExecWait '"$SYSDIR\sc.exe" stop "SYNCHROBridge"'
  ; ExecWait '"$SYSDIR\sc.exe" delete "SYNCHROBridge"'
  
  ; Remove files
  Delete "$INSTDIR\Uninstall.exe"
  RMDir /r "$INSTDIR"
  
  ; Remove shortcuts
  Delete "$SMPROGRAMS\SYNCHRO\SYNCHRO Trading Agent.lnk"
  Delete "$SMPROGRAMS\SYNCHRO\Uninstall.lnk"
  Delete "$SMPROGRAMS\SYNCHRO\SYNCHRO Website.lnk"
  RMDir "$SMPROGRAMS\SYNCHRO"
  Delete "$DESKTOP\SYNCHRO Trading Agent.lnk"
  
  ; Registry
  DeleteRegKey HKLM "Software\SYNCHRO"
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\SYNCHRO"
SectionEnd

; Function to find MT5 data folder
Function FindMT5DataFolder
  Exch $R0
  
  ; Check registry for MT5 installation
  ReadRegStr $R1 HKCU "Software\MetaQuotes\Terminal\MT5" "DataPath"
  ${If} $R1 != ""
    StrCpy $R0 $R1
    Exch $R0
    Return
  ${EndIf}
  
  ReadRegStr $R1 HKLM "Software\MetaQuotes\Terminal\MT5" "DataPath"
  ${If} $R1 != ""
    StrCpy $R0 $R1
    Exch $R0
    Return
  ${EndIf}
  
  ; Check common locations
  ${If} ${FileExists} "$APPDATA\MetaQuotes\Terminal\*.dat"
    ; Find the correct terminal folder
    FindFirst $R1 $R2 "$APPDATA\MetaQuotes\Terminal\*"
    loop:
      ${If} $R2 != "."
      ${AndIf} $R2 != ".."
      ${AndIf} ${FileExists} "$APPDATA\MetaQuotes\Terminal\$R2\history\*"
        StrCpy $R0 "$APPDATA\MetaQuotes\Terminal\$R2"
        Exch $R0
        Return
      ${EndIf}
      FindNext $R1 $R2
      ${If} $R2 != ""
        Goto loop
      ${EndIf}
    FindClose $R1
  ${EndIf}
  
  StrCpy $R0 ""
  Exch $R0
FunctionEnd

; Install EA to MT5
Function InstallEA
  Exch $R0
  
  Push $R1
  Push $R2
  Push $R3
  
  ; Find MT5 data folder
  Call FindMT5DataFolder
  Pop $R1
  
  ${If} $R1 == ""
    MessageBox MB_ICONERROR "Could not find MetaTrader 5 data folder. Please install manually."
    Pop $R3
    Pop $R2
    Pop $R1
    Exch $R0
    Return
  ${EndIf}
  
  ; Copy EA files
  StrCpy $R2 "$R1\MQL5\Experts\SYNCHRO"
  CreateDirectory "$R2"
  CopyFiles "$INSTDIR\bridge\ea\*" "$R2"
  
  ; Copy include files if any
  StrCpy $R3 "$R1\MQL5\Include\SYNCHRO"
  CreateDirectory "$R3"
  ; CopyFiles "$INSTDIR\bridge\include\*" "$R3"
  
  MessageBox MB_OK "SYNCHRO EA installed to:\n$R2\n\nRestart MetaTrader 5 to load the EA."
  
  Pop $R3
  Pop $R2
  Pop $R1
  Exch $R0
FunctionEnd

; Verify bridge connection
Function VerifyBridgeConnection
  Exch $R0
  
  Push $R1
  Push $R2
  
  ; Check if bridge directory exists
  ${IfNot} ${FileExists} "C:\SynchroBridge\config\bridge_config.json"
    MessageBox MB_ICONWARNING "Bridge not configured. Run auto-configuration from SYNCHRO app."
    Exch $R0
    Return
  ${EndIf}
  
  ; Try to connect to bridge
  ; This would be done via the SYNCHRO app
  
  Pop $R2
  Pop $R1
  Exch $R0
FunctionEnd