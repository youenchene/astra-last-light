; Astra Kick13 loader. Loader glue: MPL-2.0 (see game/art/intro/MPL-2.0.txt).
; Wepl/Psygore kick13.s and Wepl/JOTD/Psygore/DJ Mike kickfs.s: Public Domain.
; Derived from the official SDK20.0 Kick13 example, not the Rugby AGA loader.
 INCLUDE whdload.i
 INCLUDE whdmacros.i
 INCLUDE game-version.i
CHIPMEMSIZE = $80000
FASTMEMSIZE = $200000
NUMDRIVES = 1
WPDRIVES = %0000
BOOTDOS
HDINIT
STACKSIZE = 32768
IOCACHE = 4096
slv_Version = 19
slv_Flags = WHDLF_NoError
slv_keyexit = $59
 INCLUDE whdload/kick13.s
slv_CurrentDir dc.b "data",0
slv_name dc.b "Astra: Last Light",0
slv_copy dc.b "2026 Youen Chene; mixed licenses",0
slv_info dc.b "Kick13 / 68000 OCS",10,"F10 quits; Escape returns normally",0
slv_config = slv_base
 EVEN

_bootdos:
 ; Discard caller return so the executable sees the CLI stack-size argument.
 addq.l #4,sp
 move.l (_resload,pc),a2
 bsr _versionCheck
 lea (_dosname,pc),a1
 move.l 4.w,a6
 jsr (_LVOOldOpenLibrary,a6)
 move.l d0,a6
 lea (_program,pc),a0
 move.l a0,d1
 jsr (_LVOLoadSeg,a6)
 move.l d0,d7
 beq _loadError
 bsr _patchKeyboard
 move.l d7,a1
 add.l a1,a1
 add.l a1,a1
 moveq #1,d0
 lea (_args,pc),a0
 jsr (4,a1)
_quit:
 pea TDREASON_OK
 move.l (_resload,pc),a2
 jmp (resload_Abort,a2)
_loadError:
 jsr (_LVOIoErr,a6)
 pea (_program,pc)
 move.l d0,-(sp)
 pea TDREASON_DOSREAD
 move.l (_resload,pc),a2
 jmp (resload_Abort,a2)
_wrongVersion:
 pea TDREASON_WRONGVER
 move.l (_resload,pc),a2
 jmp (resload_Abort,a2)

_versionCheck:
 lea (_program,pc),a0
 jsr (resload_GetFileSize,a2)
 cmp.l #ASTRA_SIZE,d0
 bne _wrongVersion
 move.l 4.w,a6
 move.l #ASTRA_SIZE,d0
 moveq #MEMF_PUBLIC,d1
 jsr (_LVOAllocMem,a6)
 move.l d0,d3
 beq _wrongVersion
 move.l d0,a1
 lea (_program,pc),a0
 jsr (resload_LoadFile,a2)
 cmp.l #ASTRA_SIZE,d0
 bne _wrongVersion
 move.l d3,a0
 jsr (resload_CRC16,a2)
 move.w d0,d4
 move.l d3,a1
 move.l #ASTRA_SIZE,d0
 jsr (_LVOFreeMem,a6)
 cmp.w #ASTRA_CRC,d4
 bne _wrongVersion
 rts

; Check all candidates before modifying memory. Only the absolute relocated
; g_pCia address varies. Original a0/a1 register arguments stay intact.
_patchKeyboard:
 move.l d7,d6
 moveq #0,d5
.segment:
 move.l d6,a1
 add.l a1,a1
 add.l a1,a1
 move.l (a1),d6
 move.l -4(a1),d0
 subq.l #8,d0
 lea 4(a1),a0
.scan:
 cmp.l #28,d0
 blo .next
 cmp.l #$2f0a2f02,(a0)
 bne .advance
 cmp.w #$2479,4(a0)
 bne .advance
 cmp.l #$102a0c00,10(a0)
 bne .advance
 cmp.l #$4600122a,14(a0)
 bne .advance
 cmp.l #$0e000001,18(a0)
 bne .advance
 cmp.l #$00401541,22(a0)
 bne .advance
 cmp.w #$0e00,26(a0)
 bne .advance
 addq.l #1,d5
 move.l a0,a3
.advance:
 addq.l #2,a0
 subq.l #2,d0
 bra .scan
.next:
 tst.l d6
 bne .segment
 cmp.l #1,d5
 bne _wrongVersion
 lea (_replay,pc),a1
 move.l (a3),(a1)
 move.l 4(a3),4(a1)
 move.w 8(a3),8(a1)
 lea 10(a3),a0
 move.l a0,12(a1)
 move.w #$4ef9,(a3)
 lea (_keyboard,pc),a0
 move.l a0,2(a3)
 move.l #$4e714e71,6(a3)
 move.l (_resload,pc),a2
 jsr (resload_FlushCache,a2)
 rts

_keyboard:
 movem.l d0-d1/a0-a2,-(sp)
 move.b $bfec01,d0
 not.b d0
 ror.b #1,d0
 cmp.b (_keyexit,pc),d0
 beq _quit
 movem.l (sp)+,d0-d1/a0-a2
_replay:
 ; Original ten bytes copied from relocated handler, then continuation address.
 ds.b 10
 jmp $0.l
_program dc.b "Astra",0
_args dc.b 10,0
 EVEN
