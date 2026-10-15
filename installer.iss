; ============================================================
;  Instalador do Baixador de Vídeos  (Inno Setup 6)
;  Para gerar: dê dois cliques em gerar_instalador.bat
; ============================================================
#define MyAppName "Baixador de Vídeos"
#ifndef MyAppVersion
  #define MyAppVersion "1.6.0"
#endif
#define MyAppPublisher "Lagaz"
#define MyAppExeName "BaixadorDeVideos.exe"

[Setup]
AppId={{2F6B8C1E-7A43-4D9B-A5E0-91C3D7B4F6A2}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoVersion={#MyAppVersion}
; Instala só para o usuário atual (não pede senha de administrador).
; Na tela do instalador dá para escolher "para todos os usuários".
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
DisableDirPage=auto
OutputDir=installer_output
OutputBaseFilename=BaixadorDeVideos_Setup
SetupIconFile=icone.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
WizardStyle=modern
WizardImageFile=instalador_assets\wizard_large.bmp
WizardSmallImageFile=instalador_assets\wizard_small.bmp
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\BaixadorDeVideos\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "extensao_navegador\*"; DestDir: "{app}\extensao_navegador"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
; Depois de uma atualização automática (instalação silenciosa), abre o programa de novo
Filename: "{app}\{#MyAppExeName}"; Flags: nowait skipifnotsilent

[UninstallRun]
; Fecha o programa (inclusive se estiver na bandeja) antes de remover os arquivos
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM {#MyAppExeName}"; Flags: runhidden; RunOnceId: "FecharBaixador"

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{localappdata}\BaixadorDeVideos');
    if DirExists(DataDir) and (not UninstallSilent) then
    begin
      if MsgBox('Deseja também apagar o histórico, as configurações e os componentes baixados pelo programa?' + #13#10 + #13#10 +
                '(Os vídeos que você baixou NÃO serão apagados.)',
                mbConfirmation, MB_YESNO) = IDYES then
        DelTree(DataDir, True, True, True);
    end;
  end;
end;
