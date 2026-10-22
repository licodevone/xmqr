#requires -Version 7.0
# SPDX-License-Identifier: MIT
# Update icon resources on a new unsigned PE copy. Never patches the source.
[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory)] [string] $InputExecutable,
    [Parameter(Mandatory)] [string] $IconPath,
    [Parameter(Mandatory)] [string] $OutputExecutable
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if (-not $IsWindows -or -not [Environment]::Is64BitProcess) { throw 'Requires Windows and PowerShell 7 x64.' }

function Resolve-LocalPath([string] $Path, [bool] $MustExist) {
    $full = [IO.Path]::GetFullPath($Path)
    if ($full -notmatch '^[A-Za-z]:\\' -or $full.Substring(2).Contains(':')) { throw 'Only local drive paths without alternate streams are supported.' }
    if ($MustExist -and -not [IO.File]::Exists($full)) { throw "Input file not found: $full" }
    $cursor = if (Test-Path -LiteralPath $full) { Get-Item -LiteralPath $full -Force } else { Get-Item -LiteralPath ([IO.Path]::GetDirectoryName($full)) -Force }
    while ($null -ne $cursor) {
        if (($cursor.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Reparse-point paths are not supported.' }
        $cursor = if ($cursor -is [IO.FileInfo]) { $cursor.Directory } else { $cursor.Parent }
    }
    return $full
}

$source = Resolve-LocalPath $InputExecutable $true
$icon = Resolve-LocalPath $IconPath $true
$destination = Resolve-LocalPath $OutputExecutable $false
if ([string]::Equals($source, $destination, [StringComparison]::OrdinalIgnoreCase) -or
    [string]::Equals($icon, $destination, [StringComparison]::OrdinalIgnoreCase) -or
    (Test-Path -LiteralPath $destination)) { throw 'Output must be a new path distinct from both inputs.' }
if (-not $PSCmdlet.ShouldProcess($destination, 'Create an unsigned executable copy with icon resources')) { return }

if (-not ('XmqrIconResourcesV1' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;

public static class XmqrIconResourcesV1 {
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    static extern IntPtr BeginUpdateResourceW(string path, [MarshalAs(UnmanagedType.Bool)] bool deleteExisting);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    static extern bool UpdateResourceW(IntPtr handle, IntPtr type, IntPtr name, ushort language, byte[] data, uint length);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    static extern bool EndUpdateResourceW(IntPtr handle, [MarshalAs(UnmanagedType.Bool)] bool discard);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    static extern IntPtr LoadLibraryExW(string path, IntPtr file, uint flags);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    static extern IntPtr FindResourceExW(IntPtr module, IntPtr type, IntPtr name, ushort language);
    [DllImport("kernel32.dll", SetLastError=true)] static extern uint SizeofResource(IntPtr module, IntPtr resource);
    [DllImport("kernel32.dll", SetLastError=true)] static extern IntPtr LoadResource(IntPtr module, IntPtr resource);
    [DllImport("kernel32.dll", SetLastError=true)] static extern IntPtr LockResource(IntPtr resource);
    [DllImport("kernel32.dll")] [return: MarshalAs(UnmanagedType.Bool)] static extern bool FreeLibrary(IntPtr module);

    public sealed class Result {
        public string InputExecutable { get; set; }
        public string OutputExecutable { get; set; }
        public string InputSha256 { get; set; }
        public string OutputSha256 { get; set; }
        public string IconSha256 { get; set; }
        public int IconImageCount { get; set; }
        public int VerifiedResources { get; set; }
        public int VerifiedNonResourceSections { get; set; }
        public int PreservedOtherResources { get; set; }
        public bool RelocationSectionMoved { get; set; }
        public bool CodeIntegrity { get; set; }
    }
    sealed class Section {
        public string Name;
        public uint Address, VirtualSize, RawSize, RawOffset, Flags;
        public string Hash;
    }
    sealed class Pe {
        public byte[] Bytes;
        public List<Section> Sections = new List<Section>();
        public Dictionary<string,string> OtherResources = new Dictionary<string,string>();
        public uint Entry, Subsystem;
        public ulong ImageBase;
        public uint ResourceAddress;
        public uint RelocationAddress, RelocationSize;
        public List<Tuple<uint,uint>> Directories = new List<Tuple<uint,uint>>();
        public long ResourceRoot;
        int resourceEntries;
        public Pe(byte[] bytes) {
            Bytes=bytes;
            Need(bytes,0,64);
            if (U16(bytes,0)!=0x5a4d) throw new InvalidDataException("Not a DOS/PE image.");
            long pe=U32(bytes,60); Need(bytes,pe,24);
            if (U32(bytes,pe)!=0x4550 || U16(bytes,pe+4)!=0x8664) throw new InvalidDataException("Only x64 PE images are supported.");
            int count=U16(bytes,pe+6), optionalSize=U16(bytes,pe+20);
            long optional=pe+24; Need(bytes,optional,optionalSize);
            if (optionalSize<152 || U16(bytes,optional)!=0x20b || U32(bytes,optional+108)<5) throw new InvalidDataException("Invalid PE32+ optional header.");
            if (U32(bytes,optional+144)!=0 || U32(bytes,optional+148)!=0) throw new InvalidDataException("Signed executables are refused; sign only after resource updates.");
            Entry=U32(bytes,optional+16); ImageBase=U64(bytes,optional+24); Subsystem=U16(bytes,optional+68);
            ResourceAddress=U32(bytes,optional+128);
            uint directories=U32(bytes,optional+108);
            if(directories>16) throw new InvalidDataException("Unsupported PE data directory count.");
            Need(bytes,optional+112,directories*8L);
            for(int i=0;i<directories;i++) Directories.Add(Tuple.Create(U32(bytes,optional+112+i*8),U32(bytes,optional+116+i*8)));
            if(directories>5) { RelocationAddress=U32(bytes,optional+152); RelocationSize=U32(bytes,optional+156); }
            if (count<1 || count>96) throw new InvalidDataException("Invalid PE section count.");
            long table=optional+optionalSize; Need(bytes,table,(long)count*40);
            for (int i=0;i<count;i++) {
                long row=table+i*40;
                Section s=new Section {Name=Encoding.ASCII.GetString(bytes,(int)row,8).TrimEnd('\0'),VirtualSize=U32(bytes,row+8),Address=U32(bytes,row+12),RawSize=U32(bytes,row+16),RawOffset=U32(bytes,row+20),Flags=U32(bytes,row+36)};
                Need(bytes,s.RawOffset,s.RawSize);
                if (s.Name==".rsrc" && (s.Flags&0x20000020)!=0) throw new InvalidDataException("Resource section contains executable/code flags.");
                s.Hash=Hash(Slice(bytes,s.RawOffset,s.RawSize)); Sections.Add(s);
            }
            if (ResourceAddress!=0) { ResourceRoot=Offset(ResourceAddress,16); ReadDirectory(0,0,""); }
        }
        long Offset(uint address,uint size) {
            foreach(Section s in Sections) {
                if (address>=s.Address && (ulong)address+size<=(ulong)s.Address+s.RawSize) return (long)s.RawOffset+address-s.Address;
            }
            throw new InvalidDataException("Resource RVA is outside mapped sections.");
        }
        string ResourceName(uint value) {
            if ((value&0x80000000)==0) return "#"+value;
            long offset=ResourceRoot+(value&0x7fffffff); int length=U16(Bytes,offset);
            Need(Bytes,offset+2,length*2L);
            return "s:"+Convert.ToBase64String(Slice(Bytes,offset+2,(uint)length*2));
        }
        void ReadDirectory(uint relative,int depth,string prefix) {
            if(depth>2) throw new InvalidDataException("Unexpected resource directory depth.");
            long offset=ResourceRoot+relative; Need(Bytes,offset,16);
            int count=U16(Bytes,offset+12)+U16(Bytes,offset+14);
            resourceEntries+=count; if(resourceEntries>16384) throw new InvalidDataException("Too many resource entries.");
            Need(Bytes,offset+16,count*8L);
            for(int i=0;i<count;i++) {
                uint name=U32(Bytes,offset+16+i*8), child=U32(Bytes,offset+20+i*8);
                string path=prefix+"/"+ResourceName(name);
                if((child&0x80000000)!=0) ReadDirectory(child&0x7fffffff,depth+1,path);
                else {
                    if(depth!=2) throw new InvalidDataException("Unexpected resource leaf depth.");
                    long data=ResourceRoot+child; Need(Bytes,data,16);
                    uint rva=U32(Bytes,data),size=U32(Bytes,data+4);
                    if(!path.StartsWith("/#3/",StringComparison.Ordinal) && !path.StartsWith("/#14/",StringComparison.Ordinal))
                        OtherResources.Add(path,Hash(Slice(Bytes,Offset(rva,size),size)));
                }
            }
        }
    }
    static void Need(byte[] b,long offset,long length) {
        if(offset<0 || length<0 || offset>b.LongLength || length>b.LongLength-offset) throw new InvalidDataException("Truncated or out-of-bounds binary structure.");
    }
    static ushort U16(byte[] b,long o) { Need(b,o,2); return BitConverter.ToUInt16(b,(int)o); }
    static uint U32(byte[] b,long o) { Need(b,o,4); return BitConverter.ToUInt32(b,(int)o); }
    static ulong U64(byte[] b,long o) { Need(b,o,8); return BitConverter.ToUInt64(b,(int)o); }
    static byte[] Slice(byte[] b,long o,uint n) { Need(b,o,n); byte[] copy=new byte[(int)n]; Buffer.BlockCopy(b,(int)o,copy,0,(int)n); return copy; }
    static string Hash(byte[] b) { using(SHA256 sha=SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(b)).Replace("-","").ToLowerInvariant(); }
    static byte[] ReadBounded(string path,int maximum) {
        long length=new FileInfo(path).Length;
        if(length<1 || length>maximum) throw new InvalidDataException("Input file exceeds the supported size bound.");
        return File.ReadAllBytes(path);
    }
    static List<byte[]> IconImages(byte[] ico,out byte[] group) {
        Need(ico,0,6);
        int count=U16(ico,4);
        if(U16(ico,0)!=0 || U16(ico,2)!=1 || count<1 || count>32) throw new InvalidDataException("Invalid ICO header/count.");
        Need(ico,6,count*16L);
        List<byte[]> images=new List<byte[]>(); List<Tuple<uint,uint>> ranges=new List<Tuple<uint,uint>>();
        using(MemoryStream stream=new MemoryStream()) using(BinaryWriter writer=new BinaryWriter(stream)) {
            writer.Write((ushort)0);writer.Write((ushort)1);writer.Write((ushort)count);
            for(int i=0;i<count;i++) {
                long row=6+i*16; uint size=U32(ico,row+8),offset=U32(ico,row+12);
                if(ico[row+3]!=0 || size<8 || offset<6+count*16 || U16(ico,row+4)>1) throw new InvalidDataException("Invalid ICO directory entry.");
                Need(ico,offset,size);
                foreach(var range in ranges) if((ulong)offset<(ulong)range.Item1+range.Item2 && (ulong)range.Item1<(ulong)offset+size) throw new InvalidDataException("Overlapping ICO images.");
                ranges.Add(Tuple.Create(offset,size));
                byte[] image=Slice(ico,offset,size);
                bool png=image.Length>=24 && image[0]==137 && image[1]==80 && image[2]==78 && image[3]==71 && image[4]==13 && image[5]==10 && image[6]==26 && image[7]==10;
                if(!png && (image.Length<40 || U32(image,0)<40)) throw new InvalidDataException("ICO image is neither a PNG nor a supported DIB.");
                images.Add(image);
                writer.Write(ico,(int)row,12); writer.Write((ushort)(201+i));
            }
            group=stream.ToArray();
        }
        return images;
    }
    static void WinError(string operation) { throw new Win32Exception(Marshal.GetLastWin32Error(),operation); }
    static void VerifyResource(IntPtr module,int type,int id,byte[] expected) {
        IntPtr resource=FindResourceExW(module,new IntPtr(type),new IntPtr(id),1033);
        if(resource==IntPtr.Zero) WinError("FindResourceEx");
        uint size=SizeofResource(module,resource);
        if(size!=expected.Length) throw new InvalidDataException("Stored resource size mismatch.");
        IntPtr handle=LoadResource(module,resource);
        if(handle==IntPtr.Zero) WinError("LoadResource");
        IntPtr data=LockResource(handle);
        if(data==IntPtr.Zero) WinError("LockResource");
        byte[] actual=new byte[size];Marshal.Copy(data,actual,0,(int)size);
        if(!actual.SequenceEqual(expected)) throw new InvalidDataException("Stored resource bytes mismatch.");
    }
    static IntPtr LoadResourceModule(string path) {
        for(int attempt=0;attempt<50;attempt++) {
            // Data-only mapping supports resource APIs without mapping an image
            // for execution or initializing its code/imports.
            IntPtr module=LoadLibraryExW(path,IntPtr.Zero,0x2);
            if(module!=IntPtr.Zero)return module;
            int error=Marshal.GetLastWin32Error();
            if((error!=32 && error!=33) || attempt==49)throw new Win32Exception(error,"LoadLibraryEx resource-only");
            System.Threading.Thread.Sleep(100);
        }
        throw new InvalidOperationException("Resource mapping retry limit exceeded.");
    }
    public static Result Apply(string source,string icon,string destination) {
        byte[] original=ReadBounded(source,128*1024*1024),ico=ReadBounded(icon,16*1024*1024);
        Pe before=new Pe(original); byte[] group;
        List<byte[]> images=IconImages(ico,out group);
        bool created=false; IntPtr update=IntPtr.Zero;
        try {
            using(FileStream output=new FileStream(destination,FileMode.CreateNew,FileAccess.Write,FileShare.None)) { created=true;output.Write(original,0,original.Length); }
            update=BeginUpdateResourceW(destination,false);if(update==IntPtr.Zero)WinError("BeginUpdateResource");
            for(int i=0;i<images.Count;i++) if(!UpdateResourceW(update,new IntPtr(3),new IntPtr(201+i),1033,images[i],(uint)images[i].Length))WinError("UpdateResource icon");
            if(!UpdateResourceW(update,new IntPtr(14),new IntPtr(1),1033,group,(uint)group.Length))WinError("UpdateResource group");
            IntPtr pending=update;update=IntPtr.Zero;if(!EndUpdateResourceW(pending,false))WinError("EndUpdateResource");
            byte[] changed=ReadBounded(destination,160*1024*1024);Pe after=new Pe(changed);
            if(before.Entry!=after.Entry || before.ImageBase!=after.ImageBase || before.Subsystem!=after.Subsystem)throw new InvalidDataException("Executable entrypoint/header changed.");
            if(before.Directories.Count!=after.Directories.Count)throw new InvalidDataException("PE data directory count changed.");
            for(int i=0;i<before.Directories.Count;i++) if(i!=2 && i!=5 && !before.Directories[i].Equals(after.Directories[i]))throw new InvalidDataException("A non-resource data directory changed.");
            List<Section> nonResource=before.Sections.Where(s=>s.Name!=".rsrc").ToList();
            bool relocMoved=false;
            foreach(Section section in nonResource) {
                Section actual=after.Sections.SingleOrDefault(s=>s.Name==section.Name);
                if(actual!=null && actual.Address!=section.Address) {
                    if(section.Name!=".reloc" || (section.Flags&0x20000020)!=0 ||
                        before.RelocationAddress!=section.Address || after.RelocationAddress!=actual.Address ||
                        before.RelocationSize==0 || before.RelocationSize!=after.RelocationSize || before.RelocationSize>section.RawSize)
                        throw new InvalidDataException("A section RVA changed outside the narrowly allowed relocation-directory move.");
                    relocMoved=true;
                }
                if(actual==null || actual.Flags!=section.Flags || actual.VirtualSize!=section.VirtualSize || actual.RawSize!=section.RawSize || actual.Hash!=section.Hash)throw new InvalidDataException("A non-resource section changed: "+section.Name+"; before flags/virtual/raw/hash="+section.Flags+"/"+section.VirtualSize+"/"+section.RawSize+"/"+section.Hash+"; after="+(actual==null?"missing":actual.Flags+"/"+actual.VirtualSize+"/"+actual.RawSize+"/"+actual.Hash));
            }
            if(!relocMoved && (before.RelocationAddress!=after.RelocationAddress || before.RelocationSize!=after.RelocationSize))throw new InvalidDataException("Relocation directory changed without a matching unchanged section move.");
            if(after.Sections.Count(s=>s.Name!=".rsrc")!=nonResource.Count)throw new InvalidDataException("Unexpected new non-resource section.");
            if(before.OtherResources.Count!=after.OtherResources.Count || before.OtherResources.Any(pair=>!after.OtherResources.ContainsKey(pair.Key)||after.OtherResources[pair.Key]!=pair.Value))throw new InvalidDataException("An existing non-icon resource changed.");
            IntPtr module=LoadResourceModule(destination);
            try { VerifyResource(module,14,1,group);for(int i=0;i<images.Count;i++)VerifyResource(module,3,201+i,images[i]); }
            finally { FreeLibrary(module); }
            if(Hash(File.ReadAllBytes(source))!=Hash(original))throw new InvalidDataException("Source changed while preparing the output.");
            return new Result {InputExecutable=source,OutputExecutable=destination,InputSha256=Hash(original),OutputSha256=Hash(changed),IconSha256=Hash(ico),IconImageCount=images.Count,VerifiedResources=images.Count+1,VerifiedNonResourceSections=nonResource.Count,PreservedOtherResources=before.OtherResources.Count,RelocationSectionMoved=relocMoved,CodeIntegrity=true};
        } catch {
            if(update!=IntPtr.Zero)EndUpdateResourceW(update,true);
            if(created)File.Delete(destination);
            throw;
        }
    }
}
'@
}

[XmqrIconResourcesV1]::Apply($source, $icon, $destination) | ConvertTo-Json -Depth 4
