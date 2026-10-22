#requires -Version 7.0
# SPDX-License-Identifier: MIT
# Read-only verification of an existing executable's icon resources.
[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string] $InputExecutable,
    [Parameter(Mandatory)] [string] $IconPath
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if (-not $IsWindows -or -not [Environment]::Is64BitProcess) { throw 'Requires Windows and PowerShell 7 x64.' }

function Resolve-XmqrIconInput([string] $Path) {
    $full = [IO.Path]::GetFullPath($Path)
    if ($full -notmatch '^[A-Za-z]:\\' -or $full.Substring(2).Contains(':')) { throw 'Only local drive paths without alternate streams are supported.' }
    $cursor = Get-Item -LiteralPath $full -Force
    if ($cursor -isnot [IO.FileInfo]) { throw 'Input must be an existing regular file.' }
    while ($null -ne $cursor) {
        if (($cursor.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Reparse-point paths are not supported.' }
        $cursor = if ($cursor -is [IO.FileInfo]) { $cursor.Directory } else { $cursor.Parent }
    }
    return $full
}

$executable = Resolve-XmqrIconInput $InputExecutable
$icon = Resolve-XmqrIconInput $IconPath
if (-not ('XmqrReadOnlyIconVerificationV1' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Security.Cryptography;

public static class XmqrReadOnlyIconVerificationV1 {
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    static extern IntPtr LoadLibraryExW(string path, IntPtr file, uint flags);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    static extern IntPtr FindResourceExW(IntPtr module, IntPtr type, IntPtr name, ushort language);
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern uint SizeofResource(IntPtr module, IntPtr resource);
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern IntPtr LoadResource(IntPtr module, IntPtr resource);
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern IntPtr LockResource(IntPtr resource);
    [DllImport("kernel32.dll", SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    static extern bool FreeLibrary(IntPtr module);
    [UnmanagedFunctionPointer(CallingConvention.Winapi)]
    [return: MarshalAs(UnmanagedType.Bool)]
    delegate bool LanguageCallback(IntPtr module, IntPtr type, IntPtr name, ushort language, IntPtr parameter);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    static extern bool EnumResourceLanguagesW(IntPtr module, IntPtr type, IntPtr name, LanguageCallback callback, IntPtr parameter);

    public sealed class Result {
        public int verified_resources { get; set; }
        public int icon_images { get; set; }
        public string executable_sha256 { get; set; }
        public bool unchanged { get; set; }
    }
    sealed class Image {
        public byte[] Metadata, Bytes;
    }
    static void Need(byte[] bytes, long offset, long length) {
        if(offset<0 || length<0 || offset>bytes.LongLength || length>bytes.LongLength-offset)
            throw new InvalidDataException("Truncated or out-of-bounds icon structure.");
    }
    static ushort U16(byte[] b, int o) { Need(b,o,2); return BitConverter.ToUInt16(b,o); }
    static uint U32(byte[] b, int o) { Need(b,o,4); return BitConverter.ToUInt32(b,o); }
    static uint Be32(byte[] b, int o) { Need(b,o,4); return ((uint)b[o]<<24)|((uint)b[o+1]<<16)|((uint)b[o+2]<<8)|b[o+3]; }
    static byte[] Slice(byte[] bytes, int offset, int length) {
        Need(bytes,offset,length); byte[] result=new byte[length]; Buffer.BlockCopy(bytes,offset,result,0,length); return result;
    }
    static string Hash(byte[] bytes) {
        using(SHA256 sha=SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-","").ToLowerInvariant();
    }
    static byte[] ReadBounded(string path, int maximum) {
        using(FileStream stream=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read)) {
            if(stream.Length<1 || stream.Length>maximum) throw new InvalidDataException("Input exceeds the supported size bound.");
            byte[] bytes=new byte[(int)stream.Length]; int offset=0;
            while(offset<bytes.Length) { int count=stream.Read(bytes,offset,bytes.Length-offset); if(count==0) throw new EndOfStreamException(); offset+=count; }
            if(stream.ReadByte()!=-1) throw new InvalidDataException("Input size changed while reading.");
            return bytes;
        }
    }
    static List<Image> ReadIcon(byte[] ico) {
        Need(ico,0,6);
        if(U16(ico,0)!=0 || U16(ico,2)!=1 || U16(ico,4)!=9) throw new InvalidDataException("Expected a nine-image ICO file.");
        int count=U16(ico,4); Need(ico,6,count*16);
        var images=new List<Image>(); var ranges=new List<Tuple<uint,uint>>();
        byte[] signature={137,80,78,71,13,10,26,10};
        for(int i=0;i<count;i++) {
            int row=6+i*16; uint size=U32(ico,row+8),offset=U32(ico,row+12);
            if(ico[row+3]!=0 || U16(ico,row+4)>1 || size<33 || offset<6+count*16)
                throw new InvalidDataException("Invalid ICO directory entry.");
            Need(ico,offset,size);
            foreach(var range in ranges) if((ulong)offset<(ulong)range.Item1+range.Item2 && (ulong)range.Item1<(ulong)offset+size)
                throw new InvalidDataException("Overlapping ICO images.");
            ranges.Add(Tuple.Create(offset,size));
            byte[] bytes=Slice(ico,(int)offset,(int)size);
            int width=ico[row]==0?256:ico[row],height=ico[row+1]==0?256:ico[row+1];
            if(!bytes.Take(8).SequenceEqual(signature) || Be32(bytes,8)!=13 ||
                bytes[12]!=73 || bytes[13]!=72 || bytes[14]!=68 || bytes[15]!=82 ||
                Be32(bytes,16)!=width || Be32(bytes,20)!=height)
                throw new InvalidDataException("ICO PNG signature/IHDR/dimensions mismatch.");
            images.Add(new Image {Metadata=Slice(ico,row,12),Bytes=bytes});
        }
        return images;
    }
    static void WinError(string operation) { throw new Win32Exception(Marshal.GetLastWin32Error(),operation); }
    static byte[] Resource(IntPtr module, int type, int id, ushort language, int maximum) {
        IntPtr resource=FindResourceExW(module,new IntPtr(type),new IntPtr(id),language);
        if(resource==IntPtr.Zero) WinError("FindResourceEx");
        uint length=SizeofResource(module,resource);
        if(length<1 || length>maximum) throw new InvalidDataException("Resource exceeds the supported size bound.");
        IntPtr handle=LoadResource(module,resource); if(handle==IntPtr.Zero) WinError("LoadResource");
        IntPtr data=LockResource(handle); if(data==IntPtr.Zero) WinError("LockResource");
        byte[] bytes=new byte[(int)length]; Marshal.Copy(data,bytes,0,bytes.Length); return bytes;
    }
    public static Result Verify(string executable, string icon) {
        byte[] original=ReadBounded(executable,160*1024*1024);
        var images=ReadIcon(ReadBounded(icon,16*1024*1024));
        IntPtr module=LoadLibraryExW(executable,IntPtr.Zero,0x2); // AS_DATAFILE: no executable initialization.
        if(module==IntPtr.Zero) WinError("LoadLibraryEx resource-only");
        int verified=0;
        try {
            var languages=new List<ushort>(); bool overflow=false;
            LanguageCallback callback=(m,t,n,language,p)=> {
                if(languages.Count>=16 || languages.Contains(language)) { overflow=true; return false; }
                languages.Add(language); return true;
            };
            bool enumerated=EnumResourceLanguagesW(module,new IntPtr(14),new IntPtr(1),callback,IntPtr.Zero);
            GC.KeepAlive(callback);
            if(overflow) throw new InvalidDataException("Too many or duplicate group-icon languages.");
            if(!enumerated) WinError("EnumResourceLanguages group icon 1");
            if(languages.Count==0) throw new InvalidDataException("Group icon 1 has no language resources.");
            foreach(ushort language in languages) {
                byte[] group=Resource(module,14,1,language,6+images.Count*14);
                if(group.Length!=6+images.Count*14 || U16(group,0)!=0 || U16(group,2)!=1 || U16(group,4)!=images.Count)
                    throw new InvalidDataException("Group icon header/count/length mismatch.");
                var ids=new HashSet<ushort>();
                for(int i=0;i<images.Count;i++) {
                    int row=6+i*14;
                    if(!Slice(group,row,12).SequenceEqual(images[i].Metadata)) throw new InvalidDataException("Group icon metadata mismatch.");
                    ushort id=U16(group,row+12);
                    if(id==0 || !ids.Add(id)) throw new InvalidDataException("Group icon contains zero or duplicate image IDs.");
                    byte[] actual=Resource(module,3,id,language,images[i].Bytes.Length);
                    if(!actual.SequenceEqual(images[i].Bytes)) throw new InvalidDataException("Icon image resource bytes mismatch.");
                    verified++;
                }
                verified++;
            }
        } finally { if(!FreeLibrary(module)) throw new Win32Exception(Marshal.GetLastWin32Error(),"FreeLibrary resource mapping"); }
        if(!ReadBounded(executable,160*1024*1024).SequenceEqual(original)) throw new InvalidDataException("Executable changed during verification.");
        return new Result {verified_resources=verified,icon_images=images.Count,executable_sha256=Hash(original),unchanged=true};
    }
}
'@
}
[XmqrReadOnlyIconVerificationV1]::Verify($executable, $icon) | ConvertTo-Json -Depth 3
