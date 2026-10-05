cmake_minimum_required(VERSION 3.14.0)
project(astra LANGUAGES C)

if(NOT AMIGA)
	message(SEND_ERROR "This project only compiles for Amiga - use 'agk build'")
endif()

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -DAMIGA -Wall -Wextra -fomit-frame-pointer")

# Build options (ACE and AGK) go in agk.toml under [cmake], e.g.
#   [cmake]
#   ACE_BOB_PRISTINE_BUFFER = true
# or one-off: agk build -D ACE_DEBUG=ON. Don't set() them here: ACE declares
# them as cache variables, so a plain set() is ignored on the first configure.
# Useful ones (default):
#   ACE_DEBUG (OFF)                   ACE logging + sanity checks, slow
#   ACE_BOB_WRAP_Y (ON)               BOBs wrap vertically; OFF is faster for simple buffers
#   ACE_BOB_PRISTINE_BUFFER (OFF)     BOBs restore from a clean background copy;
#                                     bobManagerCreate() then takes an extra argument
#   ACE_SCROLLBUFFER_ENABLE_SCROLL_X/Y (ON)   ACE_SCROLLBUFFER_X/Y_MARGIN_SIZE (1)
#   ACE_SCROLLBUFFER_POT_BITMAP_HEIGHT (ON)   faster, more chip RAM
#   ACE_USE_ECS_FEATURES / ACE_USE_AGA_FEATURES (OFF)
#   AGK_DEBUG_CHANNEL (host)          "serial" for debugging on real hardware
# Full list: third_party/ACE/cmake/ace_config.cmake

# tools/build passes AGK_KIT and ACE_DIR; these defaults are for manual builds.
set(AGK_KIT "/Users/youen/Code/amiga/amiga-game-kit" CACHE PATH "Amiga Game Kit root")
set(ACE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/vendor/ACE")
if(NOT EXISTS "${ACE_DIR}/include/ace/managers/multiplexedsprite.h")
	message(FATAL_ERROR "Run tools/bootstrap.sh from the repository root first")
endif()
add_subdirectory(${ACE_DIR} ace)
include_directories(${ACE_DIR}/include)
add_subdirectory(${AGK_KIT}/runtime agk)

file(GLOB_RECURSE SOURCES src/*.c)
# Art converted by agk (art/ -> build/art/art.c + art.h), if the project has any
if(EXISTS ${CMAKE_BINARY_DIR}/art/art.c)
	# AGK's pinned generator assumes allocation always succeeds. Keep the
	# upstream kit untouched, but guard generated constructors in this build.
	file(READ ${CMAKE_BINARY_DIR}/art/art.c ART_SOURCE)
	string(REGEX REPLACE "(tBitMap \\*pBm = bitmapCreate\\([^;]+;)"
		"\\1\n\tif (!pBm) return 0;" ART_SOURCE "${ART_SOURCE}")
	file(WRITE ${CMAKE_BINARY_DIR}/art/art-safe.c "${ART_SOURCE}")
	list(APPEND SOURCES ${CMAKE_BINARY_DIR}/art/art-safe.c)
	include_directories(${CMAKE_BINARY_DIR}/art)
endif()
# Sound converted by agk (sound/ -> build/sound/sound.c + sound.h), if any
if(EXISTS ${CMAKE_BINARY_DIR}/sound/sound.c)
	file(READ ${CMAKE_BINARY_DIR}/sound/sound.c SOUND_SOURCE)
	# Fail closed if the pinned generator changes: every safety anchor must match.
	function(astra_sound_replace BEFORE AFTER)
		string(FIND "${SOUND_SOURCE}" "${BEFORE}" FOUND)
		if(FOUND EQUAL -1)
			message(FATAL_ERROR "Sound safety transform: missing anchor ${BEFORE}")
		endif()
		string(REPLACE "${BEFORE}" "${AFTER}" SOUND_SOURCE "${SOUND_SOURCE}")
		set(SOUND_SOURCE "${SOUND_SOURCE}" PARENT_SCOPE)
	endfunction()
	astra_sound_replace("#include \"sound.h\""
		"#include \"sound.h\"\n#include \"audio_assets.h\"")
	astra_sound_replace("UBYTE *pDst = memAllocChip(ulBytes);"
		"UBYTE *pDst = memAllocChip(ulBytes);\n\tif(!pDst) return 0;")
	astra_sound_replace("void soundCreate(void) {" "UBYTE astraSoundCreate(void) {")
	astra_sound_replace(
		"s_pSfx[i].pData = (UWORD*)copyToChip(i, s_pSfxDefs[i].pData, s_pSfxDefs[i].uwBytes);"
		"s_pSfx[i].pData = (UWORD*)copyToChip(i, s_pSfxDefs[i].pData, s_pSfxDefs[i].uwBytes);\n\t\tif(!s_pSfx[i].pData) goto fail;")
	astra_sound_replace(
		"UBYTE *pChip = copyToChip(SOUND_SFX_COUNT + i, s_pMusicDefs[i].pSamples, s_pMusicDefs[i].ulSampleBytes);"
		"UBYTE *pChip = copyToChip(SOUND_SFX_COUNT + i, s_pMusicDefs[i].pSamples, s_pMusicDefs[i].ulSampleBytes);\n\t\tif(!pChip) goto fail;")
	# soundDestroy stops DMA/interrupts via ptplayerDestroy before freeing chip RAM.
	astra_sound_replace("\n}\n\nvoid soundDestroy(void) {"
		"\n\treturn 1;\nfail:\n\tsoundDestroy();\n\treturn 0;\n}\n\nvoid soundDestroy(void) {")
	astra_sound_replace("\t\ts_pChip[i] = 0;\n\t}\n}"
		"\t\ts_pChip[i] = 0;\n\t\ts_pChipSize[i] = 0;\n\t}\n\tfor(UBYTE i = 0; i < SOUND_SFX_COUNT; ++i) s_pSfx[i] = (tPtplayerSfx){0};\n\tfor(UBYTE i = 0; i < SOUND_MUSIC_COUNT; ++i) s_pMods[i] = (tPtplayerMod){0};\n}")
	file(WRITE ${CMAKE_BINARY_DIR}/sound/sound-safe.c "${SOUND_SOURCE}")
	list(APPEND SOURCES ${CMAKE_BINARY_DIR}/sound/sound-safe.c)
	include_directories(${CMAKE_CURRENT_SOURCE_DIR}/src)
	include_directories(${CMAKE_BINARY_DIR}/sound)
endif()
add_executable(astra ${SOURCES})
option(ASTRA_CAMPAIGN_PROBE "NON-SHIPPING injected native campaign fixture" OFF)
if(ASTRA_CAMPAIGN_PROBE)
	target_sources(astra PRIVATE tests/native/campaign_probe.c)
	target_compile_definitions(astra PRIVATE ASTRA_CAMPAIGN_PROBE=1)
endif()
target_link_libraries(astra ace agk)
