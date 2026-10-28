"""Recover financial glyphs from embedded TrueType cmap, never guessed digit shifts."""
import struct
from pypdf.generic import DecodedStreamObject, NameObject

SAFE = set("0123456789.,+-()% \u20b9")


def financial_glyph_map(data):
    if not 12 <= len(data) <= 16*1024*1024:
        return {}
    try:
        count = struct.unpack_from(">H",data,4)[0]
        if count > 128:
            return {}
        tables = {}
        for i in range(count):
            pos = 12+i*16
            off,size = struct.unpack_from(">II",data,pos+8)
            if off+size > len(data):
                return {}
            tables[data[pos:pos+4]] = (off,size)
        base,length = tables[b"cmap"]
        count = struct.unpack_from(">H",data,base+2)[0]
        if count > 64:
            return {}
        candidates = {}
        for i in range(count):
            platform,encoding,off = struct.unpack_from(">HHI",data,base+4+i*8)
            if platform != 0 and (platform,encoding) != (3,1):
                continue
            pos = base+off
            fmt,size = struct.unpack_from(">HH",data,pos)
            if fmt != 4 or off+size > length:
                continue
            n = struct.unpack_from(">H",data,pos+6)[0]//2
            ends=pos+14; starts=ends+2*n+2; deltas=starts+2*n; ranges=deltas+2*n
            if n > 8192 or ranges+2*n > pos+size:
                continue
            for char in SAFE:
                code=ord(char)
                for seg in range(n):
                    end=struct.unpack_from(">H",data,ends+2*seg)[0]
                    start=struct.unpack_from(">H",data,starts+2*seg)[0]
                    if not start <= code <= end:
                        continue
                    delta=struct.unpack_from(">h",data,deltas+2*seg)[0]
                    shift=struct.unpack_from(">H",data,ranges+2*seg)[0]
                    if shift:
                        address=ranges+2*seg+shift+2*(code-start)
                        if address+2 > pos+size:
                            continue
                        gid=struct.unpack_from(">H",data,address)[0]
                        gid=(gid+delta)&65535 if gid else 0
                    else:
                        gid=(code+delta)&65535
                    if gid:
                        candidates.setdefault(gid,set()).add(char)
                    break
        return {gid:next(iter(chars)) for gid,chars in candidates.items() if len(chars)==1}
    except (KeyError,IndexError,struct.error,ValueError):
        return {}


def recover_financial_fonts(page):
    recovered=[]
    for name,ref in page.get("/Resources",{}).get("/Font",{}).items():
        font=ref.get_object()
        if font.get("/Subtype")!="/Type0" or font.get("/Encoding")!="/Identity-H" or "/ToUnicode" in font:
            continue
        try:
            descendant=font["/DescendantFonts"][0].get_object()
            if descendant.get("/Subtype")!="/CIDFontType2" or descendant.get("/CIDToGIDMap","/Identity")!="/Identity":
                continue
            mapping=financial_glyph_map(descendant["/FontDescriptor"]["/FontFile2"].get_data())
            if not any(c.isdigit() for c in mapping.values()):
                continue
            rows=[f"<{gid:04x}> <{ord(c):04x}>" for gid,c in sorted(mapping.items())]
            cmap=("/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n"
                  "/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n"
                  "/CMapName /FinancialRecovery def\n/CMapType 2 def\n"
                  "1 begincodespacerange\n<0000> <ffff>\nendcodespacerange\n"+
                  str(len(rows))+" beginbfchar\n"+"\n".join(rows)+"\nendbfchar\n"
                  "endcmap\nCMapName currentdict /CMap defineresource pop\nend\nend")
            stream=DecodedStreamObject();stream.set_data(cmap.encode("ascii"))
            font[NameObject("/ToUnicode")]=stream
            recovered.append(str(name))
        except (KeyError,IndexError,TypeError,ValueError):
            continue
    return recovered
